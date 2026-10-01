(() => {
  'use strict';

  const hour = Math.floor(Date.now() / 3600000);
  const score = (text, offset) => {
    let value = 2166136261;
    for (const character of `${text}|${hour}|${offset}`) {
      value ^= character.charCodeAt(0);
      value = Math.imul(value, 16777619);
    }
    return value >>> 0;
  };
  const areRivals = (rivalries, first, second) => rivalries.some(([left, right]) =>
    (left === first && right === second) || (left === second && right === first)
  );

  const render = (root, rivalries) => {
    let items;
    try { items = JSON.parse(root.dataset.categoryProducts || '[]'); } catch { return false; }
    const usedClubs = [];
    root.innerHTML = '';
    items.forEach((item, index) => {
      const photos = Array.isArray(item.photos) ? item.photos : [];
      const card = document.createElement(item.href ? 'a' : 'div');
      card.className = `dw-category-card${photos.length ? '' : ' is-pending'}`;
      if (photos.length) {
        const ranked = [...photos].sort((left, right) => score(left.src, index) - score(right.src, index));
        const photo = ranked.find(({ club }) => !usedClubs.some((used) => used === club || areRivals(rivalries, used, club))) || ranked[0];
        if (photo.club) usedClubs.push(photo.club);
        card.href = item.href;
        card.setAttribute('aria-label', `${item.name}: zobacz produkty`);
        const image = document.createElement('img');
        image.src = photo.src;
        image.alt = item.name;
        image.loading = 'lazy';
        card.append(image);
      } else {
        if (item.href) card.href = item.href;
        card.setAttribute('aria-label', `${item.name}: zdjęcia lifestyle w przygotowaniu`);
        const note = document.createElement('small');
        note.textContent = 'Lifestyle w przygotowaniu';
        card.append(note);
      }
      const label = document.createElement('span');
      label.textContent = item.name;
      card.append(label);
      root.append(card);
    });
    return true;
  };

  const init = async () => {
    let rivalries = [];
    try {
      const response = await fetch('js/dw-clubs-data.json', { cache: 'no-store' });
      if (response.ok) {
        const data = await response.json();
        rivalries = Array.isArray(data.rivalries) ? data.rivalries : [];
      }
    } catch {
      // Known photo-to-club associations remain usable if the data file is unavailable.
    }
    let rendered = false;
    document.querySelectorAll('[data-category-products]').forEach((root) => { rendered = render(root, rivalries) || rendered; });
    if (rendered) document.documentElement.classList.add('dw-category-ready');
  };
  init();
})();
