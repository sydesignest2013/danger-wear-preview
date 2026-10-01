"""DW Social Media: offline, evidence-only monthly calendar engine.
Reads the existing manager.sqlite3 in SQLite READ-ONLY mode. Own data is separate.
"""
import calendar, csv, json, sqlite3, math, base64, hashlib
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path

HERE=Path(__file__).resolve().parent
PANEL=HERE.parent
OWN=PANEL/'data'/'dw-social.sqlite3'

def cfg():return {'manager_db':str(PANEL/'data'/'manager.sqlite3'),'site_root':str(PANEL.parent),'media_root':str(PANEL/'data'/'media')}
def own():
 c=sqlite3.connect(OWN);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
def source():
 p=Path(cfg()['manager_db']).expanduser().resolve()
 if not p.is_file():raise ValueError('Nie znaleziono bazy panelu. Ustaw manager_db w config.json.')
 c=sqlite3.connect(f'file:{p.as_posix()}?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON');return c

def init():
 with own() as c:c.executescript('''
 CREATE TABLE IF NOT EXISTS fixtures(id INTEGER PRIMARY KEY,club_id TEXT NOT NULL,at TEXT NOT NULL,UNIQUE(club_id,at));
 CREATE TABLE IF NOT EXISTS post_stats(id INTEGER PRIMARY KEY,club_id TEXT NOT NULL,category TEXT NOT NULL,format TEXT NOT NULL,at TEXT NOT NULL,reach REAL NOT NULL CHECK(reach>=0),engagement REAL NOT NULL CHECK(engagement>=0),UNIQUE(club_id,category,format,at,reach,engagement));
 CREATE TABLE IF NOT EXISTS fan_stats(id INTEGER PRIMARY KEY,club_id TEXT NOT NULL,offset_hours INTEGER NOT NULL,hour INTEGER NOT NULL CHECK(hour BETWEEN 0 AND 23),activity REAL NOT NULL CHECK(activity>=0),sample INTEGER NOT NULL DEFAULT 1 CHECK(sample>0),UNIQUE(club_id,offset_hours,hour,activity,sample));
 CREATE TABLE IF NOT EXISTS own_photos(src TEXT PRIMARY KEY,product TEXT NOT NULL,category TEXT NOT NULL,format TEXT NOT NULL,club_id TEXT);
 CREATE TABLE IF NOT EXISTS pool(id INTEGER PRIMARY KEY,month TEXT NOT NULL,src TEXT NOT NULL,club_id TEXT NOT NULL,category TEXT NOT NULL,format TEXT NOT NULL,product TEXT NOT NULL, photos TEXT NOT NULL DEFAULT '[]',options TEXT NOT NULL DEFAULT '[]',UNIQUE(month,src));
 CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY,pool_id INTEGER NOT NULL UNIQUE REFERENCES pool(id) ON DELETE CASCADE,at TEXT NOT NULL,locked INTEGER NOT NULL DEFAULT 0,format TEXT,src TEXT,photos TEXT,evidence TEXT);
 CREATE INDEX IF NOT EXISTS idx_posts_at ON posts(at);
 ''')

def library():
 with source() as c:
  clubs=[dict(x) for x in c.execute('SELECT id,name FROM dw_clubs ORDER BY name')]
  rivals={tuple(x) for x in c.execute('SELECT a,b FROM dw_rivalries')}
  photos=[]
  for r in c.execute('SELECT id,draft FROM products'):
   p=json.loads(r['draft']); product=p.get('name','');category=p.get('slug') or p.get('category','')
   for fmt,arr in p.get('galleries',{}).items():
    if not isinstance(arr,list):continue
    for im in arr:
     if isinstance(im,dict) and im.get('src'):
      photos.append(dict(key=f"{r['id']}|{fmt}|{im['src']}",src=im['src'],product=product,category=category,format=fmt,product_id=r['id']))
  bindings={r['src']:r['club_id'] for r in c.execute('SELECT src,club_id FROM dw_photo_clubs')}
  for p in photos:p['club_id']=bindings.get(p['src'])
 with own() as c:photos.extend(dict(dict(x),key='own|'+x['src']) for x in c.execute('SELECT * FROM own_photos'))
 photos=list({p['key']:p for p in photos}.values())
 return dict(clubs=clubs,rivals=[list(x) for x in sorted(rivals)],photos=photos)

