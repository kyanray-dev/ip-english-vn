#!/usr/bin/env python3
"""Deterministic visual-novel compositor. Layout units are 1280 x 720."""
import argparse, bisect, json, math, re, subprocess, tempfile, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps
from delivery import publish_video,require_video_output

ROOT=Path(__file__).resolve().parents[1]
GOLD='#ecd09a';JADE='#8ce0c6';WHITE='#f5f3eb';MUTED='#aebfc1'

def font_path(kind):
    bundled=ROOT/'fonts'
    names={'en':'sans.ttf','bold':'bold.ttf','serif':'serif.ttf','zh':'cjk.ttc'}
    if (bundled/names[kind]).exists():return str(bundled/names[kind])
    families={'en':'DejaVu Sans','bold':'DejaVu Sans:style=Bold','serif':'DejaVu Serif','zh':'Noto Sans CJK SC'}
    return subprocess.check_output(['fc-match','-f','%{file}',families[kind]],text=True).strip()

class Renderer:
    def __init__(self,data,folder,width=1920):
        self.data=data;self.folder=folder;self.scale=width/1280;self.size=(width,round(width*9/16));self.fonts={}
        self.paths={k:font_path(k) for k in ['en','bold','serif','zh']}
        self.bg=ImageOps.fit(Image.open(folder/data['background']).convert('RGB'),self.size,method=Image.Resampling.LANCZOS)
        self.bg=ImageEnhance.Brightness(self.bg).enhance(.7).convert('RGBA')
        self.sprites={}
        for who,c in data['characters'].items():
            if 'sprite' in c:
                im=Image.open(folder/c['sprite']).convert('RGBA');height=round(612*self.scale)
                im=im.resize((round(im.width*height/im.height),height),Image.Resampling.LANCZOS)
                self.sprites[who]=(im,ImageEnhance.Brightness(im).enhance(.66))
        self.starts=[l['start'] for l in data['lines']]
        self.layouts={l['id']:self.word_layout(l) for l in data['lines']}
        self.overflow=[]
        for l in data['lines']:
            if max((p[2] for p in self.layouts[l['id']]),default=0)>613: self.overflow.append(l['id'])
            if any(x+w>1210 for _,x,_,w in self.layouts[l['id']]):self.overflow.append(l['id']+': long token')
            if self.measure(l['zh'],19,'zh')>1150:self.overflow.append(l['id']+': Chinese caption')
            if self.measure(l.get('act',''),14)>780:self.overflow.append(l['id']+': act label')
            if l.get('vocab'):
                v=l['vocab']
                if self.measure(v['term'],25,'bold')>350:self.overflow.append(l['id']+': vocabulary term')
                if self.measure(v['meaning'],20,'zh')>350:self.overflow.append(l['id']+': vocabulary meaning')
                if len(self.wrap(v.get('note',''),350,13,'zh'))>2:self.overflow.append(l['id']+': vocabulary note')
            for o in l.get('options',[]):
                if self.measure(o['en'],19)>442:self.overflow.append(l['id']+': choice option')
        if self.overflow:raise ValueError('Dialogue overflow: '+','.join(self.overflow))
    def f(self,size,kind='en'):
        key=(size,kind)
        if key not in self.fonts:self.fonts[key]=ImageFont.truetype(self.paths[kind],round(size*self.scale))
        return self.fonts[key]
    def txt(self,d,xy,text,size=20,fill=WHITE,kind='en',**kw):
        d.text(tuple(round(x*self.scale) for x in xy),text,font=self.f(size,kind),fill=fill,**kw)
    def rect(self,d,box,fill,radius=12,outline=None,width=1):
        d.rounded_rectangle(tuple(round(x*self.scale) for x in box),round(radius*self.scale),fill=fill,outline=outline,width=max(1,round(width*self.scale)))
    def measure(self,text,size=20,kind='en'):return self.f(size,kind).getlength(text)/self.scale
    def wrap(self,text,width,size,kind='en'):
        chunks=text.split(' ') if kind!='zh' else list(text);sep=' ' if kind!='zh' else '';out=[];line=''
        for token in chunks:
            test=line+sep+token if line else token
            if self.measure(test,size,kind)>width and line:out.append(line);line=token
            else:line=test
        if line:out.append(line)
        return out
    def word_layout(self,l):
        x=64;y=554;out=[]
        for token in l['en'].split():
            w=self.measure(token,28)
            if x+w>1210:x=64;y+=39
            out.append((token,x,y,w));x+=w+self.measure(' ',28)
        return out
    def cue(self,t):
        i=bisect.bisect_right(self.starts,t)-1
        return (i,self.data['lines'][i]) if i>=0 else (-1,None)
    def text_block(self,d,text,x,y,width,size=20,kind='en',fill=WHITE,leading=1.35):
        for line in self.wrap(text,width,size,kind):
            self.txt(d,(x,y),line,size,fill,kind);y+=size*leading
        return y
    def lantern(self,im,t,l):
        if self.data.get('prop')!='lantern':return
        rise=next((line['start'] for line in self.data['lines'] if line.get('sfx')=='lyre'),self.data['duration'])
        s=self.scale;up=max(0,t-rise)*8
        x=640+math.sin(t*.7)*12;y=210+math.sin(t*.9)*6-up
        if y<-100:return
        glow=Image.new('RGBA',self.size);d=ImageDraw.Draw(glow)
        for r in range(70,9,-5):
            d.ellipse(tuple(round(z*s) for z in (x-r,y-r,x+r,y+r)),fill=(246,195,93,2))
        self.rect(d,(x-17,y-25,x+17,y+25),(249,205,124,240),10,outline=(255,234,179,255))
        for dx in [-9,0,9]:d.line([(round((x+dx)*s),round((y-23)*s)),(round((x+dx)*s),round((y+23)*s))],fill=(151,96,44,170),width=round(s))
        d.line([(round(x*s),round((y-45)*s)),(round(x*s),round((y-25)*s))],fill=GOLD,width=round(s))
        im.alpha_composite(glow)
    def frame(self,t,zh=True):
        im=self.bg.copy();s=self.scale;i,l=self.cue(t)
        # Slow drifting motes keep the environment alive without moving the subtitles.
        d=ImageDraw.Draw(im)
        for n in range(18):
            x=(n*157+t*(7+n%3))%1280;y=70+(n*83)%390+math.sin(t*.6+n)*10
            d.ellipse((round(x*s),round(y*s),round((x+2)*s),round((y+2)*s)),fill=(180,228,211,140))
        if t<5:return self.title(im,t)
        if t>=self.data['outro_start']:return self.outro(im,t)
        prev=self.data['lines'][i-1].get('stage',[]) if i>0 else []
        current=l.get('stage',[]);local=t-l['start'];ease=1-(1-min(1,local/.7))**3
        for who in dict.fromkeys(prev+current):
            if who not in self.sprites:continue
            c=self.data['characters'][who];side=c.get('side','left');active=l['speaker']==who
            sprite=self.sprites[who][0 if active else 1]
            entering=who not in prev;leaving=who not in current
            if leaving and local>=.7:continue
            a=ease if entering else 1-ease if leaving else 1
            offset=(1-a)*440*(-1 if side=='left' else 1)
            x=(62 if side=='left' else 808)+offset
            y=66+math.sin(t*1.8+(0 if side=='left' else 2))*2
            im.alpha_composite(sprite,(round(x*s),round(y*s)))
        self.lantern(im,t,l)
        overlay=Image.new('RGBA',self.size);d=ImageDraw.Draw(overlay)
        self.rect(d,(24,18,1256,65),(7,21,32,225),14,outline=(167,207,199,60))
        self.txt(d,(42,29),self.data.get('brand','WIND / WORDS'),18,GOLD,'bold')
        self.txt(d,(284,32),l.get('act','STORY'),14,MUTED)
        self.txt(d,(1100,29),self.data['level']+'  /  EN',17,JADE,'bold')
        # Vocabulary floats in the open space between the characters.
        v=l.get('vocab')
        if v and l.get('type')!='choice':
            self.rect(d,(441,299,839,473),(8,26,37,237),18,outline=(140,224,198,110))
            self.txt(d,(465,317),'WORD DISCOVERED',11,JADE,'bold')
            self.txt(d,(465,339),v['term'],25,GOLD,'bold')
            self.txt(d,(465,374),v.get('ipa',''),14,MUTED)
            self.txt(d,(465,400),v['meaning'],20,WHITE,'zh')
            self.text_block(d,v.get('note',''),465,437,350,13,'zh',MUTED)
        if l.get('type')=='choice':self.choice(d,l,t)
        self.rect(d,(28,509,1252,686),(8,22,33,247),18,outline=(205,185,132,150))
        c=self.data['characters'][l['speaker']]
        self.rect(d,(51,495,248,536),(19,48,54,255),9,outline=c['color'])
        self.txt(d,(67,504),c['name'],18,c['color'],'bold')
        self.txt(d,(269,518),c['zh'],13,MUTED,'zh')
        self.txt(d,(1113,518),f'{i+1:02d} / {len(self.data["lines"]):02d}',13,MUTED)
        spoken=t-l['audio_start'];words=l['words']
        # Map real word boundaries by matching normalized text spans, including contractions.
        current_word=None
        for word in words:
            if word['start']<=spoken<word['end']+.04:current_word=word;break
        target=re.sub(r'[^a-z0-9]','',current_word['text'].lower()) if current_word else ''
        hit=None
        if target:
            index=words.index(current_word);before=''.join(re.sub(r'[^a-z0-9]','',w['text'].lower()) for w in words[:index]);char_start=len(before)
            count=0
            for k,(token,x,y,w) in enumerate(self.layouts[l['id']]):
                n=len(re.sub(r'[^a-z0-9]','',token.lower()))
                if count<=char_start<count+n:hit=k;break
                count+=n
        term=v['term'].lower().split() if v else []
        for k,(token,x,y,w) in enumerate(self.layouts[l['id']]):
            if k==hit:self.rect(d,(x-4,y-1,x+w+5,y+36),(67,109,101,255),6)
            fill=JADE if k==hit else WHITE
            self.txt(d,(x,y),token,28,fill)
            if re.sub(r'[^a-z]','',token.lower()) in term:
                d.line([(round(x*s),round((y+35)*s)),(round((x+w)*s),round((y+35)*s))],fill=GOLD,width=round(1.5*s))
        if zh:self.txt(d,(64,643),l['zh'],19,MUTED,'zh')
        fraction=t/self.data['duration'];self.rect(d,(28,703,1252,706),(66,84,87,255),1);self.rect(d,(28,703,28+1224*fraction,706),JADE,1)
        im.alpha_composite(overlay)
        return im.convert('RGB')
    def choice(self,d,l,t):
        self.rect(d,(369,159,911,477),(7,24,36,245),20,outline=(140,224,198,175))
        self.txt(d,(395,182),'YOUR TURN',14,JADE,'bold')
        self.txt(d,(395,210),'Read the clue. Make a choice.',22,WHITE,'bold')
        self.txt(d,(395,245),'暂停想一想，再继续剧情',16,MUTED,'zh')
        for n,o in enumerate(l['options']):
            y=286+n*76;selected=t>l['end']-1.5 and n==l['answer']
            self.rect(d,(393,y,887,y+62),(33,73,70,255) if selected else (23,43,55,255),10,outline=JADE if selected else '#527078')
            self.txt(d,(410,y+9),f'{"AB"[n]}  '+o['en'],19,JADE if selected else WHITE)
            self.txt(d,(440,y+36),o['zh'],14,MUTED,'zh')
        remaining=max(0,math.ceil(l['end']-t-1.5))
        self.txt(d,(398,451),f'{remaining:02d} s   /   '+('CLUE FOUND' if remaining==0 else 'THINK IN ENGLISH'),11,GOLD,'bold')
    def title(self,im,t):
        layer=Image.new('RGBA',self.size,(5,19,31,95));d=ImageDraw.Draw(layer)
        self.txt(d,(76,70),self.data.get('brand','WIND / WORDS'),22,GOLD,'bold')
        self.txt(d,(80,184),self.data['ip'].split('/')[0].strip().upper()+'  /  FAN STORY 01',14,JADE,'bold')
        y=self.text_block(d,self.data['title'],76,230,1050,58,'serif',WHITE,1.15)
        self.txt(d,(80,y+21),self.data['title_zh'],31,GOLD,'zh')
        self.txt(d,(80,541),'A story to follow. A language to discover.',22,WHITE)
        self.txt(d,(80,586),self.data['level']+' ENGLISH     /     '+str(len(self.data['characters']))+' VOICES     /     READ · LISTEN · CHOOSE',13,JADE,'bold')
        self.txt(d,(80,662),self.data.get('disclosure',''),11,MUTED)
        im.alpha_composite(layer);return im.convert('RGB')
    def outro(self,im,t):
        layer=Image.new('RGBA',self.size,(4,19,30,180));d=ImageDraw.Draw(layer)
        self.txt(d,(88,75),'QUEST COMPLETE',16,JADE,'bold')
        self.txt(d,(84,118),self.data.get('ending_title','Every story leaves a little light.'),43,WHITE,'serif')
        self.txt(d,(88,190),'故事结束，带走三个表达。',23,GOLD,'zh')
        vocab_lines=[line for line in self.data['lines'] if line.get('vocab')]
        review=self.data.get('review_terms',[line['vocab']['term'] for line in vocab_lines[:3]])
        selected=[next(line for line in vocab_lines if line['vocab']['term']==term) for term in review[:3]]
        for n,line in enumerate(selected):
            term=line['vocab']['term'];meaning=line['vocab']['meaning'];sentence=line['en']
            y=262+n*105;self.rect(d,(84,y,1196,y+86),(16,41,51,242),13,outline='#395c61')
            self.txt(d,(107,y+17),term,25,JADE,'bold');self.txt(d,(500,y+22),meaning,21,GOLD,'zh');self.txt(d,(108,y+54),sentence,15,MUTED)
        self.txt(d,(88,624),'REPLAY THE STORY. CAN YOU USE THESE EXPRESSIONS?',14,GOLD,'bold')
        self.txt(d,(88,669),self.data.get('disclosure',''),11,MUTED)
        im.alpha_composite(layer);return im.convert('RGB')

