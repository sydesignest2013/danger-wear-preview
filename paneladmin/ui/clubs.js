'use strict';
let clubState=null;
const clubOrder=(a,b)=>a.name.localeCompare(b.name,'pl',{sensitivity:'base'});
async function clubRefresh(){clubState=await api('clubs');return clubState;}
async function clubWrite(change){clubState=await api('clubs',{revision:clubState.revision,...change});return clubState;}
function clubPicker(value,onchange){
 const label=document.createElement('label');label.textContent='Klub (puste = zdjęcie neutralne)';
 const input=document.createElement('input'),list=document.createElement('datalist'),key='clubs-'+crypto.randomUUID();
 input.setAttribute('list',key);input.placeholder='Wyszukaj klub…';input.autocomplete='off';list.id=key;
 const rows=[...(clubState?.clubs||[])].sort(clubOrder);input.value=rows.find(c=>c.id===value)?.name||'';
 for(const c of rows){const option=document.createElement('option');option.value=c.name;option.label=c.id;list.append(option);}
 input.onchange=guard(async()=>{const c=rows.find(c=>c.name===input.value);if(input.value&&!c){input.setCustomValidity('Wybierz istniejący klub z listy.');input.reportValidity();return;}input.setCustomValidity('');await onchange(c?.id||null);});
 label.append(input,list);return label;
}
async function renderClubs(){
 await clubRefresh();
 content.innerHTML='<div class="toolbar"><input id="clubSearch" placeholder="Szukaj klubu…" aria-label="Szukaj klubu"><select id="clubSort" aria-label="Sortowanie klubów"><option value="az">A–Z</option><option value="most">Najwięcej zdjęć</option><option value="least">Najmniej zdjęć</option><option value="stars">⭐ Promowane</option></select><button id="clubAdd" class="primary">＋ Dodaj klub</button></div><div class="club-legend"><span class="count-lifestyle">Lifestyle</span> · <span class="count-realizacje">Realizacje</span> · <span class="count-methods">Metody znakowania</span></div><div id="clubList"></div>';
 function draw(){
  const q=$('#clubSearch').value.toLocaleLowerCase('pl'),sort=$('#clubSort').value,total=c=>Object.values(c.counts).reduce((a,b)=>a+b,0);
  const rows=clubState.clubs.filter(c=>(c.name+' '+c.id).toLocaleLowerCase('pl').includes(q)).sort((a,b)=>(sort==='most'?total(b)-total(a):sort==='least'?total(a)-total(b):sort==='stars'?b.promoted-a.promoted:0)||clubOrder(a,b));
  $('#clubList').innerHTML=rows.map(c=>`<div class="club-row"><button class="club-name" data-club="${esc(c.id)}">${esc(c.name)}</button><span class="club-counts">${Object.entries(c.counts).filter(([,n])=>n).map(([kind,n])=>`<button class="count-${kind}" data-photos="${esc(c.id)}" data-kind="${kind}" aria-label="${esc(c.name)}: ${n} zdjęć ${kind}">${n}</button>`).join('')}</span><button class="club-star ${c.promoted?'promoted':''}" data-star="${esc(c.id)}" aria-label="Promowanie ${esc(c.name)}" aria-pressed="${!!c.promoted}">${c.promoted?'★':'☆'}</button></div>`).join('')||'<p class="empty">Brak klubów.</p>';
  $$('[data-club]').forEach(b=>b.onclick=guard(()=>clubDetail(b.dataset.club)));
  $$('[data-photos]').forEach(b=>b.onclick=guard(()=>clubPhotos(b.dataset.photos,b.dataset.kind)));
  $$('[data-star]').forEach(b=>b.onclick=guard(async()=>{const c=clubState.clubs.find(c=>c.id===b.dataset.star);await clubWrite({action:'edit',...c,promoted:!c.promoted});draw();}));
 }
 $('#clubSearch').oninput=draw;$('#clubSort').onchange=draw;
 $('#clubAdd').onclick=()=>{showModal('Dodaj klub','<label>Nazwa klubu<input id="newClubName" maxlength="120"></label><div class="modal-footer"><button id="saveNewClub" class="primary">Dodaj klub</button></div>');$('#saveNewClub').onclick=guard(async()=>{await clubWrite({action:'create',name:$('#newClubName').value});modal.close();draw();});};draw();
}
async function clubDetail(id){
 await clubRefresh();const c=clubState.clubs.find(c=>c.id===id),rivals=new Set(clubState.rivalries.filter(p=>p.includes(id)).flat().filter(x=>x!==id));
 content.innerHTML=`<button id="clubBack" class="back">← Wszystkie kluby</button><section class="section"><h2>${esc(c.name)}</h2><p>Stały identyfikator: <code>${esc(id)}</code></p><label>Nazwa<input id="clubName" value="${esc(c.name)}" maxlength="120"></label><label class="check"><input id="clubPromoted" type="checkbox" ${c.promoted?'checked':''}> Promowany klub ⭐</label><label>Bonus do wagi losowania (%)<input id="clubBonus" type="number" min="0" max="20" step="0.1" value="${+(c.bonus*100).toFixed(2)}"></label><p class="hint">5% oznacza wagę 1,05. Promocja nie omija kos.</p><button id="clubSave" class="primary">Zapisz klub</button></section><section class="section"><h3>Kosy (${rivals.size})</h3><div id="rivalPicker"></div><button id="rivalAdd">＋ Dodaj kosę</button><div>${clubState.clubs.filter(c=>rivals.has(c.id)).sort(clubOrder).map(c=>`<div class="club-row"><span>${esc(c.name)}</span><button data-unrival="${esc(c.id)}">− Usuń kosę</button></div>`).join('')||'<p class="hint">Brak zapisanych kos.</p>'}</div></section><section class="section"><h3>Historia zmian</h3><div class="club-history">${clubState.history.filter(e=>e.detail.includes(id)).map(e=>`<p><time>${esc(new Date(e.at).toLocaleString('pl'))}</time> · ${esc(e.event)}<br><small>${esc(e.detail)}</small></p>`).join('')||'<p>Brak indywidualnych zmian.</p>'}</div></section>`;
 $('#clubBack').onclick=guard(renderClubs);let other=null;$('#rivalPicker').append(clubPicker(null,v=>{other=v;}));
 $('#rivalAdd').onclick=guard(async()=>{if(!other)throw new Error('Wybierz klub.');await clubWrite({action:'rivalry',a:id,b:other,enabled:true});await clubDetail(id);});
 $$('[data-unrival]').forEach(b=>b.onclick=guard(async()=>{await clubWrite({action:'rivalry',a:id,b:b.dataset.unrival,enabled:false});await clubDetail(id);}));
 $('#clubSave').onclick=guard(async()=>{await clubWrite({action:'edit',id,name:$('#clubName').value,promoted:$('#clubPromoted').checked,bonus:Number($('#clubBonus').value)/100});toast('Klub zapisany. Galerie korzystają z aktualnych zasad.');await clubDetail(id);});
}
async function clubPhotos(id,kind){
 await clubRefresh();const c=clubState.clubs.find(c=>c.id===id),items=clubState.photos.filter(p=>p.club_id===id&&p.category===kind);
 content.innerHTML=`<button id="photosBack" class="back">← Kluby</button><h2>${esc(c.name)} · ${esc(kind)}</h2><div class="media-grid">${items.map((p,i)=>`<article class="media-card"><img src="${window.DW_BASE}/asset/${esc(p.src)}" alt="${esc(p.alt)}"><small>${esc(p.product||p.method)}</small><button data-photo-edit="${i}">Edytuj zdjęcia</button><div data-photo-picker="${i}"></div></article>`).join('')}</div>`;
 $('#photosBack').onclick=guard(renderClubs);
 $$('[data-photo-edit]').forEach(b=>b.onclick=guard(async()=>{const p=items[+b.dataset.photoEdit];if(p.product_id){await reload();openEditor(p.product_id);document.getElementById(kind+'Gallery')?.scrollIntoView();}else await renderMethodPhotos(p.method);}));
 $$('[data-photo-picker]').forEach(el=>{const p=items[+el.dataset.photoPicker];el.append(clubPicker(p.club_id,async club_id=>{await clubWrite({action:'assign',src:p.src,club_id});await clubPhotos(id,kind);}));});
}
async function renderMethodPhotos(selected='sublimacja'){
 await clubRefresh();content.innerHTML=`<div class="toolbar"><label>Metoda<select id="photoMethod">${Object.entries(clubState.methods).map(([id,name])=>`<option value="${id}" ${id===selected?'selected':''}>${esc(name.replaceAll('_',' '))}</option>`).join('')}</select></label><button id="methodUpload" class="primary">＋ Wgraj zdjęcia</button><button id="methodLibrary">Wybierz z biblioteki</button></div><p class="hint">Klub wybierzesz przy każdym zdjęciu. Zapis działa od następnego załadowania strony. Usunięcie z metody zachowuje plik.</p><div class="media-grid" id="methodPhotoGrid"></div>`;
 const rows=clubState.photos.filter(p=>p.category==='methods'&&p.method===selected);
 $('#methodPhotoGrid').innerHTML=rows.map((p,i)=>`<article class="media-card"><img src="${window.DW_BASE}/asset/${esc(p.src)}" alt="${esc(p.alt)}"><div data-method-picker="${i}"></div><button data-method-remove="${p.photo_id}">Usuń z metody</button></article>`).join('');
 $$('[data-method-picker]').forEach(el=>{const p=rows[+el.dataset.methodPicker];el.append(clubPicker(p.club_id,club_id=>clubWrite({action:'assign',src:p.src,club_id})));});
 $$('[data-method-remove]').forEach(b=>b.onclick=guard(async()=>{await clubWrite({action:'method_remove',photo_id:+b.dataset.methodRemove});await renderMethodPhotos(selected);}));
 $('#photoMethod').onchange=guard(e=>renderMethodPhotos(e.target.value));
 const add=items=>guard(async()=>{for(const p of items)await clubWrite({action:'method_add',method:selected,src:p.src,alt:'',club_id:null});await renderMethodPhotos(selected);})();
 $('#methodUpload').onclick=()=>chooseUpload(50,add);$('#methodLibrary').onclick=guard(()=>pickMedia(50,add));
}
// Extend the existing photo editor without replacing its upload or publication flow.
const originalRenderGallery=renderGallery;
renderGallery=function(kind){originalRenderGallery(kind);const current=product;
 guard(async()=>{await clubRefresh();if(product!==current)return;const root=$('#'+kind+'Gallery');if(!root)return;$$('.gallery-item',root).forEach(el=>{el.querySelector('label:has(datalist)')?.remove();const p=current.galleries[kind][+el.dataset.index];const owner=clubState.photos.find(x=>x.src===p.src)?.club_id||p.club_id||null;el.querySelector('.row-actions').before(clubPicker(owner,async club_id=>{await clubWrite({action:'assign',src:p.src,club_id});p.club_id=club_id;toast('Przypisanie klubu zapisane.');}));});})();
};
