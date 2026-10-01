"""Start local DW services without changing their databases or credentials."""
from pathlib import Path
import json,os,subprocess,sys,time,urllib.request,webbrowser,traceback
APP=Path(__file__).resolve().parent
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def health(port):
 try:
  with OPENER.open(f'http://127.0.0.1:{port}/api/health',timeout=2) as r:return json.load(r)
 except OSError:return None
def start(app,python,port,expected,args):
 h=health(port)
 if h:
  if not expected(h):raise RuntimeError(f'Port {port} zajmuje inna aplikacja. Niczego nie zatrzymano.')
  return
 with (app/'launcher-server.log').open('a',encoding='utf-8') as log:
  proc=subprocess.Popen([str(python),str(app/'server.py'),*args],cwd=str(app),stdout=log,stderr=log,stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
 for _ in range(80):
  h=health(port)
  if h and expected(h):return
  if proc.poll() is not None:raise RuntimeError(f'Serwer zakonczyl prace. Sprawdz {app / "launcher-server.log"}')
  time.sleep(.25)
 raise RuntimeError(f'Serwer nie odpowiedzial na porcie {port}. Sprawdz launcher-server.log.')
def main():
 cfg=json.loads((APP/'config.json').read_text('utf-8'))
 port=int(cfg.get('port',8765));url=f'http://127.0.0.1:{port}{cfg.get("admin_path","/admin")}/'
 start(APP,Path(sys.executable),port,lambda h:h.get('app')=='DangerWearManager' and Path(h.get('app_dir','')).resolve()==APP.resolve(),[])
 settings=json.loads((APP/'launcher-config.json').read_text('utf-8'))
 # Paths in launcher-config.json are deliberately relative to this folder so a
 # complete project folder can be moved between ROBocze, GOTOWE and a server.
 def app_path(value):
  p=Path(value).expanduser()
  return (p if p.is_absolute() else APP/p).resolve()
 social=app_path(settings['social_dir']);runtime=app_path(settings['social_python'])
 try:
  start(social,runtime,8786,lambda h:bool(h.get('ok')) and Path(h.get('app','')).resolve()==social.resolve(),['--no-browser'])
 except Exception as e:
  print('Panel strony dziala. Social Media wymaga uwagi:',e,flush=True)
  webbrowser.open(url)
  return 1
 print('Panel strony: '+url+'\nSocial Media: http://127.0.0.1:8786/',flush=True)
 if '--no-browser' not in sys.argv:webbrowser.open(url)
 return 0
if __name__=='__main__':
 try:sys.exit(main())
 except Exception:
  traceback.print_exc();sys.exit(1)
