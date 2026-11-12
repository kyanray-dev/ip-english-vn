import copy,importlib.util,json,sys,unittest,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from prepare import validate
from render import Renderer

class EpisodeContractTests(unittest.TestCase):
    def setUp(self):
        self.folder=ROOT/'examples/genshin';self.data=json.loads((self.folder/'episode.json').read_text())
    def test_bundled_episode_valid(self):validate(self.data,self.folder)
    def test_duplicate_id_rejected(self):
        self.data['lines'][1]['id']=self.data['lines'][0]['id']
        with self.assertRaisesRegex(ValueError,'duplicate ID'):validate(self.data,self.folder)
    def test_offstage_speaker_rejected(self):
        self.data['lines'][1]['stage']=[]
        with self.assertRaisesRegex(ValueError,'on stage'):validate(self.data,self.folder)
    def test_out_of_root_asset_rejected(self):
        self.data['background']='../../../../etc/passwd'
        with self.assertRaisesRegex(ValueError,'escapes'):validate(self.data,self.folder)
    def test_invalid_choice_rejected(self):
        next(l for l in self.data['lines'] if l.get('type')=='choice')['answer']=4
        with self.assertRaisesRegex(ValueError,'valid answer'):validate(self.data,self.folder)
    def test_nonexistent_vocab_rejected(self):
        self.data['lines'][0]['vocab']['term']='a phrase that is absent'
        with self.assertRaisesRegex(ValueError,'occur in dialogue'):validate(self.data,self.folder)
    def test_missing_review_term_rejected(self):
        self.data['review_terms']=['missing','against','let it go']
        with self.assertRaisesRegex(ValueError,'3 existing'):validate(self.data,self.folder)
    def test_stage_side_collision_rejected(self):
        self.data['characters']['venti']['side']='left'
        with self.assertRaisesRegex(ValueError,'distinct sides'):validate(self.data,self.folder)
    def test_renderer_generic_metadata_and_no_prop(self):
        d=json.loads((self.folder/'timeline.json').read_text());d['ip']='A Different World';d['title']='A New Mystery';d['prop']=None;d['ending_title']='A promise kept.';d['review_terms']=['at dusk','faint','counts as']
        # Reuse artwork only to test that rendering does not require sample-specific metadata.
        r=Renderer(d,self.folder,1280)
        for t in [0,17,62,d['outro_start']+1]:self.assertEqual(r.frame(t).size,(1280,720))
    def test_payload_cannot_close_script_element(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            path=Path(td);d={'title':'</script><script>alert(1)</script>'};(path/'timeline.json').write_text(json.dumps(d))
            subprocess.run([sys.executable,str(ROOT/'scripts/package_player.py'),str(path/'timeline.json'),'--out',str(path/'out')],check=True,capture_output=True)
            html=(path/'out/index.html').read_text();self.assertNotIn('"title": "</script>',html)

if __name__=='__main__':unittest.main()