def make_audio(data,folder,out):
    import wave
    sr=48000;mix=np.zeros(round((data['duration']+.2)*sr),dtype=np.float32)
    for line in data['lines']:
        raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(folder/line['audio']),'-f','f32le','-ac','1','-ar',str(sr),'-'])
        pcm=np.frombuffer(raw,dtype='<f4').copy()
        rms=float(np.sqrt(np.mean(pcm**2)));gain=min(2.0,.12/max(rms,.001));pcm*=gain
        at=round(line['audio_start']*sr);mix[at:at+len(pcm)]+=pcm[:len(mix)-at]
        if line.get('sfx')=='lyre':
            for k,f in enumerate([392,493.88,587.33]):
                tt=np.arange(round(sr*1.9))/sr;note=.025*np.sin(2*np.pi*f*tt)*np.exp(-tt*2.7)
                pos=at+round((.25+k*.22)*sr);mix[pos:pos+len(note)]+=note
    # Quiet original synthesized ambience, no copyrighted soundtrack.
    tt=np.arange(len(mix))/sr
    bed=.0016*(np.sin(2*np.pi*146.83*tt)+.55*np.sin(2*np.pi*220*tt))
    fade=np.minimum(1,tt/3)*np.minimum(1,(data['duration']-tt)/3).clip(0,1)
    mix+=bed*fade;mix=np.clip(mix,-.95,.95)
    with wave.open(str(out),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes((mix*32767).astype('<i2').tobytes())

def stamp(t):
    ms=round(t*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'

def export_subtitles(data,work):
    """Temporary muxing inputs, never standalone deliverables."""
    for lang in ['en','zh']:
        text='\n\n'.join(f'{i+1}\n{stamp(l["audio_start"])} --> {stamp(l["audio_start"]+l["speech_duration"])}\n{l[lang]}' for i,l in enumerate(data['lines']))
        (work/f'subtitles.{lang}.srt').write_text(text+'\n')

def encode_video(data,folder,work,renderer,fps,chinese):
    export_subtitles(data,work);make_audio(data,folder,work/'mix.wav')
    total=math.ceil(data['duration']*fps);start=time.time();temp=work/'episode.mp4'
    command=['ffmpeg','-y','-v','warning','-f','rawvideo','-pix_fmt','rgb24','-s',f'{renderer.size[0]}x{renderer.size[1]}','-r',str(fps),'-i','-','-i',str(work/'mix.wav'),'-i',str(work/'subtitles.zh.srt'),'-i',str(work/'subtitles.en.srt'),'-map','0:v','-map','1:a','-map','2:s','-map','3:s','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-c:s','mov_text','-metadata:s:s:0','language=zho','-metadata:s:s:1','language=eng','-disposition:s:0','0','-disposition:s:1','0','-movflags','+faststart','-t',str(data['duration']),str(temp)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE)
    try:
        for n in range(total):
            process.stdin.write(renderer.frame(n/fps,chinese).tobytes())
            if n%240==0:print(f'RENDER {n}/{total} frames / {time.time()-start:.0f}s elapsed',flush=True)
        process.stdin.close()
        if process.wait()!=0:raise RuntimeError('FFmpeg failed')
    except BaseException:
        process.kill();process.wait();raise
    return temp

def main():
    p=argparse.ArgumentParser();p.add_argument('timeline',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--width',type=int,default=1920);p.add_argument('--fps',type=int,default=24);p.add_argument('--no-chinese',action='store_true');args=p.parse_args()
    if args.width<320 or args.width%2 or round(args.width*9/16)%2:p.error('Width and 16:9 height must be positive even values')
    if not 1<=args.fps<=120:p.error('FPS must be between 1 and 120')
    path=args.timeline.resolve();data=json.loads(path.read_text());out=args.out.resolve();require_video_output(out)
    r=Renderer(data,path.parent,args.width)
    with tempfile.TemporaryDirectory(prefix='ip-english-vn-render-') as tmp:
        source=encode_video(data,path.parent,Path(tmp),r,args.fps,not args.no_chinese)
        video=publish_video(source,out)
    print('DONE',video,flush=True)

if __name__=='__main__':main()
