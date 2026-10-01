(async()=>{
 const base=new URL('.',document.currentScript.src);
 try {
  const {load}=await import(new URL('dw-clubs-engine.js',base));const rules=await load(base);
  const source=window.DW_GALLERIES||{};
  window.DW_GALLERIES={...source,lifestyle:rules.lifestyle(source.lifestyle,5),realizacje:rules.realizacje(source.realizacje,18)};
 } catch(error) {window.DW_GALLERIES={lifestyle:[],realizacje:[]};console.warn('Danger Wear: dobór zdjęć niedostępny.',error);}
/* Local manager gallery adapter. Original source scripts remain untouched. */
(()=>{
 const g=window.DW_GALLERIES||{},life=g.lifestyle||[],real=g.realizacje||[],by=id=>document.getElementById(id);
 const hero=by('lifestyleHero'),stage=by('lifestyleStage'),title=by('lifestyleTitle'),sub=by('lifestyleSubtitle');
 const controls=['lifestylePrev','lifestyleNext','carouselArrowPrev','carouselArrowNext'];
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');let index=0,timer=null,busy=false,hover=false,focused=false;
 const wrap=(n,len)=>(n+len)%len;
 // Keep the very same 3-layer caption in cards published by the local manager.
 const caption=title?.closest('.mesh-ref-caption,.mesh-carousel-caption-below');
 let outline=null;
 if(caption&&title&&sub&&!caption.classList.contains('dw-kinetic-caption')){
  const group=title.parentElement,headline=document.createElement('div');headline.className='dw-caption-headline';
  outline=document.createElement('span');outline.className='dw-caption-outline';outline.setAttribute('aria-hidden','true');
  title.before(headline);headline.append(outline,title);
  const subline=document.createElement('div');subline.className='dw-caption-subline';subline.append(sub);group.append(subline);
  caption.classList.add('dw-kinetic-caption');
 }
 function showCaption(active){
  if(!caption)return;
  if(outline)outline.textContent=title.textContent.trim();
  caption.classList.toggle('dw-has-lifestyle',!!active);
  caption.classList.toggle('dw-has-subtitle',!!active&&!!sub?.textContent.trim());
  caption.classList.toggle('dw-long-team',title.textContent.trim().length>19);
  caption.classList.remove('dw-caption-exiting');
  if(!active||reduced.matches){caption.classList.remove('dw-caption-revealing','dw-caption-revealed');return}
  caption.classList.remove('dw-caption-revealed');caption.classList.add('dw-caption-revealing');
  void caption.offsetWidth;requestAnimationFrame(()=>caption.classList.add('dw-caption-revealed'));
 }

 function render(){
  controls.forEach(id=>{const e=by(id);if(e){e.hidden=life.length<2;e.style.setProperty('display',life.length<2?'none':'','important')}});
  if(!life.length){if(hero){hero.removeAttribute('src');hero.alt='Zdjęcia w przygotowaniu'}if(title)title.textContent='ZDJĘCIA W PRZYGOTOWANIU';if(sub)sub.textContent='';showCaption(false);return}
  const p=life[index];hero.src=p.src;hero.alt=p.alt||p.title||'Zdjęcie produktu';hero.style.objectPosition=p.position||'50% 50%';
  if(title)title.textContent=p.title||'';if(sub)sub.textContent=p.subtitle||'';showCaption(true);
  for(const [id,i] of [['lifestylePrevImage',wrap(index-1,life.length)],['lifestyleNextImage',wrap(index+1,life.length)]]){const e=by(id);if(e){e.src=life[i].src;e.alt=life[i].alt||life[i].title||''}}
 }
 function schedule(){clearTimeout(timer);if(life.length<2||hover||focused||document.hidden||reduced.matches||window.DW_AUTOPLAY===false)return;timer=setTimeout(()=>move(1),5000)}
 function move(delta){if(life.length<2||busy)return;clearTimeout(timer);const finish=()=>{index=wrap(index+delta,life.length);stage?.classList.add('mesh-resetting');render();stage?.classList.remove('mesh-slide-prev','mesh-slide-next');requestAnimationFrame(()=>requestAnimationFrame(()=>{stage?.classList.remove('mesh-resetting');busy=false;schedule()}))};if(!reduced.matches&&stage){busy=true;caption?.classList.add('dw-caption-exiting');stage.classList.add(delta<0?'mesh-slide-prev':'mesh-slide-next');setTimeout(finish,980)}else finish()}
 controls.forEach((id,i)=>by(id)?.addEventListener('click',()=>move(i%2?1:-1)));
 stage?.addEventListener('mouseenter',()=>{hover=true;schedule()});stage?.addEventListener('mouseleave',()=>{hover=false;schedule()});
 stage?.addEventListener('focusin',()=>{focused=true;schedule()});stage?.addEventListener('focusout',()=>setTimeout(()=>{focused=stage.contains(document.activeElement);schedule()},0));
 document.addEventListener('visibilitychange',schedule);reduced.addEventListener('change',schedule);render();schedule();
 const box=by('realizationLightbox'),track=by('realizationsTrack');let ri=0,opener=null;
 function light(n){ri=wrap(n,real.length);const p=real[ri];by('lightboxImage').src=p.src;by('lightboxImage').alt=p.alt||p.title||'';const cap=by('lightboxCaption');cap.replaceChildren();const strong=document.createElement('strong');strong.className='dw-realization-title';strong.textContent=p.title||'REALIZACJA';cap.append(strong);if(p.subtitle&&p.subtitle.trim()){const sub=document.createElement('small');sub.className='dw-realization-subtitle';sub.textContent=p.subtitle.trim();cap.append(sub)}['lightboxPrev','lightboxNext'].forEach(id=>{const e=by(id);if(e){e.hidden=real.length<2;e.style.display=real.length<2?'none':''}})}
 function open(n,button){opener=button;light(n);box.classList.add('open');box.setAttribute('aria-hidden','false');document.body.classList.add('lightbox-open');box.querySelector('.lightbox-close')?.focus()}
 function close(){box?.classList.remove('open');box?.setAttribute('aria-hidden','true');document.body.classList.remove('lightbox-open');opener?.focus()}
 if(!real.length){const section=by('realizacje');if(section)section.hidden=true}else if(track){track.replaceChildren();real.forEach((p,n)=>{const b=document.createElement('button');b.type='button';b.className='realization-thumb';b.setAttribute('aria-label','Powiększ: '+(p.title||'realizację'));const im=document.createElement('img');im.src=p.src;im.alt=p.alt||p.title||'';im.loading='lazy';const caption=document.createElement('span');caption.className='dw-realization-caption';const strong=document.createElement('strong');strong.className='dw-realization-title';strong.textContent=p.title||'REALIZACJA';caption.append(strong);if(p.subtitle&&p.subtitle.trim()){const sub=document.createElement('small');sub.className='dw-realization-subtitle';sub.textContent=p.subtitle.trim();caption.append(sub)}b.append(im,caption);b.onclick=()=>open(n,b);track.append(b)})}
 by('lightboxPrev')?.addEventListener('click',()=>light(ri-1));by('lightboxNext')?.addEventListener('click',()=>light(ri+1));box?.querySelectorAll('[data-lightbox-close]').forEach(b=>b.addEventListener('click',close));
 document.addEventListener('keydown',e=>{if(!box?.classList.contains('open'))return;if(e.key==='Escape')close();if(e.key==='ArrowLeft')light(ri-1);if(e.key==='ArrowRight')light(ri+1);if(e.key==='Tab'){const focus=[...box.querySelectorAll('button')].filter(x=>!x.hidden&&getComputedStyle(x).display!=='none');const a=focus[0],z=focus.at(-1);if(e.shiftKey&&document.activeElement===a){e.preventDefault();z.focus()}else if(!e.shiftKey&&document.activeElement===z){e.preventDefault();a.focus()}}});
 function swipe(el,left,right){let x=0,y=0;el?.addEventListener('touchstart',e=>{x=e.changedTouches[0].clientX;y=e.changedTouches[0].clientY},{passive:true});el?.addEventListener('touchend',e=>{const dx=e.changedTouches[0].clientX-x,dy=e.changedTouches[0].clientY-y;if(Math.abs(dx)>48&&Math.abs(dx)>Math.abs(dy)*1.15)(dx<0?left:right)()},{passive:true})}
 swipe(stage,()=>move(1),()=>move(-1));swipe(box,()=>real.length&&light(ri+1),()=>real.length&&light(ri-1));
 // Preserve the same visual/semantic UI as native cards after panel publication.
 document.querySelectorAll('.fw-data-fold').forEach(fold=>{
  const first=fold.querySelector('table thead tr > th:first-child');
  if(first&&first.textContent.trim().toLocaleLowerCase('pl')==='pomiar')first.textContent='Rozmiar';
  const summary=fold.querySelector('summary');
  if(!summary||summary.querySelector('.dw-size-label'))return;
  const txt=Array.from(summary.childNodes).find(n=>n.nodeType===Node.TEXT_NODE&&n.textContent.trim());
  if(!txt)return;
  const label=document.createElement('span');label.className='dw-size-label';
  const tape=document.createElement('img');tape.className='dw-size-tape';tape.src='assets/images/miarka-krawiecka-biala.png';tape.alt='';tape.setAttribute('aria-hidden','true');tape.decoding='async';
  const name=document.createElement('span');name.className='dw-size-label-text';name.textContent=txt.textContent.trim();label.append(tape,name);summary.replaceChild(label,txt);
 });
 document.querySelectorAll('.mesh-ref-actions,.fw-ref-actions').forEach(actions=>{
  const back=actions.querySelector('.mesh-category-return,.fw-ref-secondary');if(!back)return;
  const label=back.textContent.trim();if(!label.startsWith('←'))back.textContent='← '+label;
  actions.prepend(back);
 });
 document.querySelectorAll('.fw-info details').forEach(d=>d.addEventListener('toggle',()=>{if(d.open)document.querySelectorAll('.fw-info details').forEach(o=>{if(o!==d)o.open=false})}));
 const panel=by('mobPanel'),burger=by('burger'),closeMenu=by('mobClose');function menu(open){panel?.classList.toggle('open',open);panel?.setAttribute('aria-hidden',String(!open));document.body.style.overflow=open?'hidden':'';(open?closeMenu:burger)?.focus()}
 burger?.addEventListener('click',()=>menu(true));closeMenu?.addEventListener('click',()=>menu(false));panel?.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>menu(false)));document.addEventListener('keydown',e=>{if(e.key==='Escape'&&panel?.classList.contains('open'))menu(false)});
 const mobile=matchMedia('(max-width:900px)');function heading(){document.querySelector('.mesh-mobile-heading')?.removeAttribute('aria-hidden');document.querySelectorAll('.mesh-ref-info h1,.mesh-mobile-heading h1').forEach(h=>h.dataset.glitchText=h.textContent.trim())}heading();mobile.addEventListener('change',heading);
 const style=document.createElement('style');style.textContent='[hidden]{display:none!important}@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}.fw-mark-panel{display:flex!important;flex-wrap:nowrap;gap:6px}.mesh-marking-body section+section{margin-top:20px}';document.head.append(style);

  // 2026-09-27 | Allow deliberate mouse travel between Produkty and product links.
  (function(){
    const menus=document.querySelectorAll('nav.topbar .products-menu');
    const fine=window.matchMedia('(hover:hover) and (pointer:fine)');
    menus.forEach(menu=>{
      let timer=0;
      const cancel=()=>{window.clearTimeout(timer);timer=0;};
      const show=()=>{if(!fine.matches)return;cancel();menu.classList.add('dw-mega-open');};
      const hide=()=>{cancel();timer=window.setTimeout(()=>{
        if(!menu.matches(':hover,:focus-within'))menu.classList.remove('dw-mega-open');
      },1100);};
      menu.addEventListener('pointerenter',show);
      menu.addEventListener('pointerleave',hide);
      menu.addEventListener('focusin',show);
      menu.addEventListener('focusout',hide);
      document.addEventListener('keydown',event=>{if(event.key==='Escape'){cancel();menu.classList.remove('dw-mega-open');}});
    });
  })();
})();

 document.body.classList.add('dw-clubs-ready');
})();
