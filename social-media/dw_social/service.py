"""Independent local application. All mutations are confined to engine.OWN."""
import csv,io,json,math,calendar,base64,re,zipfile,sqlite3
from datetime import datetime
from pathlib import Path
from . import engine as e

def init():
 e.init()
 with e.own() as c:
  c.executescript('''
  CREATE TABLE IF NOT EXISTS captions(id INTEGER PRIMARY KEY,product TEXT NOT NULL,body TEXT NOT NULL,updated TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS sources(id INTEGER PRIMARY KEY,name TEXT NOT NULL,kind TEXT NOT NULL,platform TEXT NOT NULL,notes TEXT NOT NULL DEFAULT '');
  CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,at TEXT NOT NULL,action TEXT NOT NULL,detail TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS imports(id INTEGER PRIMARY KEY,at TEXT NOT NULL,source_id INTEGER,name TEXT NOT NULL,kind TEXT NOT NULL,added INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS goals(id INTEGER PRIMARY KEY,month TEXT NOT NULL,product TEXT NOT NULL,club_id TEXT NOT NULL,target INTEGER NOT NULL CHECK(target>0),notes TEXT NOT NULL);
  ''')
  for table,columns in {'pool':{'caption':"TEXT NOT NULL DEFAULT ''",'platform':"TEXT NOT NULL DEFAULT 'Facebook'",'status':"TEXT NOT NULL DEFAULT 'draft'",'published_at':"TEXT",'publication_url':"TEXT NOT NULL DEFAULT ''"},'post_stats':{'platform':"TEXT NOT NULL DEFAULT 'Nieokreślone'",'source_id':'INTEGER'},'fixtures':{'source_id':'INTEGER'},'fan_stats':{'source_id':'INTEGER'}}.items():
   existing={r['name'] for r in c.execute('PRAGMA table_info('+table+')')}
   for name,typ in columns.items():
    if name not in existing:c.execute(f'ALTER TABLE {table} ADD COLUMN {name} {typ}')
  # The former schema allowed a source photo only once per month.  An empty
  # working pool can safely be upgraded so the same approved material may be
  # prepared independently for Facebook and Instagram.
  pool_sql=c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='pool'").fetchone()[0]
  if 'UNIQUE(month,src)' in pool_sql.replace(' ', '') and c.execute('SELECT COUNT(*) FROM pool').fetchone()[0]==0:
   c.executescript('''
   DROP TABLE IF EXISTS posts;
   DROP TABLE pool;
   CREATE TABLE pool(id INTEGER PRIMARY KEY,month TEXT NOT NULL,src TEXT NOT NULL,club_id TEXT NOT NULL,category TEXT NOT NULL,format TEXT NOT NULL,product TEXT NOT NULL,photos TEXT NOT NULL DEFAULT '[]',options TEXT NOT NULL DEFAULT '[]',caption TEXT NOT NULL DEFAULT '',platform TEXT NOT NULL DEFAULT 'Facebook',status TEXT NOT NULL DEFAULT 'draft',published_at TEXT,publication_url TEXT NOT NULL DEFAULT '',UNIQUE(month,src,platform));
   CREATE TABLE posts(id INTEGER PRIMARY KEY,pool_id INTEGER NOT NULL UNIQUE REFERENCES pool(id) ON DELETE CASCADE,at TEXT NOT NULL,locked INTEGER NOT NULL DEFAULT 0,format TEXT,src TEXT,photos TEXT,evidence TEXT);
   ''')
  if 'engagement,platform)' not in c.execute("SELECT sql FROM sqlite_master WHERE name='post_stats'").fetchone()[0]:
   c.executescript('''
   ALTER TABLE post_stats RENAME TO post_stats_old;
   CREATE TABLE post_stats(id INTEGER PRIMARY KEY,club_id TEXT NOT NULL,category TEXT NOT NULL,format TEXT NOT NULL,at TEXT NOT NULL,reach REAL NOT NULL CHECK(reach>=0),engagement REAL NOT NULL CHECK(engagement>=0),platform TEXT NOT NULL DEFAULT 'Nieokreślone',source_id INTEGER,UNIQUE(club_id,category,format,at,reach,engagement,platform));
   INSERT INTO post_stats(id,club_id,category,format,at,reach,engagement,platform,source_id) SELECT id,club_id,category,format,at,reach,engagement,platform,source_id FROM post_stats_old;
   DROP TABLE post_stats_old;
   ''')

