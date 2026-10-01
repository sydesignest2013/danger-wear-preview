"""Local Danger Wear editor. Source tree is read-only; every write stays in APP."""
from __future__ import annotations
import base64, copy, hashlib, io, json, mimetypes, os, re, secrets, shutil, sqlite3, sys, threading, time, traceback, unicodedata, uuid, webbrowser, zipfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import unquote, urlsplit, parse_qs
from lxml import html, etree
import clubs
from dw_social import engine as social_engine
from PIL import Image, ImageOps, ImageCms, UnidentifiedImageError

APP = Path(__file__).resolve().parent
CONFIG = json.loads((APP / 'config.json').read_text('utf-8'))
def configured_path(value):
    p=Path(value).expanduser()
    return (p if p.is_absolute() else APP/p).resolve()
SOURCE = configured_path(os.environ.get('DW_SOURCE',CONFIG['source']))
DATA = configured_path(os.environ.get('DW_DATA',CONFIG.get('data_dir','data')))
BASE = DATA / 'source-snapshot'
FOLDER_MODE = CONFIG.get('publication_mode')=='folder'
if FOLDER_MODE:BASE=SOURCE
DB = DATA / 'manager.sqlite3'
PORT = int(os.environ.get('DW_PORT', CONFIG.get('port',8765)))
ADMIN_BASE = os.environ.get('DW_ADMIN_PATH',CONFIG.get('admin_path','/admin')).rstrip('/')
if not re.fullmatch(r'/[a-zA-Z0-9_-]+',ADMIN_BASE):raise ValueError('Ścieżka panelu musi mieć postać /admin lub /inna-nazwa.')
PUBLIC_ORIGIN = os.environ.get('DW_PUBLIC_ORIGIN','').rstrip('/')
BIND = os.environ.get('DW_BIND','127.0.0.1')
if PUBLIC_ORIGIN and (urlsplit(PUBLIC_ORIGIN).scheme!='https' or not urlsplit(PUBLIC_ORIGIN).netloc or urlsplit(PUBLIC_ORIGIN).path):raise ValueError('DW_PUBLIC_ORIGIN musi być adresem HTTPS bez ścieżki.')
TOKEN = secrets.token_urlsafe(32)
STOP_TOKEN = secrets.token_urlsafe(48)
SESSIONS = {}
LOGIN_FAILURES = {}
AUTH_LOCK = threading.RLock()
SESSION_IDLE = 30 * 60
SESSION_MAX = 8 * 60 * 60
LOCK = threading.RLock()
PUBLISH_LOCK = threading.Lock()
LIMITS = {'lifestyle':5,'realizacje':18}
FIELDS = ['Materiał','Krój','Znakowanie','Personalizacja']
CATEGORIES = [dict(id='sportswear',name='SPORTSWEAR',url='fightwear.html#sportswear',active=True),dict(id='fightwear',name='FIGHTWEAR',url='fightwear.html#fightwear',active=True),dict(id='streetwear',name='STREETWEAR',url='streetwear.html',active=True),dict(id='akcesoria',name='AKCESORIA',url='akcesoria.html',active=True)]
Image.MAX_IMAGE_PIXELS = 40_000_000

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def uid(): return uuid.uuid4().hex
def dumps(x): return json.dumps(x,ensure_ascii=False,separators=(',',':'))
class ManagedConnection(sqlite3.Connection):
    def __exit__(self,*args):
        try:return super().__exit__(*args)
        finally:self.close()

def connect():
    con=sqlite3.connect(DB, timeout=20,factory=ManagedConnection)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con
def auth_record():
    with connect() as con:
        row=con.execute('SELECT value FROM settings WHERE key="auth"').fetchone()
    return json.loads(row[0]) if row else None
def hash_password(password):
    if not isinstance(password,str) or not 12<=len(password)<=128:raise ValueError('Hasło powinno mieć od 12 do 128 znaków.')
    salt=secrets.token_bytes(32)
    digest=hashlib.scrypt(password.encode('utf-8'),salt=salt,n=2**17,r=8,p=1,maxmem=256*1024*1024,dklen=32)
    return {'algorithm':'scrypt','n':2**17,'r':8,'p':1,'salt':salt.hex(),'hash':digest.hex()}
def password_matches(password,record):
    if not record or not isinstance(password,str) or len(password)>128:return False
    digest=hashlib.scrypt(password.encode('utf-8'),salt=bytes.fromhex(record['salt']),n=record['n'],r=record['r'],p=record['p'],maxmem=256*1024*1024,dklen=32)
    return secrets.compare_digest(digest.hex(),record['hash'])
def session_key(raw):return hashlib.sha256(raw.encode()).hexdigest()
def check_login_limit(client):
    cutoff=time.time()-15*60
    LOGIN_FAILURES[client]=[t for t in LOGIN_FAILURES.get(client,[]) if t>cutoff]
    if len(LOGIN_FAILURES[client])>=5:raise LoginLimited('Za dużo nieudanych prób. Spróbuj ponownie za 15 minut.')
def safe(root,relative):
    p=(root / relative).resolve()
    if not p.is_relative_to(root.resolve()): raise ValueError('Niedozwolona ścieżka.')
    return p
def atomic(path,content):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp-'+uid())
    tmp.write_text(content,encoding='utf-8'); os.replace(tmp,path)
def class_nodes(doc,name): return doc.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," '+name+' ")]')
def first_class(doc,name):
    a=class_nodes(doc,name); return a[0] if a else None
def text(node): return ''.join(node.itertext()).strip() if node is not None else ''
def set_text(node,value):
    if node is None:return
    for c in list(node):node.remove(c)
    node.text=str(value)
