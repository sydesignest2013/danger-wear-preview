import json,sys,subprocess,time,urllib.request,webbrowser,os
from pathlib import Path
APP=Path(__file__).resolve().parent
def request(url,body=None,headers={}):
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 return json.loads(opener.open(urllib.request.Request(url,data=body,headers=headers),timeout=2).read())
if '--stop' in sys.argv:
 p=APP/'data/control.json'
 if p.exists():
  c=json.loads(p.read_text());request(f'http://127.0.0.1:{c["port"]}/api/stop',b'{}',{'X-DW-Token':c['token']})
 print('DW Social Media zatrzymane.');sys.exit()
url='http://127.0.0.1:8786'
try:
 health=request(url+'/api/health')
 if health.get('app')!=str(APP):raise RuntimeError('Port 8786 zajmuje inna kopia aplikacji. Zatrzymaj ją poleceniem STOP.cmd.')
except (OSError,ValueError):
 (APP/'data').mkdir(exist_ok=True)
 log=open(APP/'data/server.log','a',encoding='utf-8')
 subprocess.Popen([sys.executable,str(APP/'server.py'),'--no-browser'],cwd=APP,stdout=log,stderr=log,stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
 for _ in range(40):
  time.sleep(.25)
  try:
   if request(url+'/api/health').get('app')==str(APP):break
  except OSError:pass
 else:raise RuntimeError('Nie udało się uruchomić aplikacji. Szczegóły w data/server.log.')
if '--no-browser' not in sys.argv:webbrowser.open(url)
print('DW Social Media: '+url)
