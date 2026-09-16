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