def slugify(s):
    s=unicodedata.normalize('NFKD',s.replace('ł','l').replace('Ł','L')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','-',s).strip('-')[:100] or 'produkt'
def settings(con): return json.loads(con.execute('SELECT value FROM settings WHERE key="catalog"').fetchone()[0])
def audit(con,event,object_id,detail=''):con.execute('INSERT INTO events(at,event,object_id,detail) VALUES(?,?,?,?)',(now(),event,object_id,detail))
def get_product(con,id):
    row=con.execute('SELECT * FROM products WHERE id=?',(id,)).fetchone()
    if not row:raise ValueError('Nie znaleziono produktu.')
    p=json.loads(row['draft']);p.update(id=row['id'],revision=row['revision'],published_revision=row['published_revision'],updated=row['updated'])
    if FOLDER_MODE:
        import folder_site
        p=folder_site.editor_product(sys.modules[__name__],p,con)
    p['parameters']=parameters(p)
    return clubs.decorate(con,p)
def parameters(p):
    if 'parameters' in p:return p['parameters']
    # Preserve arbitrary original labels; migration never forces them into four preset keys.
    values=p.get('original_specs') if p.get('imported') and p.get('revision',1)==1 else p.get('specs')
    return [{'name':k,'value':v} for k,v in (values or p.get('specs',{})).items()]
def asset_path(src):
    if src.startswith('media/'): return safe(DATA/'media',src[len('media/'):])
    path=safe(BASE,src)
    if FOLDER_MODE and not path.is_file():return safe(DATA/'source-snapshot',src)
    return path
def read_gallery(raw):
    m=re.search(r'window\.DW_GALLERIES\s*=\s*',raw)
    if not m:return {'lifestyle':[],'realizacje':[]}
    try:return json.JSONDecoder().raw_decode(raw[m.end():])[0]
    except ValueError:raise ValueError('Dane galerii nie są poprawnym JSON; wymagają ręcznej analizy.')
def import_product(path,catalog):
    raw=path.read_text('utf-8-sig');doc=html.fromstring(raw)
    info=first_class(doc,'fw-info');h=info.find('h1') if info is not None else None
    title=text(h) or path.stem
    cats=class_nodes(doc,'fw-kicker'); href=cats[0].xpath('.//a/@href')[-1] if cats else ''
    category=next((c['id'] for c in catalog['categories'] if c['url']==href),'sportswear')
    specs={text(el.find('dt')):text(el.find('dd')) for el in doc.xpath('//dl[contains(@class,"fw-specs")]/div')}
    table=first_class(doc,'fw-data-fold');tables=table.xpath('.//table') if table is not None else []
    size={'mode':'none','columns':[],'rows':[],'unit':'','tolerance':'','instructions':''}
    if tables:
        t=tables[0];cols=[text(x) for x in t.xpath('.//thead/tr/*')][1:]
        rows=[{'name':text(tr[0]),'values':[text(x) for x in list(tr)[1:]]} for tr in t.xpath('.//tbody/tr')]
        size.update(mode='custom',columns=cols,rows=rows)
    marking=first_class(doc,'mesh-marking-body');icon=doc.xpath('//*[@id="znakowanie"]//img/@src')
    method={'id':'method-'+slugify(text(marking.find('strong')) if marking is not None else 'do-ustalenia'),'name':text(marking.find('strong')) if marking is not None else 'DO USTALENIA','short':specs.get('Znakowanie',''),'description':text(marking.find('p')) if marking is not None else '', 'icon':icon[0] if icon else '', 'alt':(doc.xpath('//*[@id="znakowanie"]//img/@alt') or [''])[0], 'url':(marking.xpath('.//a/@href') or ['produkcja.html'])[0] if marking is not None else 'produkcja.html','active':True}
    if not any(x['id']==method['id'] for x in catalog['methods']):catalog['methods'].append(method)
    galleries=read_gallery(raw)
    for kind in LIMITS:
        for item in galleries.get(kind,[]):item.setdefault('alt',item.get('title',''));item.setdefault('subtitle','');item.setdefault('position','50% 50%')
    return {'slug':path.stem,'url':path.name,'source':path.name,'name':title,'description':text(first_class(doc,'fw-lead')),'category':category,'specs':{k:specs.get(k,'') for k in FIELDS},'original_specs':specs,'methods':[method], 'size':size,'galleries':{k:galleries.get(k,[]) for k in LIMITS},'autoplay':True,'archived':False,'imported':True,'seo_description':'','notes':['Dane źródłowe wymagają przeglądu.'] if any(k not in FIELDS for k in specs) else []}

def index_media(con):
    manifest=json.loads((DATA/'source-manifest.json').read_text('utf-8')) if not FOLDER_MODE else {}
    for p in BASE.rglob('*'):
        if FOLDER_MODE:
            import folder_site
            if not folder_site.public_file(BASE,p):continue
        if p.suffix.lower() not in ('.jpg','.jpeg','.png','.webp') or not p.is_file():continue
        try:
            with Image.open(p) as im:w,h=im.size
        except (OSError,Image.DecompressionBombError):continue
        con.execute('INSERT OR IGNORE INTO media VALUES(?,?,?,?,?,?,?,?)',(uid(),p.relative_to(BASE).as_posix(),p.name,w,h,p.stat().st_size,'',manifest.get(p.relative_to(BASE).as_posix()) or hashlib.sha256(p.read_bytes()).hexdigest()))

def initialize():
    DATA.mkdir(parents=True,exist_ok=True)
    with connect() as con:
        con.executescript('''CREATE TABLE IF NOT EXISTS products(id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL, draft TEXT NOT NULL, revision INTEGER NOT NULL, published_revision INTEGER, updated TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS versions(id INTEGER PRIMARY KEY,product_id TEXT NOT NULL,revision INTEGER NOT NULL,data TEXT NOT NULL,at TEXT NOT NULL,UNIQUE(product_id,revision));
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS media(id TEXT PRIMARY KEY,src TEXT UNIQUE NOT NULL,name TEXT NOT NULL,width INTEGER,height INTEGER,bytes INTEGER,original TEXT,hash TEXT);
        CREATE TABLE IF NOT EXISTS releases(id TEXT PRIMARY KEY,at TEXT NOT NULL,manifest TEXT NOT NULL,status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,at TEXT,event TEXT,object_id TEXT,detail TEXT);
        PRAGMA user_version=1;''')
        if con.execute('SELECT count(*) FROM products').fetchone()[0]:
            if not con.execute('SELECT count(*) FROM media').fetchone()[0]:index_media(con)
            return
    if not SOURCE.is_dir():raise RuntimeError('Brak folderu źródłowego. Sprawdź config.json i dostępność dysku G:.')
    print('Tworzenie oddzielnej kopii źródeł. Oryginał pozostaje bez zmian.',flush=True)
    BASE.mkdir(parents=True,exist_ok=True)
    manifest={}
    for p in SOURCE.rglob('*'):
        rel=p.relative_to(SOURCE)
        if FOLDER_MODE:
            import folder_site
            if not folder_site.public_file(SOURCE,p):continue
        if any(x.upper().startswith('BACKUP') or x in ('tools','.git') for x in rel.parts):continue
        if not p.is_file() or p.suffix.lower() in ('.zip','.bat','.ps1','.exe'):continue
        dst=BASE/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        if p.resolve()!=dst.resolve():shutil.copy2(p,dst)
        manifest[rel.as_posix()]=hashlib.sha256(dst.read_bytes()).hexdigest()
    atomic(DATA/'source-manifest.json',dumps(manifest))
    catalog={'revision':1,'categories':copy.deepcopy(CATEGORIES),'methods':[],'templates':[]}
    report={'at':now(),'source':str(SOURCE),'products':[],'errors':[],'missing_media':[]}
    with connect() as con:
        for p in sorted(BASE.glob('*.html')):
            if 'UNIFIED_PRODUCT_TEMPLATE:20260916-1800' not in p.read_text('utf-8-sig'):continue
            try:
                data=import_product(p,catalog);id=uid()
                con.execute('INSERT INTO products VALUES(?,?,?,?,?,?)',(id,data['url'],dumps(data),1,1,now()))
                con.execute('INSERT INTO versions(product_id,revision,data,at) VALUES(?,?,?,?)',(id,1,dumps(data),now()))
                report['products'].append({'id':id,'url':data['url'],'lifestyle':len(data['galleries']['lifestyle']),'realizacje':len(data['galleries']['realizacje']),'notes':data['notes']})
            except Exception as ex:report['errors'].append({'file':p.name,'error':str(ex)})
        index_media(con)
        con.execute('INSERT OR REPLACE INTO settings VALUES("catalog",?)',(dumps(catalog),))
        for row in con.execute('SELECT draft FROM products'):
            p=json.loads(row[0])
            for kind in LIMITS:
                for item in p['galleries'][kind]:
                    if not asset_path(item['src']).is_file():report['missing_media'].append({'product':p['url'],'src':item['src']})
        audit(con,'import','all',str(len(report['products']))+' produktów')
    atomic(DATA/'import-report.json',json.dumps(report,ensure_ascii=False,indent=2))
    atomic(DATA/'current.json',dumps({'release':'source'}))
    print('Import zakończony: '+str(len(report['products']))+' produktów.',flush=True)

def validate(p,publishing=False):
    errors=[];warnings=[]
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,99}',p.get('slug','')):errors.append('Adres: użyj małych liter, cyfr i łączników (do 100 znaków).')
    if p.get('url')!=p.get('slug','')+'.html':errors.append('Adres produktu nie odpowiada slugowi.')
    if len(p.get('name',''))>120:errors.append('Nazwa może mieć maksymalnie 120 znaków.')
    if publishing and len(p.get('name','').strip())<3:errors.append('Nazwa wymaga minimum 3 znaków.')
    if publishing and not 20<=len(p.get('description',''))<=3000:errors.append('Opis wymaga od 20 do 3000 znaków.')
    if len(p.get('description',''))>3000:errors.append('Opis może mieć maksymalnie 3000 znaków.')
    with connect() as con:cat=settings(con)
    c=next((c for c in cat['categories'] if c['id']==p.get('category')),None)
    if not c or (publishing and not c.get('active',True)):errors.append('Wybierz aktywną kategorię.')
    rows=parameters(p)
    if not isinstance(rows,list) or len(rows)>100:
        errors.append('Lista parametrów ma nieprawidłowy format lub przekracza 100 wierszy.');rows=[]
    else:
        for i,r in enumerate(rows):
            if not isinstance(r,dict) or not isinstance(r.get('name',''),str) or not isinstance(r.get('value',''),str):
                errors.append(f'Parametr {i+1}: nazwa i wartość muszą być tekstem.');continue
            name=str(r.get('name',''));value=str(r.get('value',''))
            if len(name)>120 or len(value)>1000:errors.append(f'Parametr {i+1}: maksymalnie 120 znaków nazwy i 1000 znaków wartości.')
            if publishing and (not name.strip() or not value.strip()):errors.append(f'Parametr {i+1}: wpisz nazwę i wartość albo usuń pusty wiersz.')
    for kind,limit in LIMITS.items():
        items=p.get('galleries',{}).get(kind,[])
        if len(items)>limit:errors.append(f'Osiągnięto limit {limit} zdjęć {kind}. Usuń lub zastąp zdjęcie.')
        if publishing and kind=='lifestyle' and not items:errors.append('Publikacja wymaga minimum jednego zdjęcia lifestyle.')
        for i,item in enumerate(items):
            try:
                if not asset_path(item.get('src','')).is_file():(errors if publishing else warnings).append(f'{kind} {i+1}: brak pliku zdjęcia.')
            except ValueError:errors.append('Niedozwolona ścieżka zdjęcia.')
            for key,maxlen in [('title',120),('subtitle',180),('alt',250)]:
                if len(item.get(key,''))>maxlen:errors.append(f'{kind} {i+1}: za długi {key}.')
            if not item.get('alt','').strip():warnings.append(f'{kind} {i+1}: uzupełnij tekst alternatywny.')
    sz=p.get('size',{})
    if sz.get('mode')!='none':
        cols=sz.get('columns',[]);rows=sz.get('rows',[])
        if not cols or not rows:errors.append('Tabela wymaga rozmiarów i pomiarów.')
        if len(cols)>30 or len(rows)>30:errors.append('Tabela może mieć maksymalnie 30 rozmiarów i 30 pomiarów.')
        if len(set(x.strip().casefold() for x in cols))!=len(cols) or any(not x.strip() for x in cols):errors.append('Nazwy rozmiarów muszą być unikalne i niepuste.')
        names=[r.get('name','').strip().casefold() for r in rows]
        if len(set(names))!=len(names) or any(not x for x in names):errors.append('Nazwy pomiarów muszą być unikalne i niepuste.')
        for row in rows:
            if len(row.get('values',[]))!=len(cols):errors.append('Liczba komórek tabeli jest niezgodna.')
            for v in row.get('values',[]):
                if v in ('—','-'):continue
                if not publishing and not str(v).strip():continue
                try:
                    n=float(str(v).replace(',','.'))
                    if not 0<n<100000:raise ValueError()
                except (ValueError,TypeError):errors.append('Pomiary muszą być dodatnie. Brak danych oznacz „—”.')
        if not sz.get('unit'):warnings.append('Jednostka tabeli niepotwierdzona — nie dopisujemy cm automatycznie.')
        if not sz.get('tolerance'):warnings.append('Tolerancja tabeli nie została określona.')
    methods=p.get('methods',[])
    for m in methods:
        if not valid_url(m.get('url','')):errors.append('Niepoprawny link metody znakowania.')
        if m.get('icon'):
            try:
                if not asset_path(m['icon']).is_file():errors.append('Brak ikony metody '+m.get('name',''))
            except ValueError:errors.append('Niepoprawna ścieżka ikony.')
    summary=', '.join(m.get('short') or m['name'] for m in methods)
    marking=next((r.get('value','') for r in rows if isinstance(r,dict) and isinstance(r.get('name'),str) and r['name'].strip().casefold()=='znakowanie'),None)
    if summary and isinstance(marking,str) and marking.casefold()!=summary.casefold():warnings.append('Parametr „Znakowanie” różni się od wybranych metod.')
    return list(dict.fromkeys(errors)),list(dict.fromkeys(warnings+p.get('notes',[])))
