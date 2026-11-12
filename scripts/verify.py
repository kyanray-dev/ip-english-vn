#!/usr/bin/env python3
"""Fail loudly on incomplete, silent, unsynchronized or invalid deliverables."""
import argparse,json,re,subprocess,sys
from pathlib import Path
import numpy as np
from prepare import validate
from render import Renderer

def norm(text):return re.sub('[^a-z0-9]','',text.lower())
def check(timeline,out):
    data=json.loads(timeline.read_text());root=timeline.parent;validate(data,root);errors=[];checks=[]
    r=Renderer(data,root,1280)
    last=5.;vocab=0
    for l in data['lines']:
        if abs(l['start']-last)>.001:errors.append(l['id']+': gap or overlap in timeline')
        if not l['start']<=l['audio_start']<l['audio_start']+l['speech_duration']<=l['end']+.01:errors.append(l['id']+': speech outside cue')
        words=l['words']
        if norm(''.join(w['text'] for w in words))!=norm(l['en']):errors.append(l['id']+': spoken words do not match script')
        prior=0
        for w in words:
            if w['start']<prior-.01 or not w['start']<w['end']<=l['speech_duration']+.15:errors.append(l['id']+': invalid word timing')
            prior=w['start']
        # A blank or corrupt clip must never be counted as a successful voice.
        raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(root/l['audio']),'-f','f32le','-ac','1','-ar','16000','-'])
        pcm=np.frombuffer(raw,dtype='<f4');rms=float(np.sqrt(np.mean(pcm**2)))
        if rms<.006:errors.append(l['id']+': silent/inaudible speech')
        last=l['end'];vocab+=bool(l.get('vocab'))
    checks.append({'name':'dialogue_and_word_alignment','cues':len(data['lines']),'status':'passed' if not errors else 'failed'})
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(out/'episode.mp4')]))
    streams=info['streams'];vs=next(s for s in streams if s['codec_type']=='video');aus=next(s for s in streams if s['codec_type']=='audio')
    if abs(float(info['format']['duration'])-data['duration'])>.12:errors.append('Video duration differs from timeline')
    if abs(float(vs.get('duration',0))-float(aus.get('duration',0)))>.15:errors.append('Audio/video duration mismatch')
    if vs['codec_name']!='h264' or vs['pix_fmt']!='yuv420p':errors.append('Video must be broadly compatible H.264/yuv420p')
    if len([s for s in streams if s['codec_type']=='subtitle'])!=2:errors.append('Missing bilingual subtitle tracks')
    checks.append({'name':'media','resolution':f'{vs["width"]}x{vs["height"]}','duration':float(info['format']['duration']),'voices':len({c['voice'] for c in data['characters'].values()}),'vocabulary_cards':vocab})
    required=['index.html','poster.jpg','subtitles.en.srt','subtitles.zh.srt','novel-english.txt','novel-bilingual.txt','vocabulary.json']
    for f in required:
        if not (out/f).exists() or not (out/f).stat().st_size:errors.append('Missing '+f)
    result={'passed':not errors,'checks':checks,'errors':errors,'timing_source':data['timing_source'],'scope':'Automated media/schema/timing/layout checks. Does not establish subjective acting quality or canon accuracy.'}
    (out/'qa-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
    return not errors
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('timeline',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();sys.exit(0 if check(a.timeline.resolve(),a.out.resolve()) else 1)