def audit(c,action,detail):c.execute('INSERT INTO audit(at,action,detail) VALUES(?,?,?)',(datetime.now().isoformat(timespec='seconds'),action,str(detail)))
def text(v,name,limit=10000):
 if not isinstance(v,str) or not v.strip() or len(v)>limit:raise ValueError('Uzupełnij poprawnie: '+name)
 return v.strip()
def month(v):
 if not isinstance(v,str) or not re.fullmatch(r'\d{4}-\d{2}',v):raise ValueError('Wymagany miesiąc RRRR-MM')
 datetime.strptime(v,'%Y-%m');return v
def at(v):
 if not isinstance(v,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}',v):raise ValueError('Wymagany lokalny termin RRRR-MM-DDTHH:MM')
 datetime.fromisoformat(v);return v
def rivals():return {tuple(sorted(r)) for r in e.library()['rivals']}
def timeline(c):return [dict(x) for x in c.execute('SELECT p.*,s.at,s.id as post_id FROM posts s JOIN pool p ON p.id=s.pool_id')]
def state(m):
 month(m)
 lib=e.library()
 with e.own() as c:
  result={key:[dict(x) for x in c.execute(sql)] for key,sql in {
   'captions':'SELECT * FROM captions ORDER BY product,id',
   'sources':'SELECT * FROM sources ORDER BY id',
   'audit':'SELECT * FROM audit ORDER BY id DESC LIMIT 300',
   'imports':'SELECT * FROM imports ORDER BY id DESC',
   'goals':'SELECT * FROM goals ORDER BY month,id',
   'history':"SELECT p.*,s.at FROM pool p LEFT JOIN posts s ON s.pool_id=p.id WHERE p.status='published' ORDER BY p.published_at DESC",
   'analytics':'SELECT * FROM post_stats ORDER BY at DESC',
   'fixtures':'SELECT * FROM fixtures ORDER BY at',
   'fans':'SELECT * FROM fan_stats ORDER BY club_id,hour'}.items()}
 result.update(library=lib,pool=e.rows(m),calendar=e.scheduled(m),counts=e.evidence())
 return result

def import_csv(b):
 kind=b['kind'];raw=text(b['csv'],'CSV',4_000_000)
 if kind=='captions':
  reader=csv.DictReader(io.StringIO(raw.lstrip('\ufeff')),delimiter=';' if ';' in raw.splitlines()[0] else ',')
  if not {'product','body'}<=set(reader.fieldnames or []):raise ValueError('Wymagane kolumny product,body')
  rows=[(text(r['product'],'produkt',200),text(r['body'],'opis',10000)) for r in reader]
  if len(rows)>20000:raise ValueError('Maksymalnie 20 000 wierszy')
  with e.own() as c:
   added=0
   for product,body in rows:
    if not c.execute('SELECT 1 FROM captions WHERE product=? AND body=?',(product,body)).fetchone():
     c.execute('INSERT INTO captions(product,body,updated) VALUES(?,?,?)',(product,body,datetime.now().isoformat()));added+=1
   audit(c,'Import opisów',f'{added} opisów');return {'imported':added}
 if kind not in ('post_stats','fan_stats','fixtures'):raise ValueError('Nieznany rodzaj danych')
 with e.own() as c:
  source=c.execute('SELECT * FROM sources WHERE id=?',(b.get('source_id'),)).fetchone()
  if not source or source['kind']!=kind:raise ValueError('Wybierz źródło zgodne z rodzajem danych')
  last=c.execute('SELECT coalesce(max(id),0) FROM '+kind).fetchone()[0]
 added=e.csv_import(kind,raw,source['id'],source['platform'])
 with e.own() as c:
  c.execute('UPDATE '+kind+' SET source_id=? WHERE id>?',(source['id'],last))
  if kind=='post_stats':c.execute('UPDATE post_stats SET platform=? WHERE id>?',(source['platform'],last))
  c.execute('INSERT INTO imports(at,source_id,name,kind,added) VALUES(?,?,?,?,?)',(datetime.now().isoformat(timespec='seconds'),source['id'],b.get('name','CSV')[:200],kind,added))
  audit(c,'Import danych',f"{source['name']}: {added} nowych wierszy")
 return {'imported':added}