def upload_photo(name,content_b64,product,category,fmt,club_id):
 """Import locally into independent module; no writes to source gallery."""
 if fmt not in ('lifestyle','realizacje','produktowe'):raise ValueError('Nieznany rodzaj materiału')
 if not all(isinstance(x,str) and x.strip() for x in (product,category,club_id)):raise ValueError('Uzupełnij produkt, kategorię i klub')
 with source() as c:
  if not c.execute('SELECT 1 FROM dw_clubs WHERE id=?',(club_id,)).fetchone():raise ValueError('Nieznany klub')
 raw=base64.b64decode(content_b64,validate=True)
 if len(raw)>7_000_000:raise ValueError('Zdjęcie przekracza 7 MB')
 if raw.startswith(b'\xff\xd8\xff'):ext='jpg'
 elif raw.startswith(b'\x89PNG\r\n\x1a\n'):ext='png'
 elif raw.startswith(b'RIFF') and raw[8:12]==b'WEBP':ext='webp'
 else:raise ValueError('Obsługiwane formaty: JPG, PNG, WEBP')
 h=hashlib.sha256(raw+f'{club_id}|{product}|{category}|{fmt}'.encode()).hexdigest();path=PANEL/'data'/'dw-social-uploads'/f'{h}.{ext}'
 path.parent.mkdir(exist_ok=True);path.write_bytes(raw)
 src='dw-social-uploads/'+path.name
 with own() as c:c.execute('INSERT OR REPLACE INTO own_photos VALUES(?,?,?,?,?)',(src,product,category,fmt,club_id))
 return {'src':src}

def csv_import(kind,text):
 columns={'fixtures':['club_id','at'],'post_stats':['club_id','category','format','at','reach','engagement'],'fan_stats':['club_id','offset_hours','hour','activity','sample']}
 if kind not in columns:raise ValueError('Nieznana kategoria importu')
 reader=csv.DictReader(text.lstrip('\ufeff').splitlines()); required=set(columns[kind])
 if not reader.fieldnames or not required.issubset(reader.fieldnames):raise ValueError('Brak kolumn: '+', '.join(sorted(required-set(reader.fieldnames or []))))
 with source() as s: valid={r['id'] for r in s.execute('SELECT id FROM dw_clubs')}
 rows=[]
 for line,r in enumerate(reader,2):
  if r['club_id'] not in valid:raise ValueError(f'Wiersz {line}: nieznany identyfikator klubu')
  d={k:r[k].strip() for k in columns[kind]}
  if 'at' in d:
   try:
    dt=datetime.fromisoformat(d['at'])
    if dt.tzinfo is not None:raise ValueError('Podaj lokalny czas polski bez oznaczenia strefy')
   except ValueError:raise ValueError(f'Wiersz {line}: wymagane ISO YYYY-MM-DDTHH:MM')
  if kind=='post_stats':
   for k in ('reach','engagement'):
    d[k]=float(d[k]);assert math.isfinite(d[k]) and d[k]>=0
  if kind=='fan_stats':
   for k in ('offset_hours','hour','sample'):d[k]=int(d[k])
   d['activity']=float(d['activity'])
   if not (0<=d['hour']<=23 and d['sample']>0 and d['activity']>=0 and math.isfinite(d['activity'])):raise ValueError(f'Wiersz {line}: niepoprawne dane')
  rows.append(tuple(d[k] for k in columns[kind]))
 with own() as c:
  before=c.execute('SELECT COUNT(*) FROM '+kind).fetchone()[0]
  c.executemany('INSERT OR IGNORE INTO '+kind+'('+','.join(columns[kind])+') VALUES('+','.join('?'*len(columns[kind]))+')',rows)
  added=c.execute('SELECT COUNT(*) FROM '+kind).fetchone()[0]-before
 return added

