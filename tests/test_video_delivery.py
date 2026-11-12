"""Exercise the real code renderer and the single-video publication boundary."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build

class VideoDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work=tempfile.TemporaryDirectory(prefix='vn-delivery-test-')
        cls.addClassCleanup(cls.work.cleanup)
        cls.base=Path(cls.work.name)
        cls.episode=cls.base/'source'
        shutil.copytree(ROOT/'examples/genshin',cls.episode)
        data=json.loads((cls.episode/'episode.json').read_text())
        data['lines']=data['lines'][:3]
        data['review_terms']=[l['vocab']['term'] for l in data['lines']]
        (cls.episode/'episode.json').write_text(json.dumps(data,ensure_ascii=False))
        cls.out=cls.base/'delivery'
        cls.built=subprocess.run([sys.executable,str(ROOT/'scripts/build.py'),str(cls.episode/'episode.json'),'--out',str(cls.out),'--width','640','--fps','6'],capture_output=True,text=True,check=True)

    def test_build_publishes_only_playable_video(self):
        self.assertEqual([p.name for p in self.out.iterdir()],['episode.mp4'])
        info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(self.out/'episode.mp4')]))
        self.assertEqual([s['codec_type'] for s in info['streams']],['video','audio','subtitle','subtitle'])
        self.assertEqual(info['streams'][0]['codec_name'],'h264')
        self.assertGreater(float(info['format']['duration']),20)
        self.assertIn('video_only_delivery',self.built.stdout)
        self.assertNotIn('SPEECH ',self.built.stdout,'Existing voice cache should be reused')

    def test_direct_english_render_has_no_sidecars(self):
        out=self.base/'english-video'
        subprocess.run([sys.executable,str(ROOT/'scripts/render.py'),str(self.episode/'timeline.json'),'--out',str(out),'--width','640','--fps','6','--no-chinese'],capture_output=True,text=True,check=True)
        self.assertEqual([p.name for p in out.iterdir()],['episode.mp4'])

    def test_verifier_rejects_extra_deliverables_without_writing_report(self):
        out=self.base/'with-sidecar';out.mkdir()
        shutil.copy2(self.out/'episode.mp4',out/'episode.mp4')
        (out/'novel.txt').write_text('Do not delete this file.')
        result=subprocess.run([sys.executable,str(ROOT/'scripts/verify.py'),str(self.episode/'timeline.json'),'--out',str(out)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Output must contain only episode.mp4',result.stdout)
        self.assertEqual({p.name for p in out.iterdir()},{'episode.mp4','novel.txt'})

    def test_build_refuses_mixed_directory_before_starting_work(self):
        out=self.base/'user-files';out.mkdir();(out/'notes.txt').write_text('Keep me.')
        with mock.patch.object(sys,'argv',['build.py',str(self.episode/'episode.json'),'--out',str(out)]),mock.patch.object(build.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'use a new directory'):build.main()
            run.assert_not_called()
        self.assertEqual((out/'notes.txt').read_text(),'Keep me.')

    def test_validation_failure_preserves_existing_video_and_cleans_staging(self):
        out=self.base/'existing';out.mkdir();(out/'episode.mp4').write_bytes(b'previous video')
        staging=[]
        def simulate(args,**kwargs):
            name=Path(args[1]).name
            if name=='render.py':
                folder=Path(args[args.index('--out')+1]);folder.mkdir()
                (folder/'episode.mp4').write_bytes(b'unverified replacement');staging.append(folder.parent)
            if name=='verify.py':raise subprocess.CalledProcessError(1,args)
            return subprocess.CompletedProcess(args,0)
        with mock.patch.object(sys,'argv',['build.py',str(self.episode/'episode.json'),'--out',str(out)]),mock.patch.object(build.subprocess,'run',side_effect=simulate):
            with self.assertRaises(subprocess.CalledProcessError):build.main()
        self.assertEqual((out/'episode.mp4').read_bytes(),b'previous video')
        self.assertEqual([p.name for p in out.iterdir()],['episode.mp4'])
        self.assertTrue(staging)
        self.assertTrue(all(not p.exists() for p in staging))

if __name__=='__main__':unittest.main()
