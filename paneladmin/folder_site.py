"""Publish selected product into the surrounding website, with reversible file writes."""
import copy, hashlib, json, os, re, shutil, time
from pathlib import Path

PUBLIC_DIRS={'assets','css','js','products','images','fonts','lifestyle','realizacje','media','produkcja','en','de','fr'}

def public_file(root,path):
    rel=path.resolve().relative_to(root.resolve())
    return len(rel.parts)==1 or rel.parts[0].lower() in PUBLIC_DIRS

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def editor_product(a,p,con):
    path=a.safe(a.SOURCE,p['url'])
    if p['revision']==1 and p.get('imported') and path.is_file():
        actual=a.import_product(path,copy.deepcopy(a.settings(con)))
        actual.update({k:p[k] for k in ('id','revision','published_revision','updated')})
        p=actual
    p.setdefault('folder_hash',digest(path))
    return p

def live_products(a,con):
    catalog=copy.deepcopy(a.settings(con));items=[]
    known={r['url']:r for r in con.execute('SELECT id,url,published_revision FROM products')}
    for path in sorted(a.SOURCE.glob('*.html')):
        raw=path.read_text('utf-8-sig')
        if 'window.DW_GALLERIES' not in raw or 'fw-info' not in raw:continue
        p=a.import_product(path,catalog);row=known.get(path.name)
        p.update(id=row['id'] if row else path.stem,revision=(row['published_revision'] or 1) if row else 1)
        items.append(p)
    return items

def write_bytes(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.panel-tmp')
    try:
        tmp.write_bytes(data);os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()

def apply_files(a,root,changes,before,expected):
    """Check all targets first; keep a journal and restore on a write failure."""
    for rel in changes:
        dest=a.safe(a.SOURCE,rel)
        if not public_file(a.SOURCE,dest):raise ValueError('Zapis poza plikami strony jest zablokowany.')
        if digest(dest)!=expected[rel]:raise a.Conflict('Plik zmienił się podczas publikacji: '+rel)
    before.mkdir(parents=True,exist_ok=True)
    for rel in changes:
        dest=a.safe(a.SOURCE,rel)
        if dest.is_file():
            old=a.safe(before,rel);old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,old)
    journal=before.parent/'transaction.json'
    a.atomic(journal,a.dumps({'status':'writing','files':list(changes),'before':expected}))
    written=[]
    try:
        for rel in changes:
            dest=a.safe(a.SOURCE,rel)
            if digest(dest)!=expected[rel]:raise a.Conflict('Plik zmienił się podczas zapisu: '+rel)
            written.append(rel)
            if changes[rel] is None:
                if dest.exists():dest.unlink()
            else:write_bytes(dest,a.safe(root,rel).read_bytes())
        a.atomic(journal,a.dumps({'status':'complete','files':list(changes),'before':expected}))
    except Exception:
        for rel in reversed(written):
            dest=a.safe(a.SOURCE,rel);old=a.safe(before,rel)
            if old.is_file():write_bytes(dest,old.read_bytes())
            elif dest.exists():dest.unlink()
        a.atomic(journal,a.dumps({'status':'reverted','files':list(changes),'before':expected}))
        raise

