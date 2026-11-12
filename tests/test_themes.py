"""Theme selection, old-input compatibility and complete visual-novel states."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare import validate
from render import Renderer
from themes import resolve_theme


class ThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = ROOT / 'examples/genshin'
        cls.data = json.loads((cls.folder/'timeline.json').read_text())

    def test_auto_selects_ip_and_preserves_existing_default(self):
        for ip in ['名侦探柯南', 'Detective Conan', 'Case Closed', '福尔摩斯', 'Sherlock Holmes']:
            self.assertEqual(resolve_theme({'ip': ip}), 'mystery')
        for ip in ['原神', '凡人修仙传', 'A Different World']:
            self.assertEqual(resolve_theme({'ip': ip}), 'jade-paper')
        self.assertEqual(resolve_theme(self.data), 'jade-paper')

    def test_explicit_theme_overrides_ip(self):
        self.assertEqual(resolve_theme({'ip': 'Conan', 'ui_theme': 'jade-paper'}), 'jade-paper')
        self.assertEqual(resolve_theme({'ip': '原神', 'ui_theme': 'mystery'}), 'mystery')

    def test_unknown_theme_is_rejected_during_input_validation(self):
        for value in ['mistery', '', None, {}, True]:
            data = copy.deepcopy(self.data)
            data['ui_theme'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'ui_theme'):
                validate(data, self.folder)

    def test_all_states_render_in_each_theme(self):
        for theme in ['jade-paper', 'mystery']:
            data = copy.deepcopy(self.data)
            data['ui_theme'] = theme
            r = Renderer(data, self.folder, 640)
            choice = next(c for c in data['lines'] if c.get('type') == 'choice')
            times = [0, data['lines'][0]['audio_start'], data['lines'][1]['start']+.2,
                     choice['start']+1, choice['end']-.5, data['outro_start']+1]
            for t in times:
                for zh in (False, True):
                    with self.subTest(theme=theme,time=t,zh=zh):
                        self.assertEqual(r.frame(t,zh).size,(640,360))
            pixel = r.frame(data['lines'][0]['audio_start']).getpixel((150,330))
            self.assertTrue(min(pixel)>150 if theme=='jade-paper' else max(pixel)<65)

    def test_child_sprite_height_is_used_and_invalid_sizes_fail(self):
        data = copy.deepcopy(self.data)
        who = next(who for who,c in data['characters'].items() if 'sprite' in c)
        data['characters'][who]['sprite_height'] = 455
        validate(data,self.folder)
        self.assertEqual(Renderer(data,self.folder,1280).sprites[who][0].height,455)
        for height in [0,641,'455',True]:
            data['characters'][who]['sprite_height'] = height
            with self.subTest(height=height), self.assertRaisesRegex(ValueError,'sprite_height'):
                validate(data,self.folder)


if __name__ == '__main__':
    unittest.main()
