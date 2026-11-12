"""Regression cases for a reusable dialogue UI, beyond the approved short line."""
import copy
import json
from pathlib import Path
import sys
import unittest

from PIL import ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from jade_paper import phrase_indices
from render import Renderer


class DialogueUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = ROOT / 'examples/genshin'
        cls.data = json.loads((cls.folder / 'timeline.json').read_text())
        cls.renderer = Renderer(cls.data, cls.folder, 1280)

    def test_bundled_dialogue_fits_at_delivery_and_preview_sizes(self):
        for width in (640, 1280, 1920):
            r = self.renderer if width == 1280 else Renderer(self.data, self.folder, width)
            for cue in self.data['lines']:
                layout = r.ui.layouts[cue['id']]
                self.assertEqual(' '.join(w[0] for w in layout['words']), cue['en'])
                for _, x, y, w in layout['words']:
                    self.assertGreaterEqual(x, 220)
                    self.assertLessEqual(x + w, layout['right'])
                    self.assertLess(y + layout['size'] + 4, layout['chinese_y'])
                self.assertLessEqual(layout['chinese_y'] + layout['chinese']['height'], 666)
                if cue.get('vocab'):
                    end = 536 + sum(field['height'] + 4 for _, field, _, _ in layout['vocab'] if field['lines'])
                    self.assertLessEqual(end, 666)

    def test_wrapped_dialogue_preserves_all_text_and_separates_vocabulary(self):
        d = copy.deepcopy(self.data)
        cue = d['lines'][0]
        cue['en'] = 'Some young people mistake fear for wisdom. The careful ones live long enough to learn the difference.'
        cue['zh'] = '有些年轻人，总把胆怯当成智慧。谨慎之人，总能活到弄清两者区别的时候。'
        cue['vocab'] = {'term': 'mistake fear for wisdom', 'ipa': '/mɪˈsteɪk fɪə fə ˈwɪzdəm/',
                        'meaning': '把恐惧误认为智慧', 'note': 'mistake A for B：把 A 误当成 B'}
        r = Renderer(d, self.folder, 1280)
        layout = r.ui.layouts[cue['id']]
        self.assertEqual(' '.join(w[0] for w in layout['words']), cue['en'])
        self.assertGreater(len({w[2] for w in layout['words']}), 1)
        self.assertLessEqual(max(x+w for _,x,_,w in layout['words']), 912)
        self.assertEqual(''.join(layout['chinese']['lines']), cue['zh'])

    def test_overflow_fails_instead_of_clipping(self):
        for field, value in [('en', 'W' * 160), ('zh', '无法放入对白框的长句' * 30)]:
            with self.subTest(field=field):
                d = copy.deepcopy(self.data)
                d['lines'][0][field] = value
                with self.assertRaisesRegex(ValueError, 'Dialogue overflow'):
                    Renderer(d, self.folder, 640)

    def test_underlining_matches_complete_phrases_and_punctuation(self):
        words = "Let it go. It is time to let it go!".split()
        self.assertEqual(phrase_indices(words, 'let it go'), {0,1,2,7,8,9})
        self.assertEqual(phrase_indices('Fear is fear; wisdom is wisdom.'.split(), 'fear for wisdom'), set())

    def test_chinese_switch_changes_only_caption_region(self):
        cue = self.data['lines'][0]
        t = cue['audio_start'] + .5
        diff = ImageChops.difference(self.renderer.frame(t, True), self.renderer.frame(t, False))
        bounds = diff.getbbox()
        self.assertIsNotNone(bounds)
        self.assertGreaterEqual(bounds[0], 220)
        self.assertGreaterEqual(bounds[1], 615)
        self.assertLessEqual(bounds[2], 912)
        self.assertLessEqual(bounds[3], 666)

    def test_real_word_timing_changes_only_active_word_in_dialogue(self):
        cue = self.data['lines'][0]
        word = cue['words'][0]
        before = self.renderer.frame(cue['audio_start'] - .05).crop((220,510,912,612))
        during = self.renderer.frame(cue['audio_start'] + (word['start']+word['end'])/2).crop((220,510,912,612))
        bounds = ImageChops.difference(before, during).getbbox()
        self.assertIsNotNone(bounds)
        first = self.renderer.layouts[cue['id']][0]
        self.assertLessEqual(bounds[2], first[3] + 7)

    def test_paper_and_frames_are_deterministic(self):
        another = Renderer(self.data, self.folder, 1280)
        self.assertIsNone(ImageChops.difference(self.renderer.frame(12), another.frame(12)).getbbox())


if __name__ == '__main__':
    unittest.main()
