"""Shared measured layout and baseline-safe timed text for all visual themes."""
import math
import re

INK = '#302b22'
JADE = '#244d43'
GOLD = '#a77b35'
LIGHT_GOLD = '#e4c88e'
SECONDARY = '#665e4e'


def normalized(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())


def phrase_indices(tokens, phrase):
    """Underline occurrences of the whole expression, not unrelated words."""
    words = [normalized(token) for token in tokens]
    target = [normalized(token) for token in phrase.split()]
    if not target:
        return set()
    return {i + j for i in range(len(words) - len(target) + 1)
            if words[i:i + len(target)] == target for j in range(len(target))}


class DialogueUI:
    FONT_KIND = 'serif'
    NAME_FONT = 'zh_serif'
    MAX_SIZE = 34
    TEXT_COLOR = INK
    ACTIVE_COLOR = JADE
    SECONDARY_COLOR = SECONDARY
    UNDERLINE_COLOR = GOLD
    LEFT = 220
    TOP = 520
    BOTTOM = 666
    DIVIDER = 940

    def __init__(self, renderer):
        self.r = renderer
        self.s = renderer.scale
        self.layouts = {}
        self.names = {}
        self.scene_labels = {}
        for who, character in renderer.data['characters'].items():
            self.names[who] = (
                self.fit(character['zh'], 108, 68, 32, 17, self.NAME_FONT, 2),
                self.fit(character['name'], 108, 34, 16, 11, 'serif', 2),
            )
        self.heading = self.fit(renderer.data['title_zh'], 850, 37, 27, 19, self.NAME_FONT, 1)
        for cue in renderer.data['lines']:
            try:
                self.layouts[cue['id']] = self.layout(cue)
                self.scene_labels[cue['id']] = self.fit(
                    renderer.data.get('scene_label') or cue.get('act', ''),
                    850, 23, 15, 12, self.NAME_FONT, 1)
                for option in cue.get('options', []):
                    self.fit(option['en'], 420, 44, 21, 17, 'serif', 2)
                    self.fit(option['zh'], 420, 24, 16, 13, 'zh', 1)
            except ValueError as error:
                raise ValueError(f'Dialogue overflow: {cue["id"]}: {error}') from error
        self.base = self.make_base()

    def point(self, xy):
        return tuple(round(v * self.s) for v in xy)

    def line(self, draw, points, fill=GOLD, width=1):
        draw.line([self.point(p) for p in points], fill=fill,
                  width=max(1, round(width * self.s)), joint='curve')

    def text(self, draw, xy, text, size, fill=INK, kind='serif', **kwargs):
        self.r.txt(draw, xy, text, size, fill, kind, anchor='lt', **kwargs)

    def fit(self, text, width, height, maximum, minimum, kind, max_lines):
        for size in range(maximum, minimum - 1, -1):
            lines = self.r.wrap(text, width, size, kind)
            if (len(lines) <= max_lines and len(lines) * size * 1.22 <= height
                    and all(self.r.measure(line, size, kind) <= width for line in lines)):
                return {'size': size, 'lines': lines, 'height': len(lines) * size * 1.22}
        raise ValueError(f'text does not fit; shorten it: {text[:60]}')

    def block(self, draw, layout, x, y, fill=INK, kind='serif', center=None):
        for line in layout['lines']:
            left = x if center is None else center - self.r.measure(line, layout['size'], kind) / 2
            self.text(draw, (left, y), line, layout['size'], fill, kind)
            y += layout['size'] * 1.22
        return y

    def layout(self, cue):
        vocab = cue.get('vocab')
        right = 912 if vocab else 1212
        width = right - self.LEFT
        # Keep a short question and reply on separate lines, as in the approved mockup.
        for size in range(self.MAX_SIZE, 23, -1):
            sentences = re.split(r'(?<=[.!?])\s+', cue['en'])
            rows = (sentences if len(sentences) == 2 and
                    all(self.r.measure(row, size, self.FONT_KIND) <= width for row in sentences)
                    else self.r.wrap(cue['en'], width, size, self.FONT_KIND))
            if (len(rows) * size * 1.22 <= 100 and
                    all(self.r.measure(row, size, self.FONT_KIND) <= width for row in rows)):
                break
        else:
            raise ValueError('English dialogue; split into shorter cues')
        words = []
        for n, row in enumerate(rows):
            x = self.LEFT
            for word in row.split():
                w = self.r.measure(word, size, self.FONT_KIND)
                words.append((word, x, self.TOP + n * size * 1.22, w))
                x += w + self.r.measure(' ', size, self.FONT_KIND)
        chinese_y = max(615, self.TOP + len(rows) * size * 1.22 + 10)
        chinese = self.fit(cue['zh'], width, self.BOTTOM - chinese_y, 19, 16, 'zh', 2)
        # Keep the designed cap-height top, but share one typographic baseline.
        # A per-word 'lt' anchor aligns ink bounds: "young" then sits higher
        # than "that". The fixed font metric is independent of token and highlight.
        baseline_offset_px = -self.r.f(size, self.FONT_KIND).getbbox('H', anchor='ls')[1]
        result = {'words': words, 'size': size, 'right': right,
                  'baseline_offset_px': baseline_offset_px,
                  'chinese': chinese, 'chinese_y': chinese_y,
                  'underline': phrase_indices([w[0] for w in words], vocab['term']) if vocab else set()}
        if vocab:
            for term_size in range(25, 18, -1):
                fields = [
                    ('term', self.fit(vocab['term'], 253, 62, term_size, 19, self.FONT_KIND, 2), self.FONT_KIND, self.ACTIVE_COLOR),
                    ('ipa', self.fit(vocab.get('ipa', ''), 253, 30, 12, 11, 'en', 2), 'en', self.SECONDARY_COLOR),
                    ('meaning', self.fit(vocab['meaning'], 253, 44, 18, 16, 'zh', 2), 'zh', self.TEXT_COLOR),
                    ('note', self.fit(vocab.get('note', ''), 253, 34, 13, 11, 'zh', 2), 'zh', self.SECONDARY_COLOR),
                ]
                if sum(field['height'] + 4 for _, field, _, _ in fields if field['lines']) <= 130:
                    result['vocab'] = fields
                    break
            else:
                raise ValueError('vocabulary margin; shorten the term, meaning or note')
        return result

    def draw_highlight(self, d, x, y, width, size):
        # Ragged, deterministic brush wash instead of a rounded UI pill.
        top = [(x-5+j*(width+10)/12, y-2+math.sin(j*2.3)*1.7) for j in range(13)]
        bottom = [(x-5+j*(width+10)/12, y+size+3+math.sin(j*2.7)*1.5) for j in reversed(range(13))]
        d.polygon([self.point(p) for p in top+bottom], fill='#abc6b5')

    def draw_words(self, d, cue, t, chinese=True):
        layout = self.layouts[cue['id']]
        spoken = t - cue['audio_start']
        offset = 0
        hit = None
        for word in cue['words']:
            if word['start'] <= spoken < word['end']:
                count = 0
                for k, (token, _, _, _) in enumerate(layout['words']):
                    length = len(normalized(token))
                    if count <= offset < count + length:
                        hit = k
                        break
                    count += length
                break
            offset += len(normalized(word['text']))
        size = layout['size']
        for k, (token, x, y, width) in enumerate(layout['words']):
            if k == hit:
                self.draw_highlight(d, x, y, width, size)
            d.text((round(x*self.s), round(y*self.s) + layout['baseline_offset_px']),
                   token, font=self.r.f(size, self.FONT_KIND), fill=self.ACTIVE_COLOR if k == hit else self.TEXT_COLOR,
                   anchor='ls')
            if k in layout['underline']:
                self.line(d, [(x,y+size+4),(x+width,y+size+4)], self.UNDERLINE_COLOR, 1.3)
        if chinese:
            self.block(d, layout['chinese'], self.LEFT, layout['chinese_y'], self.SECONDARY_COLOR, 'zh')
