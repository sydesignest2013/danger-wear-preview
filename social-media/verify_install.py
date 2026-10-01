from pathlib import Path
import os,json,sqlite3
APP=Path(__file__).resolve().parent
config=json.loads((APP/'config.json').read_text('utf-8-sig'))
panel=Path(config['panel_path']).expanduser()
os.environ['DW_PANEL']=str((panel if panel.is_absolute() else APP/panel).resolve());os.environ['DW_SOCIAL_DATA']=str(APP/'data')
from dw_social import service as s,engine as e
with e.source() as c:
 clubs=c.execute('SELECT count(*) FROM dw_clubs').fetchone()[0]
 pairs=c.execute('SELECT count(*) FROM dw_rivalries').fetchone()[0]
s.init()
with e.own() as c:
 for name in ('captions','post_stats','fan_stats','fixtures','posts','pool','sources','audit','goals','imports'):
  if c.execute('SELECT count(*) FROM '+name).fetchone()[0]:raise ValueError('Instalacja wymaga pustej bazy: '+name)
print(f'OK: read-only reference: {clubs} clubs, {pairs} rivalries. New knowledge base is empty.')
