"""Run against scripts/serve.py; Playwright and Chromium are optional QA dependencies."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import argparse,json
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8001');p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1);page.set_default_timeout(15000)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(a.url,wait_until='networkidle');page.wait_for_function('document.querySelector("video").readyState>=2')
    page.locator('#start').click();page.wait_for_function('!document.querySelector("video").paused')
    page.evaluate('video.currentTime=18');page.wait_for_function('video.currentTime>19 && !video.seeking');page.evaluate('video.pause()')
    pixels=page.evaluate('''() => {const c=document.createElement('canvas');c.width=64;c.height=36;const x=c.getContext('2d');x.drawImage(video,0,0,64,36);return [...x.getImageData(0,0,64,36).data].filter((_,i)=>i%4!==3).reduce((a,b)=>a+b,0)/(64*36*3)}''')
    assert pixels>10,'Decoded video frame is black'
    page.screenshot(path=str(out/'player-preview.png'),full_page=False)
    page.locator('#captions').click();assert page.evaluate('video.textTracks[0].mode')=='hidden'
    page.locator('#captions').click();assert page.evaluate('video.textTracks[0].mode')=='showing'
    results={'video_loaded':True,'play':True,'seek':True,'subtitle_toggle':True}
    for answer in [1,0]:
        page.evaluate('''() => {answered.clear(); const l=DATA.lines.find(l=>l.type==='choice');video.currentTime=l.audio_start+l.speech_duration+.4;video.dispatchEvent(new Event('timeupdate'));}''')
        page.wait_for_selector('#choiceGate.visible');assert page.evaluate('video.paused')
        page.locator('#options button').nth(answer).click();feedback=page.locator('#feedback').inner_text();assert len(feedback)>10
        if answer==0:page.screenshot(path=str(out/'choice-preview.png'),full_page=False)
        page.locator('#continue').click();page.wait_for_function('!video.paused')
        assert page.evaluate('video.currentTime>DATA.lines.find(l=>l.type==="choice").end')
        page.evaluate('video.pause()');results['choice_'+str(answer)]={'feedback':feedback,'resumed':True}
    page.locator('#repeat').click();page.wait_for_function('!video.paused');results['replay_line']=True
    page.locator('[data-tab="vocab"]').click();expected=page.evaluate('DATA.lines.filter(l=>l.vocab).length');assert page.locator('#wordGrid .word').count()==expected;results['vocabulary_cards']=expected
    page.evaluate('video.pause()');page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'mobile-preview.png'))
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth');results['mobile_no_overflow']=True;results['console_errors']=errors;assert not errors
    (out/'browser-qa.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(results,ensure_ascii=False,indent=2));browser.close()
