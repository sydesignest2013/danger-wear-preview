(() => {
 const section=document.querySelector('.stats-section'); if(!section)return;
 const numbers=[...section.querySelectorAll('[data-count]')];
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 function animate(){numbers.forEach((el,i)=>{const target=Number(el.dataset.count);if(reduced.matches){el.textContent=target;return;}const start=performance.now()+i*100,duration=[1400,1200,900,1100][i];function tick(now){const t=Math.max(0,Math.min(1,(now-start)/duration));el.textContent=Math.round(target*(1-Math.pow(1-t,3)));if(t<1)requestAnimationFrame(tick);}requestAnimationFrame(tick);});}
 if(!('IntersectionObserver' in window)||reduced.matches)return;
 const observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){observer.disconnect();animate();}},{threshold:.3});observer.observe(section);
})();
