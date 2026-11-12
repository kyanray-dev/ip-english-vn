"""Code-drawn jade, rice paper and cloud ornaments; no generated UI assets."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from dialogue_ui import (DialogueUI, normalized, phrase_indices,
                         INK, JADE, GOLD, LIGHT_GOLD, SECONDARY)


class JadePaperUI(DialogueUI):
    def diamond(self, draw, x, y, radius=4, fill=None):
        points = [(x, y-radius), (x+radius, y), (x, y+radius), (x-radius, y), (x, y-radius)]
        if fill:
            draw.polygon([self.point(p) for p in points], fill=fill)
        self.line(draw, points, LIGHT_GOLD)

    def cloud(self, draw, x, y, sx=1, sy=1, fill=GOLD):
        """Small engraved cloud curl with an outer tail; sampled vector paths."""
        points = []
        for theta in np.linspace(0, 2.6 * math.pi, 80):
            radius = 1.2 + theta * 1.15
            points.append((x + sx * (12 + radius * math.cos(theta)),
                           y + sy * (12 + radius * math.sin(theta))))
        self.line(draw, points, fill, 1.3)
        self.line(draw, [(x, y+sy*25), (x+sx*11, y+sy*25),
                         (x+sx*25, y+sy*18), (x+sx*35, y+sy*18)], fill, 1.3)

    def make_base(self):
        layer = Image.new('RGBA', self.r.size)
        shadow = Image.new('RGBA', self.r.size)
        self.r.rect(ImageDraw.Draw(shadow), (30, 502, 1253, 686), (0, 0, 0, 125), 10)
        layer.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(9 * self.s)))
        # Procedural fibers and broad, quiet variations; seeded once, never per frame.
        width, height = self.point((1216, 180))
        rng = np.random.default_rng(725)
        yy, xx = np.mgrid[:height, :width]
        grain = (rng.normal(0, 1.1, (height, width)) +
                 1.5 * np.sin(xx / (19 * self.s) + np.sin(yy / (7 * self.s))) +
                 .8 * np.sin((xx + yy) / (3 * self.s)))
        pixels = np.clip(np.array([240, 228, 205]) + grain[..., None], 0, 255).astype('uint8')
        paper = Image.fromarray(pixels).convert('RGBA')
        layer.alpha_composite(paper, self.point((32, 497)))
        d = ImageDraw.Draw(layer)
        for x0, y0, x1, y1, color in [(32,497,1248,677,LIGHT_GOLD), (35,500,1245,674,GOLD), (39,504,1241,670,'#c2a46b')]:
            self.r.rect(d, (x0,y0,x1,y1), None, 7, color, 1)
        # Pale mountain silhouettes only at the foot of the scroll.
        mountains = Image.new('RGBA', self.r.size)
        md = ImageDraw.Draw(mountains)
        for n in range(3):
            points = [(188, 668)]
            for x in range(188, 1240, 6):
                y = 660 - n * 4 - 6 * math.sin(x * .025 + n * 2) - 5 * math.sin(x * .061 + n)
                points.append((x, y))
            points.append((1238, 668))
            md.polygon([self.point(p) for p in points], fill=(109, 111, 96, 13))
        layer.alpha_composite(mountains)
        d = ImageDraw.Draw(layer)
        for x, y, sx, sy in [(41,506,1,1), (1239,506,-1,1), (41,668,1,-1), (1239,668,-1,-1)]:
            self.cloud(d, x, y, sx, sy)
        # Jade plaque: cut corners, carved border, restrained mineral grain.
        pw, ph = self.point((132, 181))
        jy, jx = np.mgrid[:ph, :pw]
        vein = 3 * np.sin(jx / (12 * self.s) + np.sin(jy / (20 * self.s)))
        jade = np.clip(np.array([48, 75, 62]) + vein[..., None] +
                       rng.normal(0, 1, (ph, pw, 1)), 0, 255).astype('uint8')
        plaque = Image.fromarray(jade).convert('RGBA')
        shape = [(0,18),(14,3),(38,3),(49,0),(118,14),(132,29),(132,161),(112,176),(16,181),(0,165)]
        mask = Image.new('L', (pw, ph))
        ImageDraw.Draw(mask).polygon([self.point(p) for p in shape], fill=255)
        plaque.putalpha(mask)
        layer.alpha_composite(plaque, self.point((51, 486)))
        self.line(d, [(51+x,486+y) for x,y in shape+[shape[0]]], LIGHT_GOLD, 2)
        self.line(d, [(57,510),(67,497),(90,496),(100,493),(165,505),(177,519),(177,643),(160,657),(69,660),(57,648),(57,510)], '#8d9b73', 1)
        self.cloud(d, 80, 482, 1.3, 1.0, '#b2bea0')
        self.cloud(d, 162, 657, -1.3, -1.0, '#a5b092')
        # Suspended jade bead and fine silk tassel.
        self.line(d, [(68,519),(64,559)], GOLD, 1.5)
        d.ellipse(self.point((57,550,71,567)), fill='#a7b89a', outline=LIGHT_GOLD, width=max(1,round(self.s)))
        for n in range(7):
            self.line(d, [(64,568),(59+n*1.7,610+math.sin(n)*3)], '#c1a56e', .7)
        return layer

    def draw(self, image, cue, index, t, chinese=True):
        image.alpha_composite(self.base)
        d = ImageDraw.Draw(image)
        # Unboxed title and scene label leave the center of the stage open.
        self.block(d, self.heading, 40, 20, LIGHT_GOLD, 'zh_serif')
        title_width = self.r.measure(self.heading['lines'][0], self.heading['size'], 'zh_serif')
        seal_x = 53 + title_width
        self.r.rect(d, (seal_x,22,seal_x+19,45), '#763b2c', 2, '#bf7760')
        self.text(d, (seal_x+3,26), '卷', 13, '#ebbaa1', 'zh_serif')
        self.line(d, [(40,65),(77,65)], LIGHT_GOLD)
        self.diamond(d, 80,65,2)
        self.block(d, self.scene_labels[cue['id']], 91, 57, LIGHT_GOLD, 'zh_serif')
        self.text(d, (1122,27), self.r.data['level'] + ' · EN', 17, LIGHT_GOLD)
        self.line(d, [(1077,36),(1108,36)], LIGHT_GOLD)
        self.line(d, [(1212,36),(1245,36)], LIGHT_GOLD)
        name, english_name = self.names[cue['speaker']]
        name_y = 535 if len(name['lines']) == 1 else 518
        end = self.block(d, name, 0, name_y, '#f4dfae', 'zh_serif', center=122)
        self.block(d, english_name, 0, end+12, '#f4dfae', 'serif', center=122)
        self.draw_words(d, cue, t, chinese)
        if cue.get('vocab'):
            self.line(d, [(940,515),(940,565)], GOLD)
            self.cloud(d, 930,574,.55,.55)
            self.line(d, [(940,601),(940,655)], GOLD)
            self.text(d, (968,510), '词笺', 17, '#70542c', 'zh_serif')
            y = 536
            for key, field, kind, fill in self.layouts[cue['id']]['vocab']:
                if field['lines']:
                    y = self.block(d, field, 968, y, fill, kind) + 4
        self.diamond(d, 1223,651,5, GOLD)
        # Thin gold progression with chapter-like diamond markers.
        self.line(d, [(390,700),(890,700)], '#8d8267')
        fraction = max(0,min(1,t/self.r.data['duration']))
        self.line(d, [(390,700),(390+500*fraction,700)], LIGHT_GOLD)
        for n in range(6):
            self.diamond(d, 455+n*74,700,4, LIGHT_GOLD if fraction >= n/5 else '#253d35')

    def choice(self, draw, cue, t):
        self.r.rect(draw, (368,143,912,475), '#eee1c7', 5, GOLD, 2)
        self.r.rect(draw, (374,149,906,469), None, 3, '#c8ac77')
        self.text(draw, (398,164), '抉择 · YOUR TURN', 19, JADE, 'zh_serif')
        self.text(draw, (398,202), 'Read the clue. Make a choice.', 22)
        self.text(draw, (398,236), '暂停想一想，再继续剧情', 16, SECONDARY, 'zh')
        for n, option in enumerate(cue['options']):
            y = 270+n*83
            selected = t >= cue['end']-1.5 and n == cue['answer']
            self.r.rect(draw, (392,y,888,y+78), '#d0ddc8' if selected else '#e7d7b9', 3, GOLD)
            self.text(draw, (407,y+13), 'AB'[n], 21, JADE)
            layout = self.fit(option['en'],420,44,21,17,'serif',2)
            end = self.block(draw,layout,440,y+8,JADE if selected else INK)
            zh_layout = self.fit(option['zh'],420,24,16,13,'zh',1)
            self.block(draw,zh_layout,440,max(y+45,end+2),SECONDARY,'zh')
        remaining = max(0,math.ceil(cue['end']-t-1.5))
        self.text(draw, (398,448), f'{remaining:02d} s · ' + ('CLUE FOUND' if not remaining else 'THINK IN ENGLISH'), 12, JADE, 'en')
