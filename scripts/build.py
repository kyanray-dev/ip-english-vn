#!/usr/bin/env python3
"""Code-render one MP4. Never call video-generation services or export sidecars."""
import argparse,subprocess,sys,tempfile
from pathlib import Path
from delivery import publish_video,require_video_output
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('episode',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--width',type=int,default=1920);p.add_argument('--fps',type=int,default=24)
    captions=p.add_mutually_exclusive_group()
    captions.add_argument('--no-chinese',action='store_true',help='Omit Chinese dialogue from the picture; keep subtitle tracks in the same MP4')
    captions.add_argument('--bilingual',action='store_true',help=argparse.SUPPRESS)
    a=p.parse_args()
    if a.width<320 or a.width%2 or round(a.width*9/16)%2:p.error('Width and 16:9 height must be positive even values (1280 or 1920 recommended)')
    if not 1<=a.fps<=120:p.error('FPS must be between 1 and 120')
    ep=a.episode.resolve();out=a.out.resolve();timeline=ep.with_name('timeline.json')
    require_video_output(out)
    def run(script,*args):subprocess.run([sys.executable,str(ROOT/'scripts'/script),*map(str,args)],check=True)
    run('prepare.py',ep)
    with tempfile.TemporaryDirectory(prefix='ip-english-vn-build-') as tmp:
        staging=Path(tmp)/'validated-video'
        flags=['--no-chinese'] if a.no_chinese else []
        run('render.py',timeline,'--out',staging,'--width',a.width,'--fps',a.fps,*flags)
        run('verify.py',timeline,'--out',staging)
        video=publish_video(staging/'episode.mp4',out)
    print('DONE',video)
if __name__=='__main__':main()
