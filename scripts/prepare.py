#!/usr/bin/env python3
"""Validate an episode and synthesize resumable, word-aligned character audio."""
import argparse, asyncio, hashlib, importlib, json, os, re, ssl, subprocess, sys
from pathlib import Path

def probe(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)]))

def validate(data, root):
    from PIL import Image
    errors=[]
    for key in ['version','ip','title','title_zh','level','characters','lines','background']:
        if key not in data: errors.append(f'Missing {key}')
    if errors: raise ValueError('; '.join(errors))
    chars=data['characters']; ids=set()
    if data['version']!=1:errors.append('Unsupported episode version')
    if len(data.get('ending_title',''))>48:errors.append('Ending title too long (48 characters max)')
    review=data.get('review_terms',[])
    terms=[l['vocab']['term'] for l in data['lines'] if l.get('vocab')]
    if len(terms)<3:errors.append('At least 3 vocabulary cards are required')
    if len(data['title'])>72:errors.append('English title too long (72 characters max)')
    if review and (len(review)!=3 or any(term not in terms for term in review)):
        errors.append('review_terms must select exactly 3 existing vocabulary terms')
    if len({c['voice'] for c in chars.values()}) < min(3,len(chars)):
        errors.append('Use distinct narrator and character voices')
    def asset(name):
        p=(root/name).resolve()
        if not p.is_relative_to(root.resolve()): raise ValueError('Asset path escapes episode directory')
        return p
    Image.open(asset(data['background'])).verify()
    for who,c in chars.items():
        if 'sprite' in c:
            if c.get('side') not in ['left','right']:errors.append(f'{who}: invalid stage side')
            im=Image.open(asset(c['sprite']))
            if im.mode!='RGBA' or im.getextrema()[3][0]!=0:
                errors.append(f'{who}: sprite must have actual transparency')
    for line in data['lines']:
        lid=line.get('id','')
        if not re.fullmatch(r'[A-Za-z0-9_-]+',lid) or lid in ids: errors.append(f'Invalid or duplicate ID: {lid}')
        ids.add(lid)
        if line.get('speaker') not in chars: errors.append(f'{lid}: unknown speaker')
        if not line.get('en') or not line.get('zh'): errors.append(f'{lid}: bilingual text required')
        if len(line.get('en',''))>160: errors.append(f'{lid}: split long dialogue (160 characters max)')
        stage=line.get('stage',[])
        if len(stage)>2 or len(set(stage))!=len(stage):errors.append(f'{lid}: maximum two unique on-stage actors')
        if len({chars[a].get('side') for a in stage if a in chars})!=len(stage):errors.append(f'{lid}: stage actors need distinct sides')
        for actor in line.get('stage',[]):
            if actor not in chars or 'sprite' not in chars[actor]: errors.append(f'{lid}: invalid stage actor {actor}')
        if 'sprite' in chars.get(line.get('speaker'),{}) and line['speaker'] not in line.get('stage',[]):
            errors.append(f'{lid}: speaker must be on stage')
        if line.get('type')=='choice':
            opts=line.get('options',[])
            if len(opts)!=2 or line.get('answer') not in range(len(opts)): errors.append(f'{lid}: two choices and valid answer required')
            if not all(o.get('feedback') for o in opts): errors.append(f'{lid}: feedback required for each option')
        v=line.get('vocab')
        if v and v['term'].lower() not in line['en'].lower(): errors.append(f'{lid}: vocabulary term must occur in dialogue')
    if errors: raise ValueError('\n'.join(errors))

async def synth(data, root):
    import edge_tts
    # Respect the host trust store, including managed proxies. Never disable TLS checks.
    ca=os.environ.get('SSL_CERT_FILE') or os.environ.get('REQUESTS_CA_BUNDLE')
    if ca: importlib.import_module('edge_tts.communicate')._SSL_CTX=ssl.create_default_context(cafile=ca)
    folder=root/'audio';folder.mkdir(exist_ok=True)
    sem=asyncio.Semaphore(3)
    async def one(line):
        c=data['characters'][line['speaker']]
        rate=c.get('rate','+0%')
        if line.get('tone') in ['quiet','gentle']: rate=f'{int(rate[:-1])-5:+d}%'
        config={'text':line['en'],'voice':c['voice'],'rate':rate,'pitch':c.get('pitch','+0Hz'),'provider':'edge-tts-7.3.1'}
        digest=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
        audio=folder/(line['id']+'.mp3');meta=folder/(line['id']+'.json')
        if audio.exists() and meta.exists():
            old=json.loads(meta.read_text())
            if old.get('hash')==digest and abs(probe(audio)-old['duration'])<.08:
                return old
        async with sem:
            error=None
            for attempt in range(3):
                temp=audio.with_suffix('.part.mp3');bounds=[]
                try:
                    ctts=edge_tts.Communicate(config['text'],config['voice'],rate=rate,pitch=config['pitch'],boundary='WordBoundary',proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy'))
                    async def collect():
                        with temp.open('wb') as f:
                            async for chunk in ctts.stream():
                                if chunk['type']=='audio':f.write(chunk['data'])
                                elif chunk['type']=='WordBoundary':bounds.append({'text':chunk['text'],'start':chunk['offset']/1e7,'end':(chunk['offset']+chunk['duration'])/1e7})
                    await asyncio.wait_for(collect(),75)
                    duration=probe(temp)
                    if duration<.4 or not bounds:raise ValueError('Missing speech or genuine word timing')
                    if bounds[-1]['end']>duration+.15:raise ValueError('Word timing exceeds speech duration')
                    temp.replace(audio)
                    result={'hash':digest,'duration':duration,'words':bounds,'config':config,'file':str(audio.relative_to(root))}
                    tmp=meta.with_suffix('.part.json');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2));tmp.replace(meta)
                    print('SPEECH',line['id'],f'{duration:.2f}s',config['voice'],flush=True)
                    return result
                except Exception as e:
                    error=e;temp.unlink(missing_ok=True)
                    if attempt<2:await asyncio.sleep(2**attempt)
            raise RuntimeError(f"{line['id']}: TTS failed after 3 attempts: {error}. No silent or estimated-timing substitution was made.")
    return await asyncio.gather(*(one(l) for l in data['lines']))

def main():
    p=argparse.ArgumentParser();p.add_argument('episode',type=Path);p.add_argument('--validate-only',action='store_true');args=p.parse_args()
    source=args.episode.resolve();root=source.parent;data=json.loads(source.read_text());validate(data,root)
    if args.validate_only:print('Episode validation passed');return
    speech=asyncio.run(synth(data,root));cursor=5.0
    for line,clip in zip(data['lines'],speech):
        line['audio']=clip['file'];line['words']=clip['words'];line['speech_duration']=clip['duration']
        line['start']=cursor;line['audio_start']=cursor+.3
        hold=.55 if line.get('tone') in ['gentle','quiet'] else .3
        duration=.3+clip['duration']+hold
        if line.get('type')=='choice':duration+=line.get('seconds',7)
        line['end']=cursor+duration;cursor=line['end']
    data['duration']=cursor+8;data['outro_start']=cursor;data['timing_source']='TTS WordBoundary (not estimated)'
    tmp=root/'timeline.part.json';tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2));tmp.replace(root/'timeline.json')
    print(f'TIMELINE {data["duration"]:.2f}s / {len(data["lines"])} cues')

if __name__=='__main__':main()