def publication_check(a, product_id):
    """Read-only check. Describe drift and club-related layout constraints before publishing."""
    with a.LOCK, a.connect() as con:
        p=a.get_product(con, product_id)
        path=a.safe(a.SOURCE, p['url'])
        current_hash=digest(path)
        previous_hash=p.get('folder_hash')
        drift=current_hash!=previous_hash
        current_differences=[]
        if drift and path.is_file():
            try:
                live=a.import_product(path,copy.deepcopy(a.settings(con)))
                for key,label in [('name','Nazwa'),('description','Opis'),('category','Kategoria'),
                                  ('specs','Parametry'),('size','Tabela rozmiarów'),
                                  ('methods','Metody znakowania'),('galleries','Galerie zdjęć')]:
                    if p.get(key)!=live.get(key):
                        current_differences.append(label)
            except (ValueError,KeyError) as exc:
                current_differences.append('Nie można porównać bieżącej karty: '+str(exc))
        clubs={row['id']:row['name'] for row in con.execute('SELECT id,name FROM dw_clubs')}
        rivals={tuple(sorted((r['a'],r['b']))) for r in con.execute('SELECT a,b FROM dw_rivalries')}
        owners=a.clubs.bindings(con)
        layout=[];unassigned=0
        def club(item):
            return owners.get(item.get('src')) or item.get('club_id')
        galleries=p.get('galleries',{})
        for kind in ('lifestyle','realizacje'):
            gallery=galleries.get(kind,[])
            for item in gallery:
                if not club(item):unassigned+=1
            # Lifestyle: the engine cannot put rival clubs into the SAME carousel.
            # Realizacje: rivals may coexist, but must never be adjacent.
            pairs=((i,j) for i in range(len(gallery)) for j in range(i+1,len(gallery))) if kind=='lifestyle' else ((i,i+1) for i in range(len(gallery)-1))
            seen=set()
            for i,j in pairs:
                x,y=club(gallery[i]),club(gallery[j])
                if not x or not y or x==y or tuple(sorted((x,y))) not in rivals:continue
                marker=(kind,tuple(sorted((x,y))))
                if marker in seen:continue
                seen.add(marker)
                if kind=='lifestyle':
                    layout.append('Lifestyle: '+clubs.get(x,x)+' i '+clubs.get(y,y)+' nie mogą być razem w jednej karuzeli. Silnik musi odrzucić jedną z fotografii w tym zestawie.')
                else:
                    layout.append('Realizacje: '+clubs.get(x,x)+' i '+clubs.get(y,y)+' sąsiadują w kolejności szkicu. Galeria musi rozdzielić je zdjęciem neutralnego klubu albo pominąć jedną fotografię.')
        return {'id':product_id,'url':p['url'],'revision':p['revision'],
                'external_changed':drift,'current_hash':current_hash,
                'stored_hash':previous_hash,'current_differences':current_differences,
                'club_notices':layout,'unassigned_count':unassigned}

