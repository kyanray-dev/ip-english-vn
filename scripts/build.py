#!/usr/bin/env python3
"""One-command repeatable build from an agent-authored episode and generated assets."""
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('episode',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--width',type=int,default=1920);p.add_argument('--fps',type=int,default=24);p.add_argument('--bilingual',action='store_true');a=p.parse_args()
    if a.width%2 or round(a.width*9/16)%2:p.error('Width and derived 16:9 height must both be even (1280 or 1920 recommended)')
    ep=a.episode.resolve();out=a.out.resolve();timeline=ep.with_name('timeline.json')
    def run(script,*args):subprocess.run([sys.executable,str(ROOT/'scripts'/script),*map(str,args)],check=True)
    run('prepare.py',ep)
    run('render.py',timeline,'--out',out,'--width',a.width,'--fps',a.fps,'--no-chinese')
    run('package_player.py',timeline,'--out',out)
    if a.bilingual:
        # Filter filenames are local fixed basenames, never untrusted shell fragments.
        subprocess.run(['ffmpeg','-y','-v','warning','-i','episode.mp4','-vf',"subtitles=subtitles.zh.srt:force_style='FontName=Noto Sans CJK SC,FontSize=15,PrimaryColour=&H00D4DDD7,OutlineColour=&H0022170B,BorderStyle=1,Outline=1,Shadow=0,Alignment=2,MarginV=29'",'-map','0:v','-map','0:a','-c:v','libx264','-preset','fast','-crf','20','-c:a','copy','-movflags','+faststart','episode-bilingual.mp4'],cwd=out,check=True)
    run('verify.py',timeline,'--out',out)
if __name__=='__main__':main()
