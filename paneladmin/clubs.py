"""Shared clubs, symmetric rivalries and photo ownership for the existing editor."""
import json, re, sqlite3, unicodedata, math, hashlib, shutil
from pathlib import Path

METHODS={'sublimacja':'Sublimacja','haft-komputerowy':'Haft_komputerowy','sitodruk':'Sitodruk','dtf':'DTF','dtg':'DTG'}
def name_key(name):
    return re.sub(r'[^a-z0-9]+','',unicodedata.normalize('NFKD',name.casefold().replace('ł','l')).encode('ascii','ignore').decode())

def initialize(a):
    with a.connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS dw_clubs(seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT UNIQUE NOT NULL,name TEXT NOT NULL,name_key TEXT NOT NULL UNIQUE,promoted INTEGER NOT NULL DEFAULT 0 CHECK(promoted IN(0,1)),bonus REAL NOT NULL DEFAULT .05 CHECK(bonus>=0 AND bonus<=.2));
        CREATE TABLE IF NOT EXISTS dw_rivalries(a TEXT NOT NULL REFERENCES dw_clubs(id),b TEXT NOT NULL REFERENCES dw_clubs(id),PRIMARY KEY(a,b),CHECK(a<b));
        CREATE TABLE IF NOT EXISTS dw_photo_clubs(src TEXT PRIMARY KEY,club_id TEXT REFERENCES dw_clubs(id));
        CREATE TABLE IF NOT EXISTS dw_method_photos(id INTEGER PRIMARY KEY AUTOINCREMENT,method TEXT NOT NULL,src TEXT NOT NULL,alt TEXT NOT NULL DEFAULT '',UNIQUE(method,src));
        CREATE TABLE IF NOT EXISTS dw_club_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS dw_club_events(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT NOT NULL,event TEXT NOT NULL,detail TEXT NOT NULL);
        INSERT OR IGNORE INTO dw_club_meta VALUES('revision','1');
        ''')
        if not c.execute("SELECT 1 FROM dw_club_meta WHERE key='seed'").fetchone():
            seed=json.loads((a.APP/'clubs-seed.json').read_text('utf-8'))
            for row in seed['clubs']:
                c.execute('INSERT INTO dw_clubs VALUES(?,?,?,?,?,?)',(int(row['id'][4:]),row['id'],row['name'],name_key(row['name']),row['promoted'],row['promotion_bonus']))
            for row in seed['rivalries']:
                x,y=sorted((row['club_a'],row['club_b']));c.execute('INSERT OR IGNORE INTO dw_rivalries VALUES(?,?)',(x,y))
            c.execute("INSERT INTO dw_club_meta VALUES('seed',?)",(a.now(),))
            record(a,c,'import',{'clubs':len(seed['clubs']),'pairs':len(seed['rivalries']),'notes':seed['notes']})
        if not c.execute("SELECT 1 FROM dw_club_meta WHERE key='methods'").fetchone():
            for row in json.loads((a.APP/'clubs-methods-seed.json').read_text('utf-8')):
                c.execute('INSERT OR IGNORE INTO dw_method_photos(method,src,alt) VALUES(?,?,?)',(row['method'],row['src'],row['alt']))
            c.execute("INSERT INTO dw_club_meta VALUES('methods','1')")
    export(a)

def record(a,c,event,detail):
    c.execute('INSERT INTO dw_club_events(at,event,detail) VALUES(?,?,?)',(a.now(),event,a.dumps(detail)))

def revision(c):return int(c.execute("SELECT value FROM dw_club_meta WHERE key='revision'").fetchone()[0])
def bindings(c):return {r['src']:r['club_id'] for r in c.execute('SELECT * FROM dw_photo_clubs')}
def decorate(c,p):
    owners=bindings(c)
    for items in p.get('galleries',{}).values():
        for item in items:
            if item['src'] in owners:item['club_id']=owners[item['src']]
    return p

def payload(c):
    return {'version':1,'revision':revision(c),'clubs':{r['id']:{'weight':1+r['bonus'] if r['promoted'] else 1} for r in c.execute('SELECT * FROM dw_clubs')},'rivalries':[list(r) for r in c.execute('SELECT a,b FROM dw_rivalries')],'photos':bindings(c),'methods':{key:[dict(r) for r in c.execute('SELECT src,alt FROM dw_method_photos WHERE method=? ORDER BY id',(key,))] for key in METHODS}}

def export(a):
    with a.connect() as c:data=payload(c)
    a.atomic(a.SOURCE/'js/dw-clubs-data.json',a.dumps(data))

def inventory(a,c):
    found={}
    for row in c.execute('SELECT id FROM products'):
        p=a.get_product(c,row[0])
        for category,items in p.get('galleries',{}).items():
            for item in items:
                key=(category,item['src'])
                found.setdefault(key,dict(src=item['src'],category=category,product_id=p['id'],product=p['name'],alt=item.get('alt','')))
    for row in c.execute('SELECT * FROM dw_method_photos'):
        found[('methods',row['method'],row['src'])]=dict(src=row['src'],category='methods',method=row['method'],photo_id=row['id'],alt=row['alt'])
    owners=bindings(c)
    for item in found.values():item['club_id']=owners.get(item['src'])
    return list(found.values())

def state(a):
    with a.LOCK,a.connect() as c:
        photos=inventory(a,c);clubs=[dict(r) for r in c.execute('SELECT * FROM dw_clubs')]
        for club in clubs:
            club['counts']={k:len({p['src'] for p in photos if p['club_id']==club['id'] and p['category']==k}) for k in ('lifestyle','realizacje','methods')}
        return {'revision':revision(c),'clubs':clubs,'rivalries':[list(r) for r in c.execute('SELECT a,b FROM dw_rivalries')],'photos':photos,'methods':METHODS,'history':[dict(r) for r in c.execute('SELECT * FROM dw_club_events ORDER BY id DESC LIMIT 100')]}

def require_club(c,id):
    if id is not None and not c.execute('SELECT 1 FROM dw_clubs WHERE id=?',(id,)).fetchone():raise ValueError('Nie znaleziono klubu.')

def mutate(a,b):
    with a.PUBLISH_LOCK,a.LOCK,a.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        if b.get('revision')!=revision(c):raise a.Conflict('Baza klubów zmieniła się. Odśwież dane przed zapisem.')
        action=b.get('action');detail={k:v for k,v in b.items() if k!='revision'}
        if action in ('create','edit'):
            name=str(b.get('name','')).strip();key=name_key(name)
            if not 2<=len(name)<=120 or not key:raise ValueError('Nazwa klubu: 2–120 znaków.')
            try:
                if action=='create':
                    n=c.execute("SELECT seq FROM sqlite_sequence WHERE name='dw_clubs'").fetchone();seq=(n[0] if n else 0)+1
                    id=f'DW-K{seq:04d}';c.execute('INSERT INTO dw_clubs(seq,id,name,name_key) VALUES(?,?,?,?)',(seq,id,name,key));detail['id']=id
                else:
                    require_club(c,b.get('id') or '');bonus=float(b.get('bonus',.05))
                    if not math.isfinite(bonus) or not 0<=bonus<=.2:raise ValueError('Bonus musi mieścić się w zakresie 0–20%.')
                    c.execute('UPDATE dw_clubs SET name=?,name_key=?,promoted=?,bonus=? WHERE id=?',(name,key,int(bool(b.get('promoted'))),bonus,b['id']))
            except sqlite3.IntegrityError as e:raise ValueError('Klub o takiej nazwie już istnieje (sprawdź także pisownię bez polskich znaków).') from e
        elif action=='rivalry':
            x,y=sorted((str(b.get('a','')),str(b.get('b',''))));require_club(c,x);require_club(c,y)
            if x==y:raise ValueError('Klub nie może być swoją kosą.')
            c.execute('INSERT OR IGNORE INTO dw_rivalries VALUES(?,?)' if b.get('enabled') else 'DELETE FROM dw_rivalries WHERE a=? AND b=?',(x,y))
        elif action=='assign':
            src=str(b.get('src',''));owner=b.get('club_id') or None;require_club(c,owner)
            if not any(p['src']==src for p in inventory(a,c)) and not c.execute('SELECT 1 FROM media WHERE src=?',(src,)).fetchone():raise ValueError('Nie znaleziono zdjęcia.')
            c.execute('INSERT INTO dw_photo_clubs VALUES(?,?) ON CONFLICT(src) DO UPDATE SET club_id=excluded.club_id',(src,owner))
        elif action=='method_add':
            method=b.get('method');src=str(b.get('src',''))
            if method not in METHODS:raise ValueError('Nieznana metoda.')
            source=a.asset_path(src)
            if not source.is_file() or source.suffix.lower() not in ('.jpg','.jpeg','.png','.webp'):raise ValueError('Wybierz istniejące zdjęcie.')
            raw=source.read_bytes();target=f'Produkcja/Metody_znakowania/{METHODS[method]}/dw-{hashlib.sha256(raw).hexdigest()[:20]}{source.suffix.lower()}'
            dest=a.safe(a.SOURCE,target);dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():dest.write_bytes(raw)
            owner=b.get('club_id') or None;require_club(c,owner)
            c.execute('INSERT OR IGNORE INTO dw_method_photos(method,src,alt) VALUES(?,?,?)',(method,target,str(b.get('alt',''))[:250]))
            c.execute('INSERT INTO dw_photo_clubs VALUES(?,?) ON CONFLICT(src) DO UPDATE SET club_id=excluded.club_id',(target,owner));detail['src']=target
        elif action=='method_remove':c.execute('DELETE FROM dw_method_photos WHERE id=?',(b.get('photo_id'),))
        else:raise ValueError('Nieznana operacja klubów.')
        record(a,c,action,detail)
        c.execute("UPDATE dw_club_meta SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")
        target=a.SOURCE/'js/dw-clubs-data.json';old=target.read_bytes() if target.exists() else None
        try:
            a.atomic(target,a.dumps(payload(c)));c.commit()
        except Exception:
            c.rollback()
            if old is not None:a.atomic(target,old.decode('utf-8'))
            raise
    return state(a)

def copy_binding(c,old,new):
    row=c.execute('SELECT club_id FROM dw_photo_clubs WHERE src=?',(old,)).fetchone()
    if row:c.execute('INSERT INTO dw_photo_clubs VALUES(?,?) ON CONFLICT(src) DO UPDATE SET club_id=excluded.club_id',(new,row[0]))
