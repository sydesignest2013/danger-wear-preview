// REVEAL
var obs = new IntersectionObserver(function(entries) {
  entries.forEach(function(e) { if (e.isIntersecting) e.target.classList.add('in'); });
}, { threshold: .08 });
document.querySelectorAll('.reveal').forEach(function(el) { obs.observe(el); });

// UNIFIED PRODUCT REFERENCE OVERLAY 2026-09-16
(function () {
  var page = document.querySelector('.pp-page');
  var visual = page && page.querySelector('.pp-visual');
  var copy = page && page.querySelector('.pp-copy');
  if (!visual || !copy || visual.querySelector('.pp-ref-brand')) return;

  var heading = copy.querySelector('h1');
  var kicker = copy.querySelector('.pp-kicker');
  var index = visual.querySelector('.pp-index');
  var title = heading ? heading.textContent.trim() : 'DANGER WEAR';
  var category = kicker ? kicker.textContent.split('/').pop().trim() : 'PRODUKT';
  var code = index ? index.textContent.trim() : 'DW';

  var brand = document.createElement('div');
  brand.className = 'pp-ref-brand';
  brand.innerHTML = '<strong>DANGER WEAR</strong><span>PRODUCTION</span>';

  var caption = document.createElement('div');
  caption.className = 'pp-ref-caption';
  caption.innerHTML = '<strong></strong><span></span>';
  caption.querySelector('strong').textContent = title;
  caption.querySelector('span').textContent = code + '   ' + category;

  visual.appendChild(brand);
  visual.appendChild(caption);
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
    document.querySelectorAll('.dw-theme-toggle button[data-theme-value]').forEach(function(btn){btn.setAttribute('aria-pressed',String(btn.getAttribute('data-theme-value')===value));});
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
