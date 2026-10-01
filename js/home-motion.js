/* Values are read from the existing counter text; no separate data source. */
(()=>{
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
  const counters=[...document.querySelectorAll('.home-stat strong')];
  const active=new Map();
  function finish(){for(const [node,state] of active){cancelAnimationFrame(state.frame);node.textContent=state.original;}active.clear();}
  const observer=new IntersectionObserver(entries=>{
    for(const entry of entries){
      if(!entry.isIntersecting)continue;
      const node=entry.target;observer.unobserve(node);
      if(reduced.matches)continue;
      const original=node.textContent;
      const match=original.match(/\d[\d\s]*(?:[.,]\d+)?/);
      if(!match)continue;
      const target=Number(match[0].replace(/\s/g,'').replace(',','.'));
      if(!Number.isFinite(target))continue;
      const decimals=(match[0].split(/[.,]/)[1]||'').length;
      const prefix=original.slice(0,match.index),suffix=original.slice(match.index+match[0].length);
      node.setAttribute('aria-label',original);
      const state={original,frame:0};active.set(node,state);
      let start;
      function tick(now){
        start??=now;
        const progress=Math.min((now-start)/1400,1);
        const value=target*(1-Math.pow(1-progress,3));
        node.textContent=prefix+value.toLocaleString('pl-PL',{minimumFractionDigits:decimals,maximumFractionDigits:decimals})+suffix;
        if(progress<1)state.frame=requestAnimationFrame(tick);
        else{node.textContent=original;active.delete(node);}
      }
      state.frame=requestAnimationFrame(tick);
    }
  },{threshold:.5});
  counters.forEach(node=>observer.observe(node));
  reduced.addEventListener('change',()=>{if(reduced.matches)finish();});
})();
