// HERO SLIDER — robust fallback until background video is supplied
(function() {
  var slides = Array.from(document.querySelectorAll('.hero-slide'));
  var dotsWrap = document.getElementById('heroDots');
  if (!slides.length || !dotsWrap) return;
  var cur = 0;
  slides.forEach(function(_, i) {
    var d = document.createElement('button');
    d.type = 'button';
    d.className = 'hero-dot' + (i === 0 ? ' active' : '');
    d.setAttribute('aria-label', 'Pokaż slajd ' + (i + 1));
    d.addEventListener('click', function() { go(i); });
    dotsWrap.appendChild(d);
  });
  function go(idx) {
    if (!slides.length) return;
    slides[cur].classList.remove('visible');
    if (dotsWrap.children[cur]) dotsWrap.children[cur].classList.remove('active');
    cur = (idx + slides.length) % slides.length;
    slides[cur].classList.add('visible');
    if (dotsWrap.children[cur]) dotsWrap.children[cur].classList.add('active');
  }
  if (slides.length > 1) {
    var timer = setInterval(function() { if (!document.hidden) go(cur + 1); }, 5000);
    window.addEventListener('beforeunload', function(){ clearInterval(timer); });
  }
})();
