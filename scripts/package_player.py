#!/usr/bin/env python3
import argparse,json,shutil
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('timeline',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    data=json.loads(a.timeline.read_text());a.out.mkdir(parents=True,exist_ok=True)
    template=Path(__file__).with_name('player.html').read_text()
    # JSON embedded inside script must never be able to close the script element.
    payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    (a.out/'index.html').write_text(template.replace('__EPISODE_DATA__',payload))
    shutil.copy2(Path(__file__).with_name('serve.py'),a.out/'serve.py')
    print(a.out/'index.html')
if __name__=='__main__':main()
