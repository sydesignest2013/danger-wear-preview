import json,re,urllib.request,os
from pathlib import Path
root=Path(__file__).parent
config=json.loads((root/'config.json').read_text('utf-8'))
url='http://127.0.0.1:'+str(config.get('port',8765))
try:
    data=Path(os.environ.get('DW_DATA',config.get('data_dir','data'))).expanduser()
    control=(data if data.is_absolute() else root/data)/'local-control.json'
    control_data=json.loads(control.read_text('utf-8')) if control.is_file() else {}
    admin=control_data.get('admin_path','')
    url='http://127.0.0.1:'+str(control_data.get('port',config.get('port',8765)))
    page=urllib.request.urlopen(url+admin+'/',timeout=3).read().decode()
    token=re.search(r'window.DW_TOKEN="([^"]+)"',page)[1]
    headers={'Content-Type':'application/json','X-DW-Token':token,'Origin':url}
    if control_data:headers['X-DW-Stop']=control_data['stop_token']
    req=urllib.request.Request(url+admin+'/api/shutdown',data=b'{}',headers=headers)
    print(urllib.request.urlopen(req,timeout=5).read().decode())
except Exception as e:print('Program nie jest uruchomiony lub nie odpowiada:',e)