def valid_url(s):
    if not s:return True
    u=urlsplit(s)
    return (u.scheme in ('https','http') and bool(u.netloc)) or (not u.scheme and not u.netloc and not s.startswith(('/','\\')) and '..' not in s and '\\' not in s)

def render_product(p,catalog):
    template=safe(BASE,p.get('source') or 'koszulki-sportowe.html')
    if not template.is_file():template=BASE/'koszulki-sportowe.html'
    doc=html.fromstring(template.read_text('utf-8-sig'))
    for node in doc.xpath('//h1'):
        set_text(node,p['name']);node.set('data-glitch-text',p['name'])
    for node in doc.xpath('//title'):set_text(node,p['name']+' | Danger Wear Production')
    for node in class_nodes(doc,'mesh-ref-main'):node.set('aria-label','Karta produktu '+p['name'])
    desc=first_class(doc,'fw-lead');set_text(desc,p.get('description',''))
    if desc is not None:desc.set('style','white-space:pre-line')
    if p.get('seo_description'):
        meta=etree.SubElement(doc.find('head'),'meta',name='description',content=p['seo_description'])
    cat=next(c for c in catalog['categories'] if c['id']==p['category'])
    for node in class_nodes(doc,'fw-kicker'):
        links=node.xpath('.//a')
        if links:links[-1].set('href',cat['url']);set_text(links[-1],cat['name'])
    for node in class_nodes(doc,'mesh-category-return'):node.set('href',cat['url']);set_text(node,'WRÓĆ DO '+cat['name'])
    for node in doc.xpath('//a[starts-with(@href,"kontakt.html?produkt=")]'):node.set('href','kontakt.html?produkt='+p['slug'])
    spec=first_class(doc,'fw-specs')
    if spec is not None:
        set_text(spec,'')
        for item in parameters(p):
            row=etree.SubElement(spec,'div');etree.SubElement(row,'dt').text=item.get('name','');etree.SubElement(row,'dd').text=item.get('value','')
        if not parameters(p):spec.getparent().remove(spec)
    fold=first_class(doc,'fw-data-fold');size=p['size']
    if fold is not None:
        if size['mode']=='none':fold.getparent().remove(fold)
        else:
            body=first_class(fold,'fw-data-fold-body');set_text(body,'');body.set('class','fw-data-fold-body table-wrap')
            t=etree.SubElement(body,'table');head=etree.SubElement(etree.SubElement(t,'thead'),'tr');etree.SubElement(head,'th').text='Pomiar'
            for col in size['columns']:etree.SubElement(head,'th',scope='col').text=col
            tbody=etree.SubElement(t,'tbody')
            for r in size['rows']:
                tr=etree.SubElement(tbody,'tr');etree.SubElement(tr,'th',scope='row').text=r['name']
                for value in r['values']:etree.SubElement(tr,'td').text=str(value)
            notes=[]
            if size.get('unit'):notes.append('Jednostka: '+size['unit'])
            if size.get('tolerance'):notes.append('Tolerancja: '+size['tolerance'])
            if size.get('instructions'):notes.append(size['instructions'])
            if notes:etree.SubElement(body,'p').text=' · '.join(notes)
    marking=doc.get_element_by_id('znakowanie',None)
    if marking is not None:
        if not p.get('methods'):marking.getparent().remove(marking)
        else:
            panel=first_class(marking,'fw-mark-panel');body=first_class(marking,'mesh-marking-body');set_text(panel,'');set_text(body,'')
            for method in p['methods']:
                if method.get('icon'):
                    badge=etree.SubElement(panel,'span',{'class':'mark-badge'});etree.SubElement(badge,'img',src=method['icon'],alt=method.get('alt') or method['name'])
                section=etree.SubElement(body,'section');etree.SubElement(section,'strong').text=method['name'];etree.SubElement(section,'p').text=method.get('description','')
                if method.get('url'):etree.SubElement(section,'a',href=method['url']).text='POZNAJ PROCES PRODUKCJI →'
            etree.SubElement(panel,'span',{'class':'fw-mark-plus','aria-hidden':'true'}).text='+'
    for node in doc.xpath('//script'):
        if 'window.DW_GALLERIES' in (node.text or ''):node.text='window.DW_GALLERIES='+dumps(p['galleries']).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')+';window.DW_AUTOPLAY='+str(bool(p.get('autoplay',True))).lower()+';'
        if node.get('src','').startswith('js/mesh-card.js'):node.set('src','js/dw-gallery.js')
    return html.tostring(doc,encoding='unicode',doctype='<!DOCTYPE html>')

