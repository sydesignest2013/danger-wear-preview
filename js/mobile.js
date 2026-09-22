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
    function placeThemeToggle(){
      var desktop=window.matchMedia('(min-width:901px)').matches;
      var target=desktop ? (document.querySelector('nav.topbar .navlinks') || document.querySelector('nav#mainNav .nav-links')) : document.body;
      if(target && wrap.parentNode!==target) target.appendChild(wrap);
    }
    placeThemeToggle();
    window.addEventListener('resize',placeThemeToggle,{passive:true});
    apply(getSaved());
  }
  apply(getSaved());
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',mount,{once:true});
  else mount();
})();

/* === GLOBAL SOCIAL FOOTER — ALL PAGES / 2026-09-18 === */
(function(){
  if(window.__DW_GLOBAL_FOOTER__) return;
  window.__DW_GLOBAL_FOOTER__=true;

  function ensureStylesheet(href){
    var exists=[].slice.call(document.querySelectorAll('link[rel="stylesheet"]')).some(function(link){
      return (link.getAttribute('href')||'').split('?')[0]===href;
    });
    if(exists) return;
    var link=document.createElement('link');
    link.rel='stylesheet';
    link.href=href+'?v=20260918-final-v5';
    document.head.appendChild(link);
  }

  function socialMarkup(){
    return ''+
      '<a href="https://www.instagram.com/danger_wear_production/" target="_blank" rel="noopener" class="social-item">'+
        '<svg class="social-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="2" y="2" width="20" height="20" rx="5" stroke="currentColor" stroke-width="1.5"></rect><circle cx="12" cy="12" r="4.5" stroke="currentColor" stroke-width="1.5"></circle><circle cx="17.5" cy="6.5" r="1" fill="currentColor"></circle></svg>'+
        '<div class="social-info"><span class="social-name">Instagram</span><span class="social-handle">@danger_wear_production</span></div><span class="social-arrow">↗</span>'+
      '</a>'+
      '<a href="https://www.facebook.com/DangerWearProduction" target="_blank" rel="noopener" class="social-item">'+
        '<svg class="social-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M18 2H15C13.3 2 12 3.3 12 5V8H9V12H12V22H16V12H19L20 8H16V5C16 4.4 16.4 4 17 4H20V2Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path></svg>'+
        '<div class="social-info"><span class="social-name">Facebook</span><span class="social-handle">DangerWearProduction</span></div><span class="social-arrow">↗</span>'+
      '</a>'+
      '<a href="mailto:kontakt@dangerwear.pl" class="social-item" aria-label="Napisz e-mail na Kontakt@Dangerwear.PL">'+
        '<svg class="social-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="2.5" y="4.5" width="19" height="15" rx="2" stroke="currentColor" stroke-width="1.5"></rect><path d="M4 7L12 13L20 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path></svg>'+
        '<div class="social-info"><span class="social-name">Kontakt@Dangerwear.PL</span><span class="social-handle">Napisz do nas</span></div><span class="social-arrow">↗</span>'+
      '</a>';
  }

  function mountFooter(){
    ensureStylesheet('css/socials.css');
    ensureStylesheet('css/footer.css');

    var social=document.querySelector('.social-bar');
    var footer=document.querySelector('footer');

    if(!social){
      social=document.createElement('div');
      social.className='social-bar dw-global-social';
      social.innerHTML=socialMarkup();
      if(footer && footer.parentNode) footer.parentNode.insertBefore(social,footer);
      else document.body.appendChild(social);
    }else{
      social.classList.add('dw-global-social');
    }

    if(!footer){
      footer=document.createElement('footer');
      footer.className='dw-global-footer';
      footer.innerHTML='<p>© 2026 Danger Wear Production. Wszelkie prawa zastrzeżone.</p><small>Produkcja odzieży i gadżetów w Polsce.</small>';
      document.body.appendChild(footer);
    }else{
      footer.classList.add('dw-global-footer');
    }
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',mountFooter,{once:true});
  else mountFooter();
})();
