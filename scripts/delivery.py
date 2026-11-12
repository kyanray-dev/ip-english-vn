"""Keep final output limited to one video and publish it atomically."""
import os
import shutil
import tempfile
from pathlib import Path

def require_video_output(out, complete=False):
    out=Path(out)
    if out.exists():
        if not out.is_dir():raise ValueError('Output must be a directory')
        extras=sorted(p.name for p in out.iterdir() if p.name!='episode.mp4')
        if extras:raise ValueError('Output must contain only episode.mp4; use a new directory. Found: '+', '.join(extras))
        video=out/'episode.mp4'
        if video.is_symlink() or (video.exists() and not video.is_file()):
            raise ValueError('episode.mp4 must be a regular file')
    if complete and (not (out/'episode.mp4').is_file() or not (out/'episode.mp4').stat().st_size):
        raise ValueError('Missing or empty episode.mp4')

def publish_video(source,out):
    out=Path(out);require_video_output(out)
    out.mkdir(parents=True,exist_ok=True)
    # A sibling temporary directory keeps copy/rename on the output filesystem,
    # without exposing partial files or sidecars inside the delivery directory.
    with tempfile.TemporaryDirectory(prefix='.'+out.name+'-publish-',dir=out.parent) as tmp:
        staging=Path(tmp)/'episode.mp4';shutil.copyfile(source,staging)
        require_video_output(out)
        os.replace(staging,out/'episode.mp4')
    return out/'episode.mp4'
