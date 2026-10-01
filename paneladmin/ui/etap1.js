'use strict';
// Presentation layer; existing product fields and save handlers remain intact.
let productView='tiles';try{productView=localStorage.getItem('dw-product-view')||'tiles'}catch{}
const originalRenderProducts=renderProducts;
renderProducts=function(){
 originalRenderProducts();
 const toolbar=$('.toolbar',content),cards=$('#cards');
 const switcher=document.createElement('div');switcher.className='view-switch';switcher.setAttribute('aria-label','Widok produktów');
 switcher.innerHTML='<button type="button" data-view="tiles">Kafelki</button><button type="button" data-view="list">Lista</button>';
 toolbar.append(switcher);
 const saveOrder=document.createElement('button');saveOrder.className='primary';saveOrder.textContent='Zapisz kolejność na stronie';saveOrder.hidden=true;toolbar.after(saveOrder);
 let pending=null,dragged=null;
 function decorate(){
  const category=$('#categoryFilter').value;
  const ordering=pending?pending.map(id=>state.products.find(p=>p.id===id).url):(state.catalog.product_order?.[category]||[]);
  const all=state.products.filter(p=>p.category===category).sort((a,b)=>{
   const ai=ordering.indexOf(a.url),bi=ordering.indexOf(b.url);return (ai<0?9999:ai)-(bi<0?9999:bi);
  });
  const rank=new Map(all.map((p,i)=>[p.id,i]));
  const rows=$$('.product-card',cards).sort((a,b)=>(rank.get(a.dataset.id)??9999)-(rank.get(b.dataset.id)??9999));
  rows.forEach(row=>cards.append(row));
  cards.classList.toggle('products-list',productView==='list');
  $$('[data-view]',switcher).forEach(b=>{b.classList.toggle('selected',b.dataset.view===productView);b.setAttribute('aria-pressed',String(b.dataset.view===productView))});
  const canSort=productView==='list'&&category&&!$('#search').value&&!$('#statusFilter').value;
  rows.forEach((row,i)=>{
   row.querySelector('.order-controls')?.remove();
   row.querySelector('.list-status')?.remove();
   if(productView!=='list')return;
   const p=state.products.find(p=>p.id===row.dataset.id);
   const status=document.createElement('span');status.className='list-status';status.textContent=p.revision===p.published_revision?'Opublikowano':'Szkic / zmiany';row.querySelector('.card-copy').append(status);
   const controls=document.createElement('div');controls.className='order-controls';
   controls.innerHTML=`<button class="drag-handle" type="button" aria-label="Przeciągnij produkt ${esc(p.name)}" ${canSort?'':'disabled'}>⠿</button><span>${category?String(i+1).padStart(2,'0'):'—'}</span><button type="button" data-step="-1" aria-label="Przesuń w górę" ${canSort&&i>0?'':'disabled'}>↑</button><button type="button" data-step="1" aria-label="Przesuń w dół" ${canSort&&i<rows.length-1?'':'disabled'}>↓</button>`;
   controls.onclick=e=>e.stopPropagation();controls.onkeydown=e=>e.stopPropagation();row.prepend(controls);
   const handle=$('.drag-handle',controls);handle.draggable=!!canSort;
   handle.ondragstart=e=>{dragged=row;e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',row.dataset.id);row.classList.add('dragging')};
   handle.ondragend=()=>{row.classList.remove('dragging');dragged=null};
   row.ondragover=e=>{if(dragged&&canSort){e.preventDefault();e.dataTransfer.dropEffect='move'}};
   row.ondrop=e=>{e.preventDefault();if(!dragged||dragged===row||!canSort)return;const after=e.clientY>row.getBoundingClientRect().top+row.offsetHeight/2;cards.insertBefore(dragged,after?row.nextSibling:row);changedOrder()};
   $$('[data-step]',controls).forEach(b=>b.onclick=e=>{e.stopPropagation();const list=$$('.product-card',cards),n=list.indexOf(row),other=list[n+Number(b.dataset.step)];if(other){cards.insertBefore(row,Number(b.dataset.step)>0?other.nextSibling:other);changedOrder()}});
  });
  switcher.title=category?'':'Wybierz kategorię i widok Lista, aby ustawić kolejność.';
 }
 function changedOrder(){pending=$$('.product-card',cards).map(r=>r.dataset.id);const category=$('#categoryFilter').value;for(const id of ['search','categoryFilter','statusFilter'])$('#'+id).disabled=true;saveOrder.hidden=false;dirty=true;decorate()}
 saveOrder.onclick=guard(async()=>{saveOrder.disabled=true;try{const r=await api('order',{category:$('#categoryFilter').value,ids:pending,revision:state.catalog.revision});state.catalog=r.catalog;dirty=false;pending=null;saveOrder.hidden=true;for(const id of ['search','categoryFilter','statusFilter'])$('#'+id).disabled=false;toast('Kolejność zapisana w panelu i plikach strony.')}finally{saveOrder.disabled=false}});
 for(const id of ['search','categoryFilter','statusFilter']){const el=$('#'+id),prop=id==='search'?'oninput':'onchange',original=el[prop];el[prop]=e=>{if(pending){const proceed=confirm('Masz niezapisaną kolejność. Odrzucić ją i zmienić filtr?');if(!proceed){renderProducts();return}pending=null;dirty=false;saveOrder.hidden=true}original(e);decorate()}}
 $$('[data-view]',switcher).forEach(b=>b.onclick=()=>{productView=b.dataset.view;try{localStorage.setItem('dw-product-view',productView)}catch{}decorate()});
 decorate();
};

const helpPopup=document.createElement('div');helpPopup.className='help-popup';helpPopup.id='dw-help';helpPopup.setAttribute('role','tooltip');helpPopup.hidden=true;document.body.append(helpPopup);
function compactHints(){
 $$('.hint',content).forEach(h=>{
  if(h.querySelector('input,button,a,select')||!h.textContent.trim())return;
  const message=h.textContent.trim();
  const b=document.createElement('button');b.type='button';b.className='help-dot';b.textContent='i';b.setAttribute('aria-label','Informacja: '+message);b.setAttribute('aria-describedby','dw-help');
  const show=()=>{helpPopup.textContent=message;helpPopup.hidden=false;const r=b.getBoundingClientRect();helpPopup.style.left=Math.max(8,Math.min(r.left,innerWidth-330))+'px';helpPopup.style.top=Math.min(r.bottom+8,innerHeight-helpPopup.offsetHeight-8)+'px'};
  const hide=()=>helpPopup.hidden=true;
  b.onmouseenter=show;b.onfocus=show;b.onmouseleave=hide;b.onblur=hide;b.onclick=e=>{e.preventDefault();e.stopPropagation();show()};b.onkeydown=e=>{if(e.key==='Escape')hide()};
  const label=h.closest('label');if(label)label.insertBefore(b,label.querySelector('input,select,textarea'));else {const title=h.closest('.section')?.querySelector('.section-title h3');if(title)title.append(b);else h.before(b)}h.remove();
 });
}
new MutationObserver(compactHints).observe(content,{childList:true,subtree:true});
document.addEventListener('keydown',e=>{if(e.key==='Escape')helpPopup.hidden=true});
window.addEventListener('scroll',()=>helpPopup.hidden=true,true);
compactHints();