def update_navigation(raw,products,catalog,filename):
    doc=html.fromstring(raw)
    active=[p for p in products if not p.get('archived')]
    reference=html.fromstring((BASE/'koszulki-sportowe.html').read_text('utf-8-sig'))
    order=reference.xpath('//div[contains(@class,"products-dropdown")]//a/@href')
    custom=catalog.get('product_order',{})
    def rank(p):
        chosen=custom.get(p['category'],[])
        return chosen.index(p['url']) if p['url'] in chosen else len(chosen)+(order.index(p['url']) if p['url'] in order else 1000)
    active.sort(key=rank)
    this=next((p for p in active if p['url']==filename),None)
    if this:
        category=next(c for c in catalog['categories'] if c['id']==this['category'])
        for node in class_nodes(doc,'fw-kicker'):
            links=node.xpath('.//a')
            if links:links[-1].set('href',category['url']);set_text(links[-1],category['name'])
        for node in class_nodes(doc,'mesh-category-return'):node.set('href',category['url']);set_text(node,'WRÓĆ DO '+category['name'])
    for selector in ['products-dropdown','mob-products-tree','nav-dropdown']:
        for menu in class_nodes(doc,selector):
            set_text(menu,'')
            sport_section=None
            for c in catalog['categories']:
                group=[p for p in active if p['category']==c['id']]
                if not group:continue
                if selector in ('products-dropdown','nav-dropdown'):
                    if c['id']=='fightwear' and sport_section is not None:parent=sport_section
                    else:parent=etree.SubElement(menu,'section')
                    if c['id']=='sportswear':sport_section=parent
                else:parent=menu
                etree.SubElement(parent,'a',href=c['url'],attrib={'class':'products-group' if selector=='products-dropdown' else 'nav-dropdown-label nav-dropdown-label-link'}).text=c['name']
                for p in group:etree.SubElement(parent,'a',href=p['url'],attrib={'class':'nav-dropdown-sub'} if selector=='nav-dropdown' else {}).text=p['name']
    for c in catalog['categories']:
        target=urlsplit(c['url'])
        if target.path!=filename:continue
        section=doc.get_element_by_id(target.fragment,None) if target.fragment else None
        lists=class_nodes(section if section is not None else doc,'dw-product-list')
        for listing in lists[:1]:
            set_text(listing,'')
            for p in active:
                if p['category']==c['id']:
                    li=etree.SubElement(listing,'li');etree.SubElement(li,'span').text=p['name'];etree.SubElement(li,'a',href=p['url']).text='ZOBACZ PRODUKT →'
    if filename=='produkty.html':
        for heading in doc.xpath('//h2[a]'):
            link=heading.find('a')
            c=next((x for x in catalog['categories'] if x['url']==link.get('href')),None)
            if c is None:continue
            set_text(link,c['name'])
            lists=heading.getparent().xpath('./ul')
            if not lists:continue
            listing=lists[0];set_text(listing,'')
            for p in active:
                if p['category']==c['id']:
                    li=etree.SubElement(listing,'li');etree.SubElement(li,'a',href=p['url']).text=p['name']
        grid=first_class(doc,'products-index-grid')
        if grid is not None:
            known=set(grid.xpath('.//h2/a/@href'))
            for c in catalog['categories']:
                if c['url'] in known or not any(p['category']==c['id'] for p in active):continue
                card=etree.SubElement(grid,'section',{'class':'products-index-card'});h=etree.SubElement(card,'h2');etree.SubElement(h,'a',href=c['url']).text=c['name'];listing=etree.SubElement(card,'ul')
                for p in active:
                    if p['category']==c['id']:etree.SubElement(etree.SubElement(listing,'li'),'a',href=p['url']).text=p['name']
    for menu in class_nodes(doc,'mob-sub'):
        set_text(menu,'');etree.SubElement(menu,'a',href='produkty.html').text='Wszystkie produkty'
        for c in catalog['categories']:
            if any(p['category']==c['id'] for p in active):etree.SubElement(menu,'a',href=c['url']).text=c['name']
    if filename=='kontakt.html':
        select=doc.get_element_by_id('produkt',None)
        if select is not None:
            set_text(select,'');etree.SubElement(select,'option',value='',disabled='',selected='').text='Wybierz produkt…'
            for c in catalog['categories']:
                group=etree.SubElement(select,'optgroup',label=c['name'])
                for p in active:
                    if p['category']==c['id']:etree.SubElement(group,'option',value=p['name']).text=p['name']
            etree.SubElement(select,'option',value='Inne').text='Inne'
            # The original contact script registers before this callback; set the canonical label afterwards.
            mapping={p['slug']:p['name'] for p in active}
            etree.SubElement(doc.find('body'),'script').text='document.addEventListener("DOMContentLoaded",()=>{const m='+dumps(mapping).replace('<','\\u003c')+';const k=new URLSearchParams(location.search).get("produkt");if(m[k]){const s=document.getElementById("produkt");s.value=m[k];s.classList.add("filled");const d=document.getElementById("opis");if(d.value==="Zapytanie o produkcję: "+k)d.value="";}});'
    return html.tostring(doc,encoding='unicode',doctype='<!DOCTYPE html>')

def current():return json.loads((DATA/'current.json').read_text('utf-8'))['release']
def published_products(con):
    if FOLDER_MODE:
        import folder_site
        return folder_site.live_products(sys.modules[__name__],con)
    release=current()
    if release=='source':
        return [dict(json.loads(r['data']),id=r['product_id'],revision=r['revision']) for r in con.execute('SELECT * FROM versions WHERE revision=1') if json.loads(r['data']).get('imported')]
    manifest=json.loads(con.execute('SELECT manifest FROM releases WHERE id=?',(release,)).fetchone()[0])
    return manifest['products']
