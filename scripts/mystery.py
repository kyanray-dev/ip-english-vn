"""A code-drawn case-file theme: charcoal panels, red tabs and amber clues."""
import math

import numpy as np
from PIL import Image, ImageDraw

from dialogue_ui import DialogueUI

WHITE = '#edf1f2'
MUTED = '#a7b3c1'
AMBER = '#f4c273'
RED = '#b84945'
BORDER = '#405265'


class MysteryUI(DialogueUI):
    FONT_KIND = 'en'
    NAME_FONT = 'zh'
    MAX_SIZE = 32
    LEFT = 56
    TOP = 531
    TEXT_COLOR = WHITE
    ACTIVE_COLOR = '#fff1ce'
    SECONDARY_COLOR = MUTED
    UNDERLINE_COLOR = AMBER

    def make_base(self):
        layer = Image.new('RGBA', self.r.size)
        width, height = self.point((1224, 202))
        yy, xx = np.mgrid[:height, :width]
        rng = np.random.default_rng(407)
        grain = rng.normal(0, .65, (height, width)) + yy / height * 3
        pixels = np.clip(np.array([17, 24, 35]) + grain[..., None], 0, 255).astype('uint8')
        layer.alpha_composite(Image.fromarray(pixels).convert('RGBA'), self.point((28, 480)))
        d = ImageDraw.Draw(layer)
        self.r.rect(d, (28,480,1252,682), None, 2, BORDER)
        self.line(d, [(28,480),(236,480)], RED, 3)
        self.line(d, [(44,516),(1236,516)], '#2c3b4a')
        for x,y,sx,sy in [(28,480,1,1),(1252,480,-1,1),(28,682,1,-1),(1252,682,-1,-1)]:
            self.line(d, [(x,y+sy*10),(x,y),(x+sx*14,y)], '#708395', 1.5)
        return layer

    def draw_highlight(self, d, x, y, width, size):
        self.r.rect(d, (x-4,y-3,x+width+4,y+size+4), '#604b2e', 2)

    def draw(self, image, cue, index, t, chinese=True):
        image.alpha_composite(self.base)
        d = ImageDraw.Draw(image)
        self.r.rect(d, (32,22,37,74), RED, 0)
        self.block(d, self.heading, 51,23,WHITE,'zh')
        self.block(d, self.scene_labels[cue['id']], 53,64,MUTED,'zh')
        self.text(d, (1102,29), self.r.data['level']+' / EN', 16, AMBER, 'bold')
        self.text(d, (1102,55), 'CASE FILE 01', 11, MUTED, 'en')
        c = self.r.data['characters'][cue['speaker']]
        self.r.rect(d, (44,491,108,509), RED, 1)
        self.text(d, (51,494), 'VOICE', 10, WHITE, 'bold')
        label = self.fit(c['zh']+'  /  '+c['name'], 650, 24, 18, 13, 'zh', 1)
        self.block(d,label,124,491,WHITE,'zh')
        self.text(d,(813,495),f'{index+1:02d} / {len(self.r.data["lines"]):02d}',11,MUTED,'en')
        if cue.get('vocab'):
            for x in range(954,1235,24):
                self.line(d, [(x,528),(x,670)], '#1b2938', .5)
            self.line(d, [(940,531),(940,663)], BORDER)
        self.draw_words(d,cue,t,chinese)
        if cue.get('vocab'):
            self.text(d,(968,494),'LANGUAGE FILE',11,AMBER,'bold')
            y = 536
            for _, field, kind, fill in self.layouts[cue['id']]['vocab']:
                if field['lines']:
                    y = self.block(d,field,968,y,fill,kind)+4
        fraction = max(0,min(1,t/self.r.data['duration']))
        self.line(d,[(44,701),(1236,701)],BORDER)
        self.line(d,[(44,701),(44+1192*fraction,701)],RED,2)
        self.r.rect(d,(43+1192*fraction,698,46+1192*fraction,704),AMBER,0)

    def choice(self, d, cue, t):
        self.r.rect(d,(368,143,912,475),'#111a26',3,BORDER,2)
        self.line(d,[(368,143),(570,143)],RED,3)
        self.text(d,(398,164),'YOUR DEDUCTION',18,AMBER,'bold')
        self.text(d,(398,201),'Which clue changes the story?',21,WHITE,'en')
        self.text(d,(398,236),'暂停观察，再作判断',16,MUTED,'zh')
        for n,option in enumerate(cue['options']):
            y = 270+n*83
            selected = t >= cue['end']-1.5 and n == cue['answer']
            self.r.rect(d,(392,y,888,y+78),'#443827' if selected else '#1b2938',2,AMBER if selected else BORDER)
            self.text(d,(407,y+13),'AB'[n],21,AMBER,'bold')
            # Use the same measured option font as the shared preflight.
            layout = self.fit(option['en'],420,44,21,17,'serif',2)
            end = self.block(d,layout,440,y+8,WHITE)
            zh = self.fit(option['zh'],420,24,16,13,'zh',1)
            self.block(d,zh,440,max(y+45,end+2),MUTED,'zh')
        remaining = max(0,math.ceil(cue['end']-t-1.5))
        self.text(d,(398,448),f'{remaining:02d} s / '+('CLUE CONFIRMED' if not remaining else 'EXAMINE THE EVIDENCE'),12,AMBER,'en')

    def title(self, image, t):
        layer = Image.new('RGBA', self.r.size, (5,11,19,150))
        d = ImageDraw.Draw(layer)
        self.r.rect(d,(64,65,204,96),RED,1)
        self.text(d,(78,74),'CASE FILE 01',14,WHITE,'bold')
        self.line(d,[(68,188),(68,456)],RED,3)
        title = self.fit(self.r.data['title'],1050,164,58,36,'serif',2)
        end = self.block(d,title,94,219,WHITE)
        self.text(d,(97,end+24),self.r.data['title_zh'],29,AMBER,'zh')
        self.text(d,(96,524),'LOOK CLOSER. EVERY DETAIL MATTERS.',18,WHITE,'bold')
        self.text(d,(96,569),self.r.data['level']+' ENGLISH / READ · LISTEN · DEDUCE',13,MUTED,'en')
        self.text(d,(96,664),self.r.data.get('disclosure',''),11,MUTED,'en')
        image.alpha_composite(layer)
        return image.convert('RGB')

    def outro(self, image, t):
        layer = Image.new('RGBA',self.r.size,(5,11,19,205))
        d = ImageDraw.Draw(layer)
        self.text(d,(84,67),'CASE CLOSED / EVIDENCE REVIEW',15,AMBER,'bold')
        title = self.fit(self.r.data.get('ending_title','The details tell the truth.'),1110,100,42,28,'serif',2)
        self.block(d,title,80,116,WHITE)
        self.text(d,(84,213),'案件结束，记住三个表达。',21,MUTED,'zh')
        vocab = [line for line in self.r.data['lines'] if line.get('vocab')]
        review = self.r.data.get('review_terms',[line['vocab']['term'] for line in vocab[:3]])
        for n,term in enumerate(review[:3]):
            cue = next(line for line in vocab if line['vocab']['term']==term)
            y = 273+n*103
            self.r.rect(d,(80,y,1200,y+85),'#152131',2,BORDER)
            self.r.rect(d,(80,y,84,y+85),RED,0)
            name = self.fit(term,370,35,25,19,'en',1)
            self.block(d,name,104,y+15,AMBER,'en')
            meaning = self.fit(cue['vocab']['meaning'],650,30,21,16,'zh',1)
            self.block(d,meaning,510,y+19,WHITE,'zh')
            sentence = self.fit(cue['en'],1060,24,15,12,'en',1)
            self.block(d,sentence,105,y+56,MUTED,'en')
        self.text(d,(84,621),'A SMALL CLUE. A DIFFERENT STORY.',14,AMBER,'bold')
        self.text(d,(84,668),self.r.data.get('disclosure',''),11,MUTED,'en')
        image.alpha_composite(layer)
        return image.convert('RGB')