def add_pool(month,items):
 datetime.strptime(month,'%Y-%m')
 lib=library();by_key={p['key']:p for p in lib['photos']};valid={p['id'] for p in lib['clubs']}
 with own() as c:
  for item in items:
   key=item.get('key') or item.get('src')
   ref=by_key.get(key)
   # Legacy clients may use plain paths only when they identify one unique photo.
   if ref is None:
    possible=[p for p in lib['photos'] if p['src']==key]
    if len(possible)==1:ref=possible[0]
   if not ref:raise ValueError('Zdjęcie spoza galerii albo niejednoznaczny plik: '+str(key))
   src=ref['src']
   club=item.get('club_id') or ref['club_id'];category=item.get('category') or ref['category'];fmt=item.get('format') or ref['format']
   if club not in valid:raise ValueError('Przypisz prawidłowy klub do: '+src)
   if not category or not fmt:raise ValueError('Brakuje kategorii lub rodzaju zdjęcia')
   keys=item.get('srcs') or [key]
   if not isinstance(keys,list) or not keys or len(keys)>12 or len(set(keys))!=len(keys):raise ValueError('Post może mieć 1–12 różnych zdjęć')
   chosen=[]
   for k in keys:
    other=by_key.get(k)
    if other is None:
     possible=[p for p in lib['photos'] if p['src']==k]
     if len(possible)==1:other=possible[0]
    if not other:raise ValueError('Zdjęcie nie istnieje lub jest niejednoznaczne: '+str(k))
    if ('product_id' in other and 'product_id' in ref and other['product_id']!=ref['product_id']) or other['product']!=ref['product']:raise ValueError('Jeden post musi dotyczyć jednego produktu')
    if other.get('club_id') and other['club_id']!=club:raise ValueError('Połączone zdjęcia mają różne kluby')
    chosen.append(other['src'])
   if len(set(chosen))!=len(chosen):raise ValueError('Nie dodawaj tego samego pliku kilka razy do posta')
   options=item.get('options') or []
   if options:
    if not isinstance(options,list) or len(options)>3:raise ValueError('Dopuszczalne są maksymalnie trzy warianty posta')
    known=set();resolved=[]
    for opt in options:
     if opt.get('format') not in ('lifestyle','realizacje','produktowe') or opt['format'] in known:raise ValueError('Nieprawidłowe warianty formy')
     known.add(opt['format'])
     if not opt.get('srcs') or not set(opt['srcs'])<=set(keys):raise ValueError('Wariant ma zdjęcia spoza wybranej puli')
     resolved.append({'format':opt['format'],'srcs':[chosen[keys.index(k)] for k in opt['srcs']]})
    options=resolved
    fmt='auto' if len(options)>1 else options[0]['format']
   else:options=[{'format':fmt,'srcs':chosen}]
   already=c.execute('SELECT photos FROM pool WHERE month=?',(month,)).fetchall()
   if any(set(json.loads(row['photos']))&set(chosen) for row in already):raise ValueError('Jedno ze zdjęć jest już w miesięcznej puli')
   c.execute('INSERT INTO pool(month,src,club_id,category,format,product,photos,options) VALUES(?,?,?,?,?,?,?,?)',(month,src,club,category,fmt,ref['product'],json.dumps(chosen),json.dumps(options)))

def rows(month):
 with own() as c:return [dict(r) for r in c.execute('SELECT p.*,s.at,s.locked FROM pool p LEFT JOIN posts s ON s.pool_id=p.id WHERE p.month=? ORDER BY s.at,p.id',(month,))]

