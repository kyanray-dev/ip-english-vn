#!/usr/bin/env python3
"""Local-only video preview server with byte ranges for reliable seeking."""
import argparse,functools,http.server,os,re
from pathlib import Path
class RangeHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        path=self.translate_path(self.path);self.byte_range=None
        if not os.path.isfile(path) or 'Range' not in self.headers:return super().send_head()
        size=os.path.getsize(path);m=re.fullmatch(r'bytes=(\d*)-(\d*)',self.headers['Range'])
        if not m:self.send_error(416);return None
        if m[1]:start=int(m[1]);end=min(int(m[2]) if m[2] else size-1,size-1)
        else:start=max(0,size-int(m[2] or 0));end=size-1
        if start>end or start>=size:self.send_error(416);return None
        f=open(path,'rb');f.seek(start);self.byte_range=(start,end)
        self.send_response(206);self.send_header('Content-Type',self.guess_type(path));self.send_header('Content-Length',str(end-start+1));self.send_header('Content-Range',f'bytes {start}-{end}/{size}');self.send_header('Accept-Ranges','bytes');self.end_headers();return f
    def copyfile(self,source,outputfile):
        remaining=self.byte_range[1]-self.byte_range[0]+1 if self.byte_range else None
        try:
            while remaining is None or remaining>0:
                block=source.read(65536 if remaining is None else min(65536,remaining))
                if not block:break
                outputfile.write(block)
                if remaining is not None:remaining-=len(block)
        except (BrokenPipeError,ConnectionResetError):pass
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--port',type=int,default=8000);a=p.parse_args()
    print(f'Open http://127.0.0.1:{a.port}',flush=True)
    http.server.ThreadingHTTPServer(('127.0.0.1',a.port),functools.partial(RangeHandler,directory=str(a.directory))).serve_forever()
