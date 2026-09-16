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
