"""DW Social Media Windows localhost application; no website write endpoints."""
import os,sys,json,secrets,threading,mimetypes,webbrowser,io,zipfile,sqlite3,argparse
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs,unquote
APP=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8786);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
CONFIG=APP/'config.json'
config=json.loads(CONFIG.read_text('utf-8-sig')) if CONFIG.exists() else {}
panel=Path(config.get('panel_path','')).expanduser()
os.environ.setdefault('DW_PANEL',str((panel if panel.is_absolute() else APP/panel).resolve()))
os.environ.setdefault('DW_SOCIAL_DATA',str(APP/'data'))
from dw_social import engine as e,service as s
s.init()
TOKEN=secrets.token_urlsafe(32);LOCK=threading.RLock();ORIGIN=f'http://127.0.0.1:{args.port}';PHOTO_SRCS=set()
def safe(root,src):
 root=Path(root).resolve();p=(root/src).resolve()
 if not p.is_relative_to(root):raise ValueError('Niedozwolona ścieżka')
 return p
from functools import lru_cache
from PIL import Image, ImageOps
@lru_cache(maxsize=64)
def thumbnail(path,mtime):
 with Image.open(path) as im:
  im=ImageOps.exif_transpose(im);im.thumbnail((480,480));buf=io.BytesIO();im.convert('RGB').save(buf,'WEBP',quality=80);return buf.getvalue()
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def send(self,content,typ='application/json; charset=utf-8',code=200,attachment=None,cache=False):
  if not isinstance(content,bytes):content=json.dumps(content,ensure_ascii=False).encode()
  self.send_response(code);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(content)));self.send_header('Cache-Control','private, max-age=300' if cache else 'no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
  self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'nonce-"+TOKEN+"'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors http://127.0.0.1:8765; base-uri 'none'; form-action 'self'")
  if attachment:self.send_header('Content-Disposition','attachment; filename="'+attachment+'"')
  self.end_headers()
  try:self.wfile.write(content)
  except (ConnectionAbortedError,ConnectionResetError,BrokenPipeError):pass
 def valid_host(self):return self.headers.get('Host')==f'127.0.0.1:{args.port}'
 def do_GET(self):
  try:
   if not self.valid_host():return self.send({'error':'Nieprawidłowy host'},code=403)
   u=urlsplit(self.path);q=parse_qs(u.query);path=unquote(u.path)
   if path=='/':return self.send((APP/'ui/index.html').read_text('utf-8').replace('%%TOKEN%%',TOKEN).encode(),'text/html; charset=utf-8')
   if path.startswith('/ui/'):
    p=safe(APP/'ui',path[4:]);return self.send(p.read_bytes(),mimetypes.guess_type(p.name)[0] or 'application/octet-stream')
   if path=='/api/health':return self.send({'ok':True,'version':'2.0.0','app':str(APP)})
   if path=='/favicon.ico':return self.send(b'',code=204)
   if path=='/api/state':
    with LOCK:
     result=s.state(q.get('month',[''])[0]);PHOTO_SRCS.update(x['src'] for x in result['library']['photos']);return self.send(result)
   if path=='/api/export':return self.send(s.export(q['kind'][0],q.get('month',[''])[0]),'text/csv; charset=utf-8',attachment='DW-'+q['kind'][0]+'.csv')
   if path=='/api/backup':
    with LOCK:
     buf=io.BytesIO();snapshot=e.OWN.parent/'backup-snapshot.sqlite3'
     with e.own() as c:
      dest=sqlite3.connect(snapshot);c.backup(dest);dest.close()
     with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
      z.write(snapshot,'dw-social.sqlite3')
      for p in (e.OWN.parent/'dw-social-uploads').glob('*'):z.write(p,'dw-social-uploads/'+p.name)
     snapshot.unlink();return self.send(buf.getvalue(),'application/zip',attachment='DW-Social-Media-kopia.zip')
   if path=='/api/image':
    src=q['src'][0]
    if src not in PHOTO_SRCS:raise ValueError('Zdjęcie nie należy do biblioteki')
    p=e.photo_path(src)
    if p is None:raise ValueError('Plik zdjęcia jest niedostępny')
    if q.get('thumb')==['1']:return self.send(thumbnail(str(p),p.stat().st_mtime_ns),'image/webp',cache=True)
    return self.send(p.read_bytes(),mimetypes.guess_type(p.name)[0] or 'application/octet-stream',cache=True)
   if path=='/api/post-package':
    with e.own() as c:
     p=c.execute('SELECT p.*,s.at,s.photos as selected_photos FROM pool p LEFT JOIN posts s ON s.pool_id=p.id WHERE p.id=?',(int(q['id'][0]),)).fetchone()
     if not p:raise ValueError('Nie znaleziono posta')
     buf=io.BytesIO()
     with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
      z.writestr('OPIS.txt',p['caption']);z.writestr('PUBLIKACJA.txt',f"{p['platform']}\n{p['product']}\n{p['at'] or 'Termin nieustalony'}\n")
      for i,src in enumerate(json.loads(p['selected_photos'] or p['photos']),1):
       photo=e.photo_path(src)
       if photo is None:raise ValueError('Brakuje zdjęcia: '+src)
       z.write(photo,f'{i:02d}'+photo.suffix)
     return self.send(buf.getvalue(),'application/zip',attachment=f'DW-post-{p["id"]}.zip')
   return self.send({'error':'Nie znaleziono'},code=404)
  except (ValueError,KeyError,TypeError,FileNotFoundError,sqlite3.Error) as ex:return self.send({'error':str(ex)},code=400)
 def do_POST(self):
  try:
   if not self.valid_host() or self.headers.get('X-DW-Token')!=TOKEN or self.headers.get('Origin') not in (None,ORIGIN):return self.send({'error':'Odmowa dostępu. Odśwież aplikację.'},code=403)
   length=int(self.headers.get('Content-Length','0'))
   if length<2 or length>12_000_000:raise ValueError('Niepoprawny rozmiar danych (maks. 12 MB)')
   b=json.loads(self.rfile.read(length));action=urlsplit(self.path).path.removeprefix('/api/')
   if action=='stop':
    self.send({'ok':True});threading.Thread(target=self.server.shutdown,daemon=True).start();return
   with LOCK:result=s.mutate(action,b)
   return self.send(result)
  except (ValueError,KeyError,TypeError,sqlite3.Error) as ex:return self.send({'error':str(ex)},code=400)
if __name__=='__main__':
 server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
 (e.OWN.parent/'control.json').write_text(json.dumps({'port':args.port,'token':TOKEN,'pid':os.getpid()}),'utf-8')
 print('DW Social Media '+ORIGIN,flush=True)
 if not args.no_browser:webbrowser.open(ORIGIN)
 server.serve_forever()