def publish(a,id,expected_revision,action,key,ack_external=False,expected_live_hash=None):
    with a.PUBLISH_LOCK,a.LOCK,a.connect() as con:
        if key:
            old=con.execute('SELECT id FROM releases WHERE status=?',('key:'+key,)).fetchone()
            if old:return {'release':old[0],'url':'/','reused':True}
        p=a.get_product(con,id)
        if p['revision']!=expected_revision:raise a.Conflict('Produkt zmienił się. Wczytaj aktualną wersję.')
        live_hash=digest(a.safe(a.SOURCE,p['url']))
        changed_externally=live_hash!=p.get('folder_hash')
        if changed_externally:
            if not ack_external:
                raise a.Conflict('Karta zmieniła się poza panelem. Najpierw wyświetl raport synchronizacji, a następnie świadomie zatwierdź zapis.')
            if expected_live_hash!=live_hash:
                raise a.Conflict('Plik zmienił się już PO wyświetleniu raportu. Odśwież raport synchronizacji i ponów zapis; nic nie nadpisano.')
        # Differences detected before a publish do not trigger a blind reset of the draft.
        # The CURRENT HTML remains the rendering template; the explicitly approved draft
        # overrides editable product fields. All other live template changes are preserved.
        errors,warnings=a.validate(p,True)
        if action=='publish' and errors:raise a.Validation(errors,warnings)
        catalog=a.settings(con)
        live_items=live_products(a,con)
        old_live=next((x for x in live_items if x['id']==id),None)
        # Content/photo-only edits must not rewrite unrelated root HTML files.
        navigation_changed=(action!='publish' or old_live is None or
                            any(old_live.get(field)!=p.get(field) for field in ('name','category','url')))
        items=[x for x in live_items if x['id']!=id]
        release=time.strftime('%Y%m%d-%H%M%S')+'-'+a.uid()[:8]
        folder=a.DATA/'releases'/release;root=folder/'files';root.mkdir(parents=True)
        changes={};hashes={}
        def stage(rel,data):
            original=a.safe(a.SOURCE,rel)
            if original.is_file() and original.read_bytes()==data:
                return  # untouched pages must not be rewritten
            dest=a.safe(root,rel);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
            changes[rel]=digest(dest);hashes.setdefault(rel,digest(original))
        if action=='publish':
            p=copy.deepcopy(p)
            # Keep the existing product folder, even where its name differs from the HTML slug.
            folders=[Path(x['src']).parts[1] for g in p['galleries'].values() for x in g if re.match(r'^products/[^/]+/(lifestyle|realizacje)/',x.get('src',''))]
            live=a.safe(a.SOURCE,p['url'])
            if live.is_file():
                original=a.read_gallery(live.read_text('utf-8-sig'))
                folders=[Path(x['src']).parts[1] for g in original.values() for x in g if re.match(r'^products/[^/]+/(lifestyle|realizacje)/',x.get('src',''))]+folders
            product_folder=folders[0] if folders else p['slug']
            for kind,gallery in p['galleries'].items():
                for n,item in enumerate(gallery,1):
                    src=a.asset_path(item['src']);data=src.read_bytes()
                    name=a.slugify(item.get('title') or src.stem)[:65]
                    rel=f'products/{product_folder}/{kind}/{n:02d}-{name}-{hashlib.sha256(data).hexdigest()[:8]}{src.suffix.lower()}'
                    a.clubs.copy_binding(con,item['src'],rel)
                    stage(rel,data);item['src']=rel
            for method in p.get('methods',[]):
                if method.get('icon','').startswith('media/'):
                    source=a.asset_path(method['icon']);rel='assets/images/metody-znakowania/'+digest(source)[:16]+source.suffix
                    stage(rel,source.read_bytes());method['icon']=rel
            stage('js/dw-gallery.js',(a.APP/'ui'/'gallery.js').read_bytes())
            stage(p['url'],a.render_product(p,catalog).encode('utf-8'));items.append(p)
        else:changes[p['url']]=None;hashes[p['url']]=digest(a.safe(a.SOURCE,p['url']))
        for category in catalog['categories']:
            from urllib.parse import urlsplit
            rel=urlsplit(category['url']).path
            if any(x['category']==category['id'] for x in items) and not a.safe(a.SOURCE,rel).exists():
                doc=a.html.fromstring((a.SOURCE/'streetwear.html').read_text('utf-8-sig'))
                for node in doc.xpath('//title|//h1'):a.set_text(node,category['name'])
                stage(rel,a.update_navigation(a.html.tostring(doc,encoding='unicode'),items,catalog,rel).encode('utf-8'))
        # Navigation uses actual live cards, never the stale drafts of other products.
        for path in a.SOURCE.glob('*.html'):
            if not navigation_changed and path.name!=p['url']:continue
            if action!='publish' and path.name==p['url']:continue
            hashes.setdefault(path.name,digest(path))
            staged=root/path.name;raw=(staged if staged.is_file() else path).read_text('utf-8-sig')
            stage(path.name,a.update_navigation(raw,items,catalog,path.name).encode('utf-8'))
        if action=='publish' and not (a.SOURCE/p['url']).exists():
            stage(p['url'],a.update_navigation((root/p['url']).read_text('utf-8'),items,catalog,p['url']).encode('utf-8'))
        stage('js/dw-clubs-data.json',a.dumps(a.clubs.payload(con)).encode('utf-8'))
        apply_files(a,root,changes,folder/'before',hashes)
        manifest={'id':release,'at':a.now(),'folder_mode':True,'products':items,'files':changes,'before':hashes,'target':id,'action':action}
        a.atomic(folder/'release.json',a.dumps(manifest))
        con.execute('INSERT INTO releases VALUES(?,?,?,?)',(release,a.now(),a.dumps(manifest),'key:'+key if key else 'ready'))
        if changed_externally:
            a.audit(con,'external_sync_approved',id,a.dumps({'before_hash':p.get('folder_hash'),'approved_live_hash':live_hash,'release':release}))
        # Persist published folder paths so future edits keep the same product directory.
        p['folder_hash']=digest(a.safe(a.SOURCE,p['url']))
        con.execute('UPDATE products SET draft=?,published_revision=? WHERE id=?',(a.dumps(p),p['revision'] if action=='publish' else None,id))
        a.audit(con,action,id,release);con.commit()
        a.atomic(a.DATA/'current.json',a.dumps({'release':release}))
        return {'release':release,'url':'/'+p['url'] if action=='publish' else '/','warnings':warnings,'external_sync':changed_externally}

