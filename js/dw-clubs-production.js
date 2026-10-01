(async()=>{
  const base=new URL('.',document.currentScript.src);
  const visuals=[...document.querySelectorAll('.dw-prod-method[data-method]')];
  // Hide legacy photos until the current shared rules have been applied.
  visuals.forEach(el=>{const v=el.querySelector('.dw-method-visual');if(v)v.style.visibility='hidden';});
  try {
    const {load}=await import(new URL('dw-clubs-engine.js',base));const e=await load(base);
    let previous={};try{previous=JSON.parse(sessionStorage.getItem('dw-clubs-production')||'{}');}catch(_){}
    const selected=e.production(e.data.methods,previous),last={};
    for(const el of visuals){
      const key=el.dataset.method,v=el.querySelector('.dw-method-visual'),img=v?.querySelector(':scope > img'),p=selected[key];
      if(!img||!v)continue;
      if(p){img.src=p.src;img.removeAttribute('srcset');img.classList.remove('is-fading');img.onerror=()=>{img.hidden=true;};v.style.visibility='visible';last[key]=p.src;}
      else {img.hidden=true;v.style.visibility='visible';}
    }
    try{sessionStorage.setItem('dw-clubs-production',JSON.stringify(last));}catch(_){}
  } catch(error) { console.warn('Danger Wear: nie można bezpiecznie dobrać zdjęć metod.',error); }
})();