def conflicts(a,b,rivals):
 if a['club_id']==b['club_id']:return 'Nie wolno umieszczać kolejno tego samego klubu.'
 if tuple(sorted((a['club_id'],b['club_id']))) in rivals:return 'Zakaz sąsiadowania klubów będących kosami.'
 if a['category']==b['category']:return 'Nie wolno umieszczać kolejno tej samej kategorii.'
 return ''

def validate_timeline(posts,rivals):
 ordered=sorted(posts,key=lambda p:(p['at'],p.get('id',0)))
 if len({p['at'] for p in ordered})!=len(ordered):raise ValueError('Dwa posty mają identyczny termin.')
 for a,b in zip(ordered,ordered[1:]):
  error=conflicts(a,b,rivals)
  if error:raise ValueError(f'{error} Konflikt: {a["at"]} → {b["at"]}')
 return True

def data_score(item,when,fixtures,stats,fans):
 """No guessed times: BOTH post-history and fan-activity evidence are mandatory.
 Post history matches club, product category, format and weekday/hour.
 Fan activity matches club, offset from match rounded to day, and hour.
 """
 history=[s for s in stats if (s['club_id'],s['category'],s['format'])==(item['club_id'],item['category'],item['format']) and datetime.fromisoformat(s['at']).weekday()==when.weekday() and datetime.fromisoformat(s['at']).hour==when.hour]
 if not history:return None
 matches=[f for f in fixtures if f['club_id']==item['club_id']]
 if not matches:return None
 offsets=[(abs((datetime.fromisoformat(f['at'])-when).total_seconds()),round((datetime.fromisoformat(f['at'])-when).total_seconds()/3600)) for f in matches]
 _,offset=min(offsets)
 fan=[f for f in fans if f['club_id']==item['club_id'] and f['hour']==when.hour and abs(f['offset_hours']-offset)<=12]
 if not fan:return None
 # Use observed engagement-per-reach and sampled fan activity. No arbitrary default engagement.
 reach=sum(s['reach'] for s in history)
 if not reach:return None
 effect=sum(s['engagement'] for s in history)/reach
 exposure=sum(f['activity']*f['sample'] for f in fan)/sum(f['sample'] for f in fan)
 return effect*exposure, len(history),sum(f['sample'] for f in fan)