def rollback(a,release):
    with a.PUBLISH_LOCK,a.LOCK,a.connect() as con:
        if a.current()!=release:raise ValueError('Cofanie w folderze jest dostępne dla ostatniej publikacji.')
        row=con.execute('SELECT manifest FROM releases WHERE id=?',(release,)).fetchone()
        if not row:raise ValueError('Brak publikacji.')
        m=json.loads(row[0])
        if not m.get('folder_mode'):raise ValueError('To wydanie pochodzi ze starego trybu kopii strony.')
        folder=a.DATA/'releases'/release
        for rel,h in m['before'].items():
            if h is not None and digest(a.safe(folder/'before',rel))!=h:raise ValueError('Kopia pliku jest uszkodzona: '+rel)
        rollback_id='undo-'+a.uid()[:8]
        apply_files(a,folder/'before',m['before'],a.DATA/'releases'/rollback_id/'before',m['files'])
        a.audit(con,'rollback',release)
        if m.get('before_catalog'):
            restored=m['before_catalog'];restored['revision']=a.settings(con)['revision']+1
            con.execute('UPDATE settings SET value=? WHERE key="catalog"',(a.dumps(restored),))
        con.execute('UPDATE products SET published_revision=NULL WHERE id=?',(m['target'],))
        con.commit();a.atomic(a.DATA/'current.json',a.dumps({'release':'source'}))
        return {'release':'source'}

def reorder(a,b):
    with a.PUBLISH_LOCK,a.LOCK,a.connect() as con:
        old=a.settings(con)
        if b.get('revision')!=old['revision']:raise a.Conflict('Kolejność lub słowniki zmieniły się. Odśwież listę.')
        category=b.get('category');ids=b.get('ids')
        products=[a.get_product(con,r[0]) for r in con.execute('SELECT id FROM products')]
        group={p['id']:p for p in products if p['category']==category}
        if not group or not isinstance(ids,list) or len(ids)!=len(set(ids)) or set(ids)!=set(group):raise ValueError('Kolejność musi zawierać wszystkie produkty wybranej kategorii dokładnie raz.')
        catalog=copy.deepcopy(old);catalog.setdefault('product_order',{})[category]=[group[id]['url'] for id in ids];catalog['revision']+=1
        items=live_products(a,con);release=time.strftime('%Y%m%d-%H%M%S')+'-order-'+a.uid()[:8]
        folder=a.DATA/'releases'/release;root=folder/'files';root.mkdir(parents=True)
        changes={};before={}
        for path in a.SOURCE.glob('*.html'):
            before[path.name]=digest(path)
            content=a.update_navigation(path.read_text('utf-8-sig'),items,catalog,path.name)
            (root/path.name).write_text(content,'utf-8');changes[path.name]=digest(root/path.name)
        apply_files(a,root,changes,folder/'before',before)
        manifest={'id':release,'at':a.now(),'folder_mode':True,'products':items,'files':changes,'before':before,'before_catalog':old,'target':'order','action':'order'}
        a.atomic(folder/'release.json',a.dumps(manifest))
        con.execute('UPDATE settings SET value=? WHERE key="catalog"',(a.dumps(catalog),))
        con.execute('INSERT INTO releases VALUES(?,?,?,?)',(release,a.now(),a.dumps(manifest),'ready'))
        a.audit(con,'order',category,release);con.commit()
        a.atomic(a.DATA/'current.json',a.dumps({'release':release}))
        return {'catalog':catalog,'release':release}