def schedule(b):
 target=at(b['at']);rr=rivals()
 with e.own() as c:
  row=c.execute('SELECT * FROM pool WHERE id=?',(b['id'],)).fetchone()
  if not row:raise ValueError('Nie znaleziono posta')
  if row['status']=='published':raise ValueError('Opublikowany post jest zapisany w historii')
  if target[:7]!=row['month']:raise ValueError('Termin musi należeć do miesiąca puli')
  proposed=[x for x in timeline(c) if x['id']!=row['id']]+[{**dict(row),'at':target}]
  e.validate_timeline(proposed,rr)
  c.execute('INSERT INTO posts(pool_id,at,locked) VALUES(?,?,1) ON CONFLICT(pool_id) DO UPDATE SET at=excluded.at,locked=1',(row['id'],target))
  c.execute("UPDATE pool SET status='scheduled' WHERE id=?",(row['id'],))
  audit(c,'Ustalono termin',f"{row['product']} / {target}")
 return {'ok':True}

def generate(b):
 m=month(b['month']);rr=rivals();allpool=e.rows(m)
 pending=[p for p in allpool if p['status']!='published' and (not p['at'] or (b.get('recalculate') and not p['locked']))]
 if not pending:return {'scheduled':0,'message':'Brak niezaplanowanych materiałów.'}
 if len(pending)>18:raise ValueError('Jednorazowe planowanie obejmuje maksymalnie 18 postów. Ustal część terminów ręcznie i ponów planowanie.')
 with e.own() as c:
  fixed=[x for x in timeline(c) if x['id'] not in {p['id'] for p in pending}]
  fixtures=[dict(x) for x in c.execute('SELECT * FROM fixtures')];stats=[dict(x) for x in c.execute('SELECT * FROM post_stats')];fans=[dict(x) for x in c.execute('SELECT * FROM fan_stats')]
 year,mo=map(int,m.split('-'));candidates={}
 for p in pending:
  options=[]
  for day in range(1,calendar.monthrange(year,mo)[1]+1):
   for hour in range(24):
    d=datetime(year,mo,day,hour)
    for variant in json.loads(p['options']):
     score=e.data_score({**p,'format':variant['format']},d,fixtures,[s for s in stats if s['platform']==p['platform']],fans)
     if score is not None:
      options.append({**p,'at':d.isoformat(timespec='minutes'),'selected_format':variant['format'],'selected_src':variant['srcs'][0],'selected_photos':json.dumps(variant['srcs']),'basis':json.dumps({'history_posts':score[1],'fan_sample':score[2],'score':score[0]}),'score':score[0]})
  candidates[p['id']]=sorted(options,key=lambda v:(-v['score'],v['at']))[:100]
 missing=[p['product'] for p in pending if not candidates[p['id']]]
 if missing:raise ValueError('Brak podstaw do rekomendacji dla: '+', '.join(missing)+'. Potrzebne są zgodne statystyki platformy, klubu, kategorii, formatu i aktywności względem meczu. Niczego nie zapisano.')
 order=sorted(pending,key=lambda p:len(candidates[p['id']]))
 visits=0;solution=None
 def search(index,selected,occupied):
  nonlocal visits,solution
  if visits>=150000:return False
  visits+=1
  if index==len(order):
   try:e.validate_timeline(fixed+selected,rr)
   except ValueError:return False
   solution=selected;return True
  for p in candidates[order[index]['id']]:
   if p['at'] in occupied:continue
   if search(index+1,selected+[p],occupied|{p['at']}):return True
  return False
 search(0,[],{p['at'] for p in fixed})
 if solution is None:raise ValueError('Nie znaleziono zgodnego planu w limicie przeszukiwania. To nie dowodzi braku rozwiązania. Zmniejsz pulę lub ustal część terminów ręcznie. Niczego nie zapisano.')
 with e.own() as c:
  for p in solution:
   c.execute('INSERT INTO posts(pool_id,at,locked,format,src,photos,evidence) VALUES(?,?,0,?,?,?,?) ON CONFLICT(pool_id) DO UPDATE SET at=excluded.at,locked=0,format=excluded.format,src=excluded.src,photos=excluded.photos,evidence=excluded.evidence',(p['id'],p['at'],p['selected_format'],p['selected_src'],p['selected_photos'],p['basis']))
   c.execute("UPDATE pool SET status='scheduled' WHERE id=?",(p['id'],))
  audit(c,'Wygenerowano plan',f'{m}: {len(solution)} postów; wyłącznie terminy oparte na danych')
 return {'scheduled':len(solution)}