def generate(month,recalculate=False):
 """Whole-pool beam optimizer. On no feasible fully evidenced solution, DO NOT save a partial calendar."""
 year,m=map(int,month.split('-'));last=calendar.monthrange(year,m)[1]
 pool=rows(month);pending=[p for p in pool if not p['at'] or (recalculate and not p['locked'])];fixed=[p for p in pool if p['at'] and (not recalculate or p['locked'])]
 if not pending:return {'scheduled':0,'message':'Brak nowych materiałów do planowania.'}
 lib=library();rivals={tuple(r) for r in lib['rivals']}
 with own() as c:
  fixtures=[dict(x) for x in c.execute('SELECT * FROM fixtures')]
  stats=[dict(x) for x in c.execute('SELECT * FROM post_stats')]
  fans=[dict(x) for x in c.execute('SELECT * FROM fan_stats')]
  # Include previous/next month's scheduled publications for boundary checks.
  external=[dict(x) for x in c.execute('SELECT p.*,s.at FROM posts s JOIN pool p ON p.id=s.pool_id WHERE p.month!=?',(month,))]
 candidates={}
 for p in pending:
  options=[]
  for day in range(1,last+1):
   for hour in range(7,24):
    d=datetime(year,m,day,hour)
    for variant in json.loads(p['options'] or '[]'):
     v={**p,'format':variant['format']}
     sc=data_score(v,d,fixtures,stats,fans)
     if sc is not None:options.append((sc[0],d.isoformat(timespec='minutes'),variant,{'history_posts':sc[1],'fan_sample':sc[2],'score':round(sc[0],5)}))
  options.sort(key=lambda x:(-x[0],x[1]));candidates[p['id']]=options[:100]
 missing=[p for p in pending if not candidates[p['id']]]
 if missing:return {'error':'Brak wystarczających danych statystycznych do wyznaczenia terminów. Nie wygenerowano kalendarza.', 'unplanned':[dict(id=p['id'],club=p['club_id'],product=p['product'],format=p['format']) for p in missing]}
 # Limited beam search, orders rare materials first; validate whole timeline after every addition.
 order=sorted(pending,key=lambda p:(len(candidates[p['id']]),p['id']))
 beams=[(0.0,[])]
 for p in order:
  new=[]
  for score,selected in beams:
   occupied={x['at'] for x in fixed+external+selected}
   for val,at,variant,basis in candidates[p['id']]:
    if at in occupied:continue
    proposed={**p,'at':at,'format':variant['format'],'src':variant['srcs'][0],'photos':json.dumps(variant['srcs']),'evidence':json.dumps(basis)}
    trial=fixed+external+selected+[proposed]
    try:validate_timeline(trial,rivals)
    except ValueError:continue
    new.append((score+val,selected+[proposed]))
  new.sort(key=lambda x:-x[0]);beams=new[:150]
  if not beams:return {'error':'Nie znaleziono pełnego harmonogramu zgodnego z danymi i zakazami. Niczego nie zapisano.','unplanned':[p['id'] for p in pending]}
 winner=beams[0][1]
 with own() as c:
  for p in winner:c.execute('INSERT INTO posts(pool_id,at,locked,format,src,photos,evidence) VALUES(?,?,0,?,?,?,?) ON CONFLICT(pool_id) DO UPDATE SET at=excluded.at,locked=0,format=excluded.format,src=excluded.src,photos=excluded.photos,evidence=excluded.evidence',(p['id'],p['at'],p['format'],p['src'],p['photos'],p['evidence']))
 return {'scheduled':len(winner),'message':'Wygenerowano harmonogram wyłącznie z danych źródłowych.'}

def move(post_id,at):
 new=datetime.fromisoformat(at).isoformat(timespec='minutes')
 lib=library();rivals={tuple(r) for r in lib['rivals']}
 with own() as c:
  row=c.execute('SELECT p.*,s.at FROM posts s JOIN pool p ON p.id=s.pool_id WHERE s.id=?',(post_id,)).fetchone()
  if not row:raise ValueError('Nie znaleziono publikacji')
  if new[:7]!=row['month']:raise ValueError('Przenoszenie między miesiącami wymaga osobnej operacji')
  allposts=[dict(x) for x in c.execute('SELECT p.*,s.at,s.id as post_id FROM posts s JOIN pool p ON p.id=s.pool_id')]
  for x in allposts:
   if x['post_id']==post_id:x['at']=new
  validate_timeline(allposts,rivals)
  c.execute('UPDATE posts SET at=?,locked=1 WHERE id=?',(new,post_id))
 return {'ok':True}

def scheduled(month):
 with own() as c:return [dict(x) for x in c.execute('SELECT s.id AS post_id,s.at,s.locked,s.format AS selected_format,s.src AS selected_src,s.photos AS selected_photos,s.evidence,p.* FROM posts s JOIN pool p ON p.id=s.pool_id WHERE p.month=? ORDER BY s.at',(month,))]


def remove_pool(item_id):
 with own() as c:
  row=c.execute('SELECT id FROM posts WHERE pool_id=?',(item_id,)).fetchone()
  if row:raise ValueError('Najpierw usuń termin z kalendarza.')
  c.execute('DELETE FROM pool WHERE id=?',(item_id,))
 return {'ok':True}

def remove_post(post_id):
 with own() as c:c.execute('DELETE FROM posts WHERE id=?',(post_id,))
 return {'ok':True}

def evidence():
 with own() as c:return {name:c.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in ('fixtures','post_stats','fan_stats')}
