(() => {
  const MOBILE_MAX = 900;
  const selectors = [
    '.product-head h1',
    '.pp-copy h1',
    '.dw-heading h1',
    '.dw-product-heading h1',
    '.products-index-card h2',
    '.dw-family h2',
    '.cat-tile-name'
  ];

  const targets = () => [...document.querySelectorAll(selectors.join(','))];

  function fitOneLine(el) {
    el.classList.add('dw-mobile-fit-line');
    el.style.removeProperty('font-size');
    el.style.removeProperty('letter-spacing');

    if (window.innerWidth > MOBILE_MAX) {
      el.classList.remove('dw-mobile-fit-line');
      return;
    }

    const width = Math.max(0, el.clientWidth - 1);
    if (!width) return;

    const computed = getComputedStyle(el);
    const initialSize = parseFloat(computed.fontSize) || 16;
    const minSize = el.matches('.cat-tile-name') ? 9 : 8.5;
    let low = minSize;
    let high = initialSize;

    el.style.fontSize = `${high}px`;
    if (el.scrollWidth <= width) return;

    for (let i = 0; i < 12; i += 1) {
      const mid = (low + high) / 2;
      el.style.fontSize = `${mid}px`;
      if (el.scrollWidth <= width) low = mid;
      else high = mid;
    }
    el.style.fontSize = `${Math.max(minSize, low - 0.15)}px`;

    // Extreme fallback: preserve one line by tightening tracking slightly.
    if (el.scrollWidth > width) {
      const currentSpacing = parseFloat(getComputedStyle(el).letterSpacing) || 0;
      el.style.letterSpacing = `${Math.min(currentSpacing, -0.35)}px`;
    }
  }

  function fitAll() {
    targets().forEach(fitOneLine);
  }

  let resizeTimer = 0;
  window.addEventListener('resize', () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(fitAll, 80);
  }, { passive: true });

  window.addEventListener('orientationchange', () => {
    window.setTimeout(fitAll, 120);
  }, { passive: true });

  document.addEventListener('DOMContentLoaded', fitAll, { once: true });
  if (document.fonts?.ready) document.fonts.ready.then(fitAll).catch(() => {});
  requestAnimationFrame(fitAll);
})();

/* === DANGER WEAR THEME SWITCH — GLOBAL / 2026-09-18 === */
(function(){
  if(window.__DW_THEME_SWITCH__) return;
  window.__DW_THEME_SWITCH__=true;
  var KEY='danger-wear-theme';
  function getSaved(){
    try{return localStorage.getItem(KEY)==='light'?'light':'dark';}catch(e){return 'dark';}
  }
  function apply(theme){
    var value=theme==='light'?'light':'dark';
    document.documentElement.setAttribute('data-theme',value);
    document.documentElement.style.colorScheme=value;
    try{localStorage.setItem(KEY,value);}catch(e){}
    var buttons=document.querySelectorAll('.dw-theme-toggle button[data-theme-value]');
    buttons.forEach(function(btn){btn.setAttribute('aria-pressed',String(btn.getAttribute('data-theme-value')===value));});
  }
  function mount(){
    if(document.querySelector('.dw-theme-toggle')){apply(getSaved());return;}
    document.body.classList.add('dw-theme-ready');
    var wrap=document.createElement('div');
    wrap.className='dw-theme-toggle';
    wrap.setAttribute('role','group');
    wrap.setAttribute('aria-label','Wybierz motyw strony');
    wrap.innerHTML='<button type="button" data-theme-value="light" aria-label="Motyw jasny" title="Motyw jasny">☀</button><button type="button" data-theme-value="dark" aria-label="Motyw ciemny" title="Motyw ciemny">☾</button>';
    wrap.addEventListener('click',function(event){
      var btn=event.target.closest('button[data-theme-value]');
      if(btn) apply(btn.getAttribute('data-theme-value'));
    });
    document.body.appendChild(wrap);
    apply(getSaved());
  }
  apply(getSaved());
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',mount,{once:true});
  else mount();
})();