def make_release(id,expected,action='publish',key=''):
    if FOLDER_MODE:
        import folder_site
        return folder_site.publish(sys.modules[__name__],id,expected,action,key)
    with PUBLISH_LOCK, LOCK, connect() as con:
        if key:
            previous=con.execute('SELECT id,manifest FROM releases WHERE status=?',('key:'+key,)).fetchone()
            if previous:return {'release':previous['id'],'url':'/','reused':True}
        p=get_product(con,id)
        if p['revision']!=expected:raise Conflict('Produkt zmienił się. Wczytaj aktualną wersję przed publikacją.')
        catalog=settings(con)
        errors,warnings=validate(p,True)
        if action=='publish' and errors:raise Validation(errors,warnings)
        items=[x for x in published_products(con) if x['id']!=id]
        if action=='publish':items.append(copy.deepcopy(p))
        release=time.strftime('%Y%m%d-%H%M%S')+'-'+uid()[:8]
        root=DATA/'releases'/release;root.mkdir(parents=True)
        try:
            for src in BASE.rglob('*'):
                if not src.is_file():continue
                dst=root/src.relative_to(BASE);dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(src,dst)
            if (DATA/'media').exists():shutil.copytree(DATA/'media',root/'media')
            (root/'js'/'dw-gallery.js').write_text((APP/'ui'/'gallery.js').read_text('utf-8'),encoding='utf-8')
            # Remove all source product cards; write only selected published snapshots.
            for row in con.execute('SELECT url FROM products'):
                path=safe(root,row[0])
                if path.is_file():path.unlink()
            for item in items:
                # Unedited imported products keep source markup; no silent rewrite of incomplete fields.
                if item['revision']==1 and item.get('imported'):
                    raw=safe(BASE,item['source']).read_text('utf-8-sig')
                else:raw=render_product(item,catalog)
                safe(root,item['url']).write_text(raw,encoding='utf-8')
            for category in catalog['categories']:
                if not any(p['category']==category['id'] for p in items):continue
                url=urlsplit(category['url']);dest=safe(root,url.path)
                if not dest.exists():
                    doc=html.fromstring((BASE/'streetwear.html').read_text('utf-8-sig'))
                    for node in doc.xpath('//title|//h1'):set_text(node,category['name'])
                    for node in class_nodes(doc,'dw-family'):
                        node.set('id',url.fragment or slugify(category['name']))
                        for h in node.xpath('./h2'):set_text(h,category['name'])
                        for label in class_nodes(node,'cat-eyebrow'):set_text(label,'Produkty / '+category['name'])
                    dest.write_text(html.tostring(doc,encoding='unicode',doctype='<!DOCTYPE html>'),encoding='utf-8')
            for file in root.glob('*.html'):
                file.write_text(update_navigation(file.read_text('utf-8-sig'),items,catalog,file.name),encoding='utf-8')
            manifest={'id':release,'at':now(),'products':items,'catalog':catalog,'action':action,'target':id,'files':{str(f.relative_to(root)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in root.rglob('*') if f.is_file()}}
            atomic(root/'release.json',dumps(manifest))
            con.execute('INSERT INTO releases VALUES(?,?,?,?)',(release,now(),dumps(manifest),'key:'+key if key else 'ready'))
            con.execute('UPDATE products SET published_revision=? WHERE id=?',(p['revision'] if action=='publish' else None,id))
            audit(con,action,id,release)
            con.commit()
            atomic(DATA/'current.json',dumps({'release':release}))
            return {'release':release,'url':'/'+(p['url'] if action=='publish' else 'index.html'),'warnings':warnings}
        except Exception:
            # Incomplete releases are never selected by current.json.
            raise

class Conflict(Exception):pass
class LoginLimited(Exception):pass
class LoginDenied(Exception):pass
class Validation(Exception):
    def __init__(self,errors,warnings=[]):self.errors=errors;self.warnings=warnings;super().__init__('Sprawdź zaznaczone dane.')

def backup():
    with LOCK:
        name='backup-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uid()[:6]+'.zip'
        target=DATA/'backups'/name;target.parent.mkdir(exist_ok=True)
        dbcopy=DATA/('backup-'+uid()+'.sqlite3')
        dest=sqlite3.connect(dbcopy)
        try:
            with connect() as source:source.backup(dest)
        finally:dest.close()
        try:
            with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
                z.write(dbcopy,'manager.sqlite3')
                for file in DATA.rglob('*'):
                    rel=file.relative_to(DATA)
                    if not file.is_file() or rel.parts[0] in ('backups','previews') or file==DB or file==dbcopy or file.name=='local-control.json' or file.name.endswith(('-wal','-shm')):continue
                    z.write(file,rel.as_posix())
                if FOLDER_MODE:
                    import folder_site
                    for file in SOURCE.rglob('*'):
                        if file.is_file() and folder_site.public_file(SOURCE,file):
                            z.write(file,'website/'+file.relative_to(SOURCE).as_posix())
            with zipfile.ZipFile(target) as z:
                corrupt=z.testzip()
                if corrupt:raise ValueError('Błąd weryfikacji kopii: '+corrupt)
        finally:dbcopy.unlink(missing_ok=True)
        return {'name':name,'bytes':target.stat().st_size}

class Handler(BaseHTTPRequestHandler):
    server_version='DangerWearLocal/1.0'
    def log_message(self,fmt,*args):print(time.strftime('%H:%M:%S'),fmt%args,flush=True)
    def send_json(self,data,status=200):self.send_data(dumps(data).encode(), 'application/json; charset=utf-8',status)
    def send_data(self,data,mime,status=200):
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','SAMEORIGIN');self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy','same-origin')
        if getattr(self,'session_cookie',None):self.send_header('Set-Cookie',self.session_cookie)
        self.end_headers()
        try:self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError):pass
    def host_ok(self):return self.headers.get('Host') in [f'127.0.0.1:{PORT}',f'localhost:{PORT}']+([urlsplit(PUBLIC_ORIGIN).netloc] if PUBLIC_ORIGIN else [])
    def redirect(self,target):
        self.send_response(308);self.send_header('Location',target);self.send_header('Content-Length','0');self.send_header('Cache-Control','no-store');self.end_headers()
    def session_id(self):
        try:
            cookies=SimpleCookie();cookies.load(self.headers.get('Cookie',''))
            raw=cookies['dw_session'].value if 'dw_session' in cookies else ''
            return session_key(raw) if raw else ''
        except Exception:return ''
    def authenticated(self):
        with AUTH_LOCK:
            key=self.session_id();session=SESSIONS.get(key)
            if not session:return False
            at=time.time()
            if at-session['last']>SESSION_IDLE or at-session['created']>SESSION_MAX:
                SESSIONS.pop(key,None);return False
            session['last']=at;return True
    def create_session(self):
        raw=secrets.token_urlsafe(48);at=time.time()
        with AUTH_LOCK:
            for key in list(SESSIONS):
                if at-SESSIONS[key]['last']>SESSION_IDLE or at-SESSIONS[key]['created']>SESSION_MAX:SESSIONS.pop(key,None)
            if len(SESSIONS)>=10:SESSIONS.pop(min(SESSIONS,key=lambda k:SESSIONS[k]['created']))
            SESSIONS[session_key(raw)]={'created':at,'last':at}
        self.session_cookie=f'dw_session={raw}; Path={ADMIN_BASE}/; HttpOnly; SameSite=Strict; Max-Age={SESSION_MAX}'+('; Secure' if PUBLIC_ORIGIN else '')
    def clear_session(self):
        with AUTH_LOCK:SESSIONS.pop(self.session_id(),None)
        self.session_cookie=f'dw_session=; Path={ADMIN_BASE}/; HttpOnly; SameSite=Strict; Max-Age=0'+('; Secure' if PUBLIC_ORIGIN else '')
    def do_GET(self):
        if not self.host_ok():return self.send_json({'error':'Nieprawidłowy host.'},403)
        try:self.get()
        except (ValueError,FileNotFoundError) as ex:self.send_json({'error':str(ex)},404)
        except Exception:traceback.print_exc();self.send_json({'error':'Błąd programu. Szczegóły w dzienniku serwera.'},500)
    def get(self):
        path=unquote(urlsplit(self.path).path);query=parse_qs(urlsplit(self.path).query)
        if path==ADMIN_BASE:
            suffix=urlsplit(self.path).query
            return self.redirect(ADMIN_BASE+'/'+('?' + suffix if suffix else ''))
        if path=='/api/health':return self.send_json({'app':'DangerWearManager','status':'ok','app_dir':str(APP)})
        if path=='/login':return self.redirect(ADMIN_BASE+'/login')
        if path.startswith(ADMIN_BASE+'/'):path=path[len(ADMIN_BASE):]
        else:path=path if path.startswith('/site/') else '/site/'+path.lstrip('/')
        signed_in=self.authenticated()
        if path in ('/','/login'):
            file='index.html' if signed_in else 'login.html'
            return self.send_data((APP/'ui'/file).read_text('utf-8').replace('__TOKEN__',TOKEN).replace('__ADMIN_BASE__',ADMIN_BASE).encode(),'text/html; charset=utf-8')
        if path=='/api/auth':return self.send_json({'configured':bool(auth_record()),'authenticated':signed_in})
        if path=='/api/health':return self.send_json({'app':'DangerWearManager','status':'ok','app_dir':str(APP)})
        public_ui=path in ('/ui/style.css','/ui/login.js')
        public_logo=path in ('/asset/assets/images/dangerwear-logo.webp','/asset/assets/images/DW-logotyp.svg')
        if not signed_in and not public_ui and not public_logo and not path.startswith('/site/'):
            return self.send_json({'error':'Zaloguj się, aby otworzyć panel.','login_required':True},401)
        if path=='/social':
            page=(APP/'ui'/'dw-social.html').read_text('utf-8').replace('%%TOKEN%%',TOKEN).replace('%%BASE%%',ADMIN_BASE)
            return self.send_data(page.encode(),'text/html; charset=utf-8')
        if path=='/api/social/library':return self.send_json(social_engine.library())
        if path=='/api/social/evidence':return self.send_json(social_engine.evidence())
        if path=='/api/social/month':
            month=query.get('month',[''])[0]
            return self.send_json({'pool':social_engine.rows(month),'calendar':social_engine.scheduled(month)})
        if path=='/api/social/image':
            src=query.get('src',[''])[0]
            if not any(x['src']==src for x in social_engine.library()['photos']):raise ValueError('Nie znaleziono zdjęcia w galerii.')
            if src.startswith('dw-social-uploads/'):
                p=safe(DATA/'dw-social-uploads',src[len('dw-social-uploads/'):])
            else:p=asset_path(src)
            if not p.is_file():raise ValueError('Brak zdjęcia.')
            mime=mimetypes.guess_type(p.name)[0]
            if mime not in ('image/png','image/jpeg','image/webp'):raise ValueError('Nieobsługiwany format zdjęcia.')
            return self.send_data(p.read_bytes(),mime)

        if path=='/api/clubs':return self.send_json(clubs.state(sys.modules[__name__]))
        if path=='/api/publication-check' and FOLDER_MODE:
            return self.send_json(__import__('folder_site').publication_check(sys.modules[__name__],query.get('id',[''])[0]))
        if path=='/api/state':
            with connect() as con:
                products=[get_product(con,r[0]) for r in con.execute('SELECT id FROM products ORDER BY url')]
                for p in products:p['errors'],p['warnings']=validate(p,True)
                return self.send_json({'products':products,'catalog':settings(con),'source':str(SOURCE),'storage':str(DATA),'release':current(),'local':True,'folder_mode':FOLDER_MODE})
        if path=='/api/media':
            with connect() as con:
                items=[dict(r) for r in con.execute('SELECT * FROM media ORDER BY rowid DESC')]
                usage={}
                for row in con.execute('SELECT draft FROM products'):
                    p=json.loads(row[0])
                    for k in LIMITS:
                        for item in p['galleries'][k]:usage.setdefault(item['src'],set()).add(p['name'])
                for item in items:item['usage']=sorted(usage.get(item['src'],set()))
                return self.send_json(items)
        if path=='/api/history':
            with connect() as con:
                versions=[dict(r) for r in con.execute('SELECT id,product_id,revision,at FROM versions WHERE product_id=? ORDER BY revision DESC',(query.get('id',[''])[0],))]
                releases=[{'id':r['id'],'at':r['at']} for r in con.execute('SELECT * FROM releases ORDER BY at DESC')]
                return self.send_json({'versions':versions,'releases':releases,'current':current()})
        if path.startswith('/ui/'):
            p=safe(APP/'ui',path[len('/ui/'):])
        elif path.startswith('/asset/'):
            p=asset_path(path[len('/asset/'):])
        elif path.startswith('/preview/'):
            parts=path[len('/preview/'):].split('/',1)
            if len(parts)!=2:raise ValueError('Brak podglądu.')
            root=safe(DATA/'previews',parts[0]);rel=parts[1]
            if not root.is_dir() or time.time()-root.stat().st_mtime>3600:raise ValueError('Podgląd wygasł. Utwórz nowy podgląd z panelu.')
            p=safe(root,rel)
            if not p.is_file():
                if rel=='js/dw-gallery.js':p=APP/'ui'/'gallery.js'
                else:p=asset_path(rel)
        elif path.startswith('/site/'):
            rel=path[len('/site/'):] or 'index.html';r=current();root=BASE if FOLDER_MODE or r=='source' else safe(DATA/'releases',r);p=safe(root,rel)
            if FOLDER_MODE:
                import folder_site
                if not folder_site.public_file(root,p):raise ValueError('Nie znaleziono pliku.')
            if p.name=='release.json' or (rel!='js/dw-clubs-data.json' and p.suffix.lower() not in ('.html','.css','.js','.jpg','.jpeg','.png','.webp','.gif','.svg','.ico','.woff','.woff2','.ttf','.mp4','.webm','.pdf','.txt')):raise ValueError('Nie znaleziono pliku.')
        else:raise ValueError('Nie znaleziono pliku.')
        if not p.is_file():raise ValueError('Nie znaleziono pliku.')
        mime=mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
        if mime.startswith('text/') or mime=='application/javascript':mime+='; charset=utf-8'
        self.send_data(p.read_bytes(),mime)
    def do_POST(self):
        path=unquote(urlsplit(self.path).path)
        if not path.startswith(ADMIN_BASE+'/'):return self.send_json({'error':'Nie znaleziono operacji.'},404)
        path=path[len(ADMIN_BASE):]
        if not self.host_ok() or self.headers.get('X-DW-Token')!=TOKEN or self.headers.get('Origin') not in [f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}']+([PUBLIC_ORIGIN] if PUBLIC_ORIGIN else []):
            return self.send_json({'error':'Żądanie spoza lokalnego panelu zostało zablokowane.'},403)
        local_stop=path=='/api/shutdown' and secrets.compare_digest(self.headers.get('X-DW-Stop',''),STOP_TOKEN)
        if path not in ('/api/login','/api/setup') and not local_stop and not self.authenticated():
            return self.send_json({'error':'Sesja wygasła. Zaloguj się ponownie.','login_required':True},401)
        try:
            length=int(self.headers.get('Content-Length',0))
            if path in ('/api/setup','/api/login','/api/password') and length>4096:raise ValueError('Żądanie logowania jest za duże.')
            if length>29_000_000:raise ValueError('Plik jest za duży. Limit zdjęcia: 20 MB.')
            body=json.loads(self.rfile.read(length))
            with LOCK:result=self.post(path,body)
            self.send_json(result)
        except Conflict as ex:self.send_json({'error':str(ex)},409)
        except LoginLimited as ex:self.send_json({'error':str(ex)},429)
        except LoginDenied as ex:self.send_json({'error':str(ex)},401)
        except Validation as ex:self.send_json({'error':str(ex),'errors':ex.errors,'warnings':ex.warnings},422)
        except (ValueError,KeyError,TypeError,sqlite3.IntegrityError) as ex:self.send_json({'error':str(ex)},400)
        except Exception:traceback.print_exc();self.send_json({'error':'Operacja nie powiodła się. Poprzednie dane pozostają zachowane; sprawdź dziennik serwera.'},500)
    def post(self,path,b):
        if path in ('/api/setup','/api/login','/api/password'):
            client=self.client_address[0]
            check_login_limit(client)
            record=auth_record()
            if path=='/api/setup':
                if record:raise Conflict('Hasło zostało już ustawione. Zaloguj się.')
                if b.get('password')!=b.get('confirmation'):raise ValueError('Wpisane hasła nie są takie same.')
                record=hash_password(b.get('password'))
                with connect() as con:
                    con.execute('INSERT INTO settings(key,value) VALUES("auth",?)',(dumps(record),));audit(con,'password_setup','local-admin')
                self.create_session();return {'authenticated':True}
            if path=='/api/login':
                if not password_matches(b.get('password'),record):
                    LOGIN_FAILURES.setdefault(client,[]).append(time.time())
                    with connect() as con:audit(con,'login_failed','local-admin')
                    raise LoginDenied('Nieprawidłowe hasło.')
                LOGIN_FAILURES.pop(client,None);self.create_session()
                with connect() as con:audit(con,'login','local-admin')
                return {'authenticated':True}
            if not password_matches(b.get('current_password'),record):
                LOGIN_FAILURES.setdefault(client,[]).append(time.time());raise LoginDenied('Aktualne hasło jest nieprawidłowe.')
            if b.get('password')!=b.get('confirmation'):raise ValueError('Wpisane nowe hasła nie są takie same.')
            record=hash_password(b.get('password'))
            with connect() as con:
                con.execute('UPDATE settings SET value=? WHERE key="auth"',(dumps(record),));audit(con,'password_changed','local-admin')
            with AUTH_LOCK:SESSIONS.clear()
            LOGIN_FAILURES.pop(client,None);self.create_session();return {'changed':True}
        if path=='/api/logout':
            self.clear_session()
            with connect() as con:audit(con,'logout','local-admin')
            return {'logged_out':True}
        if path.startswith('/api/social/'):
            action=path[len('/api/social/'):]
            if action=='upload':return social_engine.upload_photo(b.get('name',''),b['data'],b['product'],b['category'],b['format'],b['club_id'])
            if action=='import':return {'imported':social_engine.csv_import(b['type'],b['csv'])}
            if action=='pool':social_engine.add_pool(b['month'],b['items']);return {'ok':True}
            if action=='remove-pool':return social_engine.remove_pool(int(b['id']))
            if action=='remove-post':return social_engine.remove_post(int(b['id']))
            if action=='generate':return social_engine.generate(b['month'],bool(b.get('recalculate',False)))
            if action=='move':return social_engine.move(int(b['post_id']),b['at'])
            raise ValueError('Nieznana operacja DW Social Media.')

        if path=='/api/clubs':return clubs.mutate(sys.modules[__name__],b)
        if path=='/api/save':
            p=copy.deepcopy(b['product']);id=p['id']
            with connect() as con:
                old=get_product(con,id)
                if old['revision']!=p['revision']:raise Conflict('Inna karta zmieniła ten produkt. Twoje wpisy pozostają w formularzu; odśwież dane przed ponownym zapisem.')
                if old.get('imported') or old.get('published_revision') is not None:
                    p['slug']=old['slug'];p['url']=old['url']
                p['source']=old['source'];p['revision']+=1
                errors,warnings=validate(p)
                if errors:raise Validation(errors,warnings)
                collision=safe(BASE,p['url'])
                if p['url']!=old['url'] and collision.exists():raise ValueError('Adres jest zajęty przez istniejącą stronę.')
                if any(urlsplit(c['url']).path==p['url'] for c in settings(con)['categories']):raise ValueError('Adres jest zarezerwowany dla kategorii.')
                con.execute('UPDATE products SET url=?,draft=?,revision=?,updated=? WHERE id=?',(p['url'],dumps(p),p['revision'],now(),id))
                con.execute('INSERT INTO versions(product_id,revision,data,at) VALUES(?,?,?,?)',(id,p['revision'],dumps(p),now()))
                audit(con,'save',id)
                return {'product':get_product(con,id),'warnings':warnings}
        if path=='/api/reload-folder' and FOLDER_MODE:
            import folder_site
            with connect() as con:
                old=get_product(con,b['id'])
                if old['revision']!=b['revision']:raise Conflict('Szkic zmienił się. Wczytaj aktualną wersję.')
                file=safe(SOURCE,old['url'])
                if not file.is_file():raise ValueError('Brak karty w folderze strony.')
                p=import_product(file,copy.deepcopy(settings(con)))
                p.update(id=old['id'],revision=old['revision'],folder_hash=folder_site.digest(file))
            return self.post('/api/save',{'product':p})
        if path=='/api/create':
            with connect() as con:
                if b.get('from'):p=get_product(con,b['from']);p['name']+=' — kopia'
                else:
                    p={'name':'Nowy produkt','description':'','category':'sportswear','specs':{k:'' for k in FIELDS},'original_specs':{},'methods':[],'size':{'mode':'none','columns':['S','M','L'],'rows':[{'name':'Długość','values':['','','']}],'unit':'','tolerance':'','instructions':''},'galleries':{'lifestyle':[],'realizacje':[]},'autoplay':True,'notes':[],'seo_description':'','source':'koszulki-sportowe.html'}
                slug=slugify(p['name']);base=slug;n=2
                while con.execute('SELECT 1 FROM products WHERE url=?',(slug+'.html',)).fetchone() or (BASE/(slug+'.html')).exists():slug=base+'-'+str(n);n+=1
                if not b.get('from'):p['parameters']=[{'name':'','value':''}]
                id=uid();p.pop('folder_hash',None);p.update(id=id,slug=slug,url=slug+'.html',revision=1,published_revision=None,imported=False,archived=False)
                con.execute('INSERT INTO products VALUES(?,?,?,?,?,?)',(id,p['url'],dumps(p),1,None,now()))
                con.execute('INSERT INTO versions(product_id,revision,data,at) VALUES(?,?,?,?)',(id,1,dumps(p),now()))
                audit(con,'create',id);return {'product':get_product(con,id)}
        if path=='/api/preview':
            with connect() as con:
                p=get_product(con,b['id']);catalog=settings(con)
                items=[x for x in published_products(con) if x['id']!=p['id']]+[p]
            token=secrets.token_urlsafe(24);root=DATA/'previews'/token;root.mkdir(parents=True)
            (root/p['url']).write_text(update_navigation(render_product(p,catalog),items,catalog,p['url']),encoding='utf-8')
            return {'url':ADMIN_BASE+'/preview/'+token+'/'+p['url']}
        if path=='/api/order' and FOLDER_MODE:
            import folder_site
            return folder_site.reorder(sys.modules[__name__],b)
        if path=='/api/publish':
            if FOLDER_MODE:
                import folder_site
                return folder_site.publish(sys.modules[__name__],b['id'],b['revision'],'publish',b.get('key',''),
                                           ack_external=b.get('ack_external') is True,
                                           expected_live_hash=b.get('expected_live_hash'))
            return make_release(b['id'],b['revision'],key=b.get('key',''))
        if path=='/api/unpublish':
            if FOLDER_MODE:
                import folder_site
                return folder_site.publish(sys.modules[__name__],b['id'],b['revision'],'unpublish',b.get('key',''),
                                           ack_external=b.get('ack_external') is True,
                                           expected_live_hash=b.get('expected_live_hash'))
            return make_release(b['id'],b['revision'],'unpublish',b.get('key',''))
        if path=='/api/restore':
            with connect() as con:
                old=get_product(con,b['id'])
                if old['revision']!=b['revision']:raise Conflict('Produkt zmienił się od otwarcia historii.')
                row=con.execute('SELECT data FROM versions WHERE product_id=? AND revision=?',(b['id'],b['target'])).fetchone()
                if not row:raise ValueError('Nie znaleziono wersji.')
                p=json.loads(row[0]);p.update(id=b['id'],revision=b['revision'])
            return self.post('/api/save',{'product':p})
        if path=='/api/rollback':
            if FOLDER_MODE:
                import folder_site
                return folder_site.rollback(sys.modules[__name__],b['release'])
            release=b['release']
            with connect() as con:
                row=con.execute('SELECT manifest FROM releases WHERE id=?',(release,)).fetchone()
                if not row:raise ValueError('Brak wydania.')
                manifest=json.loads(row[0]);root=safe(DATA/'releases',release)
                for rel,digest in manifest['files'].items():
                    f=safe(root,rel)
                    if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=digest:raise ValueError('Wydanie jest niekompletne lub uszkodzone.')
                con.execute('UPDATE products SET published_revision=NULL')
                for p in manifest['products']:con.execute('UPDATE products SET published_revision=? WHERE id=?',(p['revision'],p['id']))
                audit(con,'rollback',release);con.commit();atomic(DATA/'current.json',dumps({'release':release}))
            return {'release':release}
        if path=='/api/catalog':
            c=b['catalog']
            with connect() as con:
                old=settings(con)
                if c['revision']!=old['revision']:raise Conflict('Słowniki zmieniły się w innej karcie. Wczytaj je ponownie.')
                ids=[x['id'] for x in c['categories']]
                if len(ids)!=len(set(ids)) or any(not x.get('name','').strip() or not valid_url(x.get('url','')) for x in c['categories']):raise ValueError('Kategorie wymagają unikalnych identyfikatorów, nazw i poprawnych adresów.')
                if any(not re.fullmatch(r'[a-z0-9-]+\.html(?:#[a-z0-9-]+)?',x.get('url','')) for x in c['categories']):raise ValueError('Adres kategorii musi być lokalną stroną .html, opcjonalnie z kotwicą, np. fightwear.html#sportswear.')
                if len({x['url'] for x in c['categories']})!=len(c['categories']):raise ValueError('Adresy kategorii muszą być unikalne.')
                old_urls={x['url'] for x in old['categories']}
                for category in c['categories']:
                    if con.execute('SELECT 1 FROM products WHERE url=?',(urlsplit(category['url']).path,)).fetchone():raise ValueError('Adres kategorii koliduje z produktem.')
                    if category['url'] not in old_urls and safe(BASE,urlsplit(category['url']).path).exists():raise ValueError('Adres nowej kategorii koliduje z istniejącą stroną.')
                for row in con.execute('SELECT draft FROM products'):
                    if json.loads(row[0])['category'] not in ids:raise ValueError('Nie można usunąć kategorii przypisanej do produktu.')
                for m in c['methods']:
                    if not m.get('name','').strip() or not valid_url(m.get('url','')):raise ValueError('Metoda wymaga nazwy i bezpiecznego linku.')
                    if m.get('icon') and not asset_path(m['icon']).is_file():raise ValueError('Nie znaleziono ikony.')
                c['revision']+=1;con.execute('UPDATE settings SET value=? WHERE key="catalog"',(dumps(c),));audit(con,'catalog','all');return {'catalog':c}
        if path=='/api/upload':
            raw=base64.b64decode(b['data'],validate=True);icon=bool(b.get('icon'))
            if len(raw)>(2 if icon else 20)*1024*1024:raise ValueError('Przekroczony limit rozmiaru pliku.')
            if shutil.disk_usage(DATA).free<max(len(raw)*5,100*1024*1024):raise ValueError('Za mało wolnego miejsca na dysku.')
            digest=hashlib.sha256(raw).hexdigest()
            with connect() as con:
                exists=con.execute('SELECT * FROM media WHERE hash=?',(digest,)).fetchone()
                if exists:return dict(exists)
            try:
                with Image.open(io.BytesIO(raw)) as check:
                    fmt=check.format;w,h=check.size
                    if fmt not in ('JPEG','PNG','WEBP') or w*h>40_000_000:raise ValueError('Obsługiwane: JPEG, PNG, WebP; maksymalnie 40 megapikseli.')
                    check.verify()
                im=ImageOps.exif_transpose(Image.open(io.BytesIO(raw)));im.load()
                if im.info.get('icc_profile'):
                    try:im=ImageCms.profileToProfile(im,ImageCms.ImageCmsProfile(io.BytesIO(im.info['icc_profile'])),ImageCms.createProfile('sRGB'),outputMode='RGBA' if 'A' in im.getbands() else 'RGB')
                    except Exception:raise ValueError('Nie można poprawnie przeliczyć profilu kolorów tego zdjęcia.')
                im=im.convert('RGBA' if 'A' in im.getbands() else 'RGB');w,h=im.size
            except (UnidentifiedImageError,OSError,Image.DecompressionBombError) as ex:raise ValueError('Nieprawidłowy lub zbyt duży obraz.') from ex
            id=uid();private=DATA/'originals'/id;private.parent.mkdir(exist_ok=True);private.write_bytes(raw)
            folder=DATA/'media'/id;folder.mkdir(parents=True)
            for bound in (320,640,960,1440,2000):
                variant=im.copy();variant.thumbnail((bound,bound),Image.Resampling.LANCZOS);variant.save(folder/(str(bound)+'.webp'),'WEBP',quality=94,method=4)
            src='media/'+id+'/2000.webp'
            item={'id':id,'src':src,'name':str(b.get('name','zdjęcie'))[:200],'width':w,'height':h,'bytes':len(raw),'original':id,'hash':digest,'usage':[]}
            with connect() as con:
                con.execute('INSERT INTO media VALUES(?,?,?,?,?,?,?,?)',tuple(item[k] for k in ('id','src','name','width','height','bytes','original','hash')));audit(con,'upload',id)
            return item
        if path=='/api/backup':return backup()
        if path=='/api/shutdown':
            threading.Timer(.4,self.server.shutdown).start()
            return {'stopped':True}
        raise ValueError('Nieznana operacja.')

def run():
    initialize()
    social_engine.init()
    clubs.initialize(sys.modules[__name__])
    try:server=ThreadingHTTPServer((BIND,PORT),Handler)
    except OSError:
        import urllib.request
        try:
            health=json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/health',timeout=2))
            if health.get('app')=='DangerWearManager':
                if '--open' in sys.argv:webbrowser.open(f'http://127.0.0.1:{PORT}{ADMIN_BASE}/')
                return
        except Exception:pass
        raise RuntimeError(f'Port {PORT} jest zajęty. Zmień port w config.json.')
    print(f'Strona: http://127.0.0.1:{PORT}/ | Panel: http://127.0.0.1:{PORT}{ADMIN_BASE}/',flush=True)
    atomic(DATA/'local-control.json',dumps({'stop_token':STOP_TOKEN,'port':PORT,'admin_path':ADMIN_BASE}))
    print('Zamknięcie tego okna zatrzymuje program. Dane pozostają zapisane.',flush=True)
    if '--open' in sys.argv:threading.Timer(.6,lambda:webbrowser.open(f'http://127.0.0.1:{PORT}{ADMIN_BASE}/')).start()
    try:server.serve_forever()
    except KeyboardInterrupt:server.shutdown()
if __name__=='__main__':run()