def mutate(action,b):
 if action=='import':return import_csv(b)
 if action=='schedule':return schedule(b)
 if action=='generate':return generate(b)
 if action=='upload':
  result=e.upload_photo(b.get('name',''),b['data'],b['product'],b['category'],b['format'],b['club_id'])
  with e.own() as c:audit(c,'Dodano zdjęcie',b['product'])
  return result
 if action=='pool':
  month(b['month']);platforms=b.get('platforms') or [b.get('platform','Facebook')]
  if not isinstance(platforms,list) or not platforms or set(platforms)-{'Facebook','Instagram'}:raise ValueError('Wybierz Facebook, Instagram lub oba kanały')
  platforms=list(dict.fromkeys(platforms))
  with e.own() as c:last=c.execute('SELECT coalesce(max(id),0) FROM pool').fetchone()[0]
  for platform in platforms:e.add_pool(b['month'],b['items'],platform)
  with e.own() as c:
   c.execute('UPDATE pool SET caption=? WHERE id>?',(b.get('caption','')[:10000],last));audit(c,'Dodano do puli',b['month']+' · '+', '.join(platforms))
  return {'ok':True}
 if action=='post':
  with e.own() as c:
   row=c.execute('SELECT * FROM pool WHERE id=?',(b['id'],)).fetchone()
   if not row or row['status']=='published':raise ValueError('Post niedostępny do edycji')
   platform=b.get('platform',row['platform'])
   if platform not in ('Facebook','Instagram'):raise ValueError('Dostępne są wyłącznie Facebook i Instagram')
   c.execute('UPDATE pool SET caption=?,platform=? WHERE id=?',(b.get('caption','')[:10000],platform,b['id']));audit(c,'Zmieniono treść posta',b['id'])
  return {'ok':True}
 if action in ('unschedule','delete-post'):
  rr=rivals()
  with e.own() as c:
   row=c.execute('SELECT * FROM pool WHERE id=?',(b['id'],)).fetchone()
   if not row or row['status']=='published':raise ValueError('Nie można usuwać opublikowanej historii')
   e.validate_timeline([p for p in timeline(c) if p['id']!=b['id']],rr)
   c.execute('DELETE FROM posts WHERE pool_id=?',(b['id'],))
   if action=='delete-post':c.execute('DELETE FROM pool WHERE id=?',(b['id'],))
   else:c.execute("UPDATE pool SET status='draft' WHERE id=?",(b['id'],))
   audit(c,'Usunięto post' if action=='delete-post' else 'Usunięto termin',b['id'])
  return {'ok':True}
 if action=='publish':
  actual=at(b['published_at']);url=b.get('url','').strip()
  if datetime.fromisoformat(actual)>datetime.now():raise ValueError('Data faktycznej publikacji nie może być w przyszłości')
  if url and not url.startswith(('https://','http://')):raise ValueError('Nieprawidłowy adres publikacji')
  rr=rivals()
  with e.own() as c:
   row=c.execute('SELECT * FROM pool WHERE id=?',(b['id'],)).fetchone()
   if not row or row['status']=='published':raise ValueError('Nie znaleziono nieopublikowanego posta')
   e.validate_timeline([p for p in timeline(c) if p['id']!=b['id']]+[{**dict(row),'at':actual}],rr)
   c.execute('INSERT INTO posts(pool_id,at,locked) VALUES(?,?,1) ON CONFLICT(pool_id) DO UPDATE SET at=excluded.at,locked=1',(b['id'],actual))
   c.execute("UPDATE pool SET status='published',published_at=?,publication_url=? WHERE id=?",(actual,url,b['id']))
   audit(c,'Potwierdzono faktyczną publikację',b['id'])
  return {'ok':True}
 if action=='caption':
  with e.own() as c:
   if b.get('delete'):c.execute('DELETE FROM captions WHERE id=?',(b['id'],))
   else:
    product=text(b['product'],'produkt',200);body=text(b['body'],'opis')
    if b.get('id'):c.execute('UPDATE captions SET product=?,body=?,updated=? WHERE id=?',(product,body,datetime.now().isoformat(),b['id']))
    else:c.execute('INSERT INTO captions(product,body,updated) VALUES(?,?,?)',(product,body,datetime.now().isoformat()))
   audit(c,'Zmieniono bazę opisów',b.get('product',b.get('id')))
  return {'ok':True}
 if action=='source':
  with e.own() as c:
   if b.get('delete'):
    if any(c.execute('SELECT 1 FROM '+t+' WHERE source_id=?',(b['id'],)).fetchone() for t in ('post_stats','fixtures','fan_stats')):raise ValueError('Źródło ma zaimportowane dane. Usuń je w tabeli przed usunięciem źródła.')
    c.execute('DELETE FROM sources WHERE id=?',(b['id'],))
   else:
    name=text(b['name'],'nazwa',200);kind=b['kind'];platform=b['platform']
    if kind not in ('fixtures','post_stats','fan_stats') or platform not in ('Facebook','Instagram','TikTok','YouTube','Nieokreślone'):raise ValueError('Nieprawidłowe źródło')
    if b.get('id'):
     old=c.execute('SELECT * FROM sources WHERE id=?',(b['id'],)).fetchone()
     if not old or (old['kind'],old['platform'])!=(kind,platform):raise ValueError('Rodzaj i platforma istniejącego źródła są stałe. Utwórz nowe źródło.')
     c.execute('UPDATE sources SET name=?,notes=? WHERE id=?',(name,b.get('notes','')[:10000],b['id']))
    else:c.execute('INSERT INTO sources(name,kind,platform,notes) VALUES(?,?,?,?)',(name,kind,platform,b.get('notes','')[:10000]))
   audit(c,'Zmieniono źródło',b.get('name',b.get('id')))
  return {'ok':True}
 if action=='delete-data':
  kind=b['kind']
  if kind not in ('fixtures','post_stats','fan_stats'):raise ValueError('Nieznana tabela')
  with e.own() as c:c.execute('DELETE FROM '+kind+' WHERE id=?',(b['id'],));audit(c,'Usunięto rekord źródłowy',f"{kind} / {b['id']}")
  return {'ok':True}
 if action=='goal':
  with e.own() as c:
   if b.get('delete'):c.execute('DELETE FROM goals WHERE id=?',(b['id'],))
   else:
    m=month(b['month']);product=text(b['product'],'produkt',200);target=int(b['target'])
    if not 1<=target<=10000:raise ValueError('Cel musi wynosić 1–10 000')
    if b['club_id'] not in {x['id'] for x in e.library()['clubs']}:raise ValueError('Nieznany klub')
    c.execute('INSERT INTO goals(month,product,club_id,target,notes) VALUES(?,?,?,?,?)',(m,product,b['club_id'],target,b.get('notes','')[:10000]))
   audit(c,'Zmieniono plan handlowy',b.get('product',b.get('id')))
  return {'ok':True}
 if action=='delete-photo':
  with e.own() as c:
   if any(b['src'] in json.loads(x[0]) for x in c.execute('SELECT photos FROM pool')):raise ValueError('Zdjęcie jest używane w puli lub historii')
   c.execute('DELETE FROM own_photos WHERE src=?',(b['src'],));audit(c,'Usunięto zdjęcie z biblioteki',b['src'])
  return {'ok':True}
 raise ValueError('Nieznana operacja')

def export(kind,m):
 with e.own() as c:
  if kind=='calendar':rows=[dict(x) for x in c.execute('SELECT p.product,p.club_id,p.category,p.platform,p.caption,p.status,s.at FROM pool p LEFT JOIN posts s ON s.pool_id=p.id WHERE p.month=? ORDER BY s.at',(month(m),))];columns=['product','club_id','category','platform','caption','status','at']
  elif kind=='captions':rows=[dict(x) for x in c.execute('SELECT product,body FROM captions')];columns=['product','body']
  elif kind=='analytics':rows=[dict(x) for x in c.execute('SELECT club_id,category,format,at,reach,engagement,platform FROM post_stats')];columns=['club_id','category','format','at','reach','engagement','platform']
  else:raise ValueError('Nieznany eksport')
 out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=columns);w.writeheader()
 for row in rows:
  w.writerow({k:("'"+str(v) if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v) for k,v in row.items()})
 return ('\ufeff'+out.getvalue()).encode('utf-8')

