// NAV
var lastY = 0;
var nav = document.getElementById('mainNav');
window.addEventListener('scroll', function() {
  var y = window.scrollY;
  nav.style.transform = (y > lastY && y > 80 && !document.getElementById('projLi')?.classList.contains('open') && !nav.matches(':hover,:focus-within')) ? 'translateY(-100%)' : 'translateY(0)';
  lastY = y;
});

function toggleProj() {
  document.getElementById('projLi').classList.toggle('open');
}
document.addEventListener('click', function(e) {
  var li = document.getElementById('projLi');
  if (li && !li.contains(e.target)) li.classList.remove('open');
});
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.getElementById('projLi').classList.remove('open');
    closeMob();
  }
});

// MOBILE MENU
function toggleMob() {
  document.getElementById('hamburger').classList.toggle('open');
  document.getElementById('mobMenu').classList.toggle('open');
  document.getElementById('mobOverlay').classList.toggle('open');
  document.body.style.overflow = document.getElementById('mobMenu').classList.contains('open') ? 'hidden' : '';
}
function closeMob() {
  document.getElementById('hamburger').classList.remove('open');
  document.getElementById('mobMenu').classList.remove('open');
  document.getElementById('mobOverlay').classList.remove('open');
  document.body.style.overflow = '';
}
function toggleMobSub() {
  document.getElementById('mobProjBtn').classList.toggle('open');
  document.getElementById('mobSub').classList.toggle('open');
}

// Mobile product shortcuts mirror the desktop hierarchy while opening the
// concrete product requested for each family.
(() => {
  const sub = document.getElementById('mobSub');
  if (!sub) return;
  sub.innerHTML = [
    ['produkty.html', 'WSZYSTKIE PRODUKTY'],
    ['koszulki-sportowe.html', 'SPORTSWEAR'],
    ['fightwear-set.html', 'FIGHTWEAR'],
    ['streetwear-bluzy.html', 'STREETWEAR'],
    ['czapki-z-daszkiem.html', 'AKCESORIA']
  ].map(([href, label]) => `<a href="${href}">${label}</a>`).join('');
})();

// 2026-09-27 | Hover intent: allow a full second to reach a menu item without the panel disappearing.
(function(){
  const li=document.getElementById('projLi');
  const dropdown=li?.querySelector('.nav-dropdown.dw-home-mega');
  if(!li || !dropdown) return;
  const fine=window.matchMedia('(hover:hover) and (pointer:fine)');
  let closeTimer=0;
  const cancel=()=>{window.clearTimeout(closeTimer);closeTimer=0;};
  const open=()=>{if(!fine.matches)return;cancel();li.classList.add('open');if(nav)nav.style.transform='translateY(0)';};
  const delay=()=>{if(!fine.matches)return;cancel();closeTimer=window.setTimeout(()=>{
    if(!dropdown.matches(':hover')&&!li.matches(':hover')&&!li.matches(':focus-within'))li.classList.remove('open');
  },1050);};
  li.addEventListener('pointerenter',open);
  li.addEventListener('pointerleave',delay);
  dropdown.addEventListener('pointerenter',open);
  dropdown.addEventListener('pointerleave',delay);
  li.addEventListener('focusin',()=>{cancel();li.classList.add('open');});
  li.addEventListener('focusout',()=>{cancel();closeTimer=window.setTimeout(()=>{
    if(!li.contains(document.activeElement))li.classList.remove('open');
  },220);});
  document.addEventListener('pointerdown',e=>{if(!li.contains(e.target))cancel();});
})();

/* DW product menu: decorative line icons keyed by existing product URLs. */
(()=>{
 const shapes={
 shirt:'M8 3 2 6l3 6 3-2v11h8V10l3 2 3-6-6-3c0 4-8 4-8 0Z',
 tank:'M8 3H5v18h14V3h-3c0 6-8 6-8 0Z',
 hoodie:'M8 6C6 0 18 0 16 6l5 3-2 9-3-1v5H8v-5l-3 1-2-9 5-3Zm0 0 4 4 4-4M9 17h6v4H9Z',
 jacket:'M8 3 3 7 1 19l4 1 3-9v11h8V11l3 9 4-1-2-12-5-4-4 3-4-3Zm4 3v16M8 12h8M8 16h8',
 trousers:'M6 2h12l2 20h-6l-2-13-2 13H4L6 2Zm0 4h12',
 shorts:'M5 3h14l2 17h-8l-1-10-1 10H3L5 3Zm0 4h14',
 cap:'M4 13V9a7 7 0 0 1 14 0v4M2 13h16l4 4H8l-6-4Z',
 beanie:'M5 14V9a7 7 0 0 1 14 0v5M3 14h18v7H3Z',
 scarf:'M5 2h5v17H5Zm9 0h5v17h-5ZM5 19v3m3-3v3m6-3v3m3-3v3M10 3h4',
 mask:'M5 21V9a7 7 0 0 1 14 0v12ZM7 9c3-2 7-2 10 0-2 4-3 4-5 1-2 3-3 3-5-1Z',
 flag:'M4 23V2m0 1c5-5 10 5 16 0v11c-6 5-11-5-16 0',
 bag:'M4 8h16l-1 13H5L4 8Zm4 0V6a4 4 0 0 1 8 0v2M8 12h8',
 sack:'M6 3h12l-2 4 4 13c-5 3-11 3-16 0L8 7 6 3Zm2 4h8',
 towel:'M5 2h14v20H5ZM5 6h14M5 18h14',
 pillow:'M4 4c5 2 11 2 16 0-2 5-2 11 0 16-5-2-11-2-16 0 2-5 2-11 0-16Z',
 glove:'M7 21 3 12c-1-3 2-3 4 0V5c0-2 3-2 3 0V3c0-2 3-2 3 0v2c0-2 3-2 3 0v2c0-2 3-2 3 0v9l-3 5H7Z',
 tube:'M5 4c4-2 10-2 14 0v16c-4 2-10 2-14 0V4Zm0 0c4 3 10 3 14 0',
 lanyard:'M8 2 5 6l6 11h2l6-11-3-4-4 10-4-10Zm3 15v3h2v-3M10 20h4v3h-4Z',
 grid:'M3 3h7v7H3Zm11 0h7v7h-7ZM3 14h7v7H3Zm11 0h7v7h-7Z'
 };
 function kind(h){if(/tank|bezrekaw/.test(h))return'tank';if(/bluz/.test(h))return'hoodie';if(/kurtk/.test(h))return'jacket';if(/spoden/.test(h))return'shorts';if(/spodni|leggins/.test(h))return'trousers';if(/daszk/.test(h))return'cap';if(/czapk/.test(h))return'beanie';if(/szalik/.test(h))return'scarf';if(/kominiark/.test(h))return'mask';if(/flag/.test(h))return'flag';if(/nerk|saszet/.test(h))return'bag';if(/worki/.test(h))return'sack';if(/recznik/.test(h))return'towel';if(/poduszk/.test(h))return'pillow';if(/rekawicz/.test(h))return'glove';if(/komin|chust/.test(h))return'tube';if(/smycz/.test(h))return'lanyard';if(/koszulk|rashguard|fightwear-set/.test(h))return'shirt';return'grid'}
 function decorate(){document.querySelectorAll('.nav-dropdown a.nav-dropdown-sub,.mob-menu .mob-sub a[href],.mob-menu .mob-products a[href]').forEach(a=>{if(a.querySelector('.dw-menu-icon'))return;const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('class','dw-menu-icon');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',shapes[kind(a.getAttribute('href')||'')]);svg.append(path);a.prepend(svg);a.classList.add('dw-icon-link')})}
 decorate();new MutationObserver(decorate).observe(document.body,{childList:true,subtree:true});
})();


/* User-supplied SVG artwork, October 2026. */
(()=>{const base=new URL('../assets/icons/menu/',document.currentScript.src);const names=['koszulki-sportowe','koszulki-sportowe-athletic','tank-top','rashguard','spodenki-mma-luzne','spodenki-mma-vale-tudo','legginsy-sportowe','fightwear-set','streetwear-koszulki','streetwear-bluzy','streetwear-kurtki','streetwear-bezrekawniki','streetwear-spodnie','streetwear-spodenki','szaliki','flagi-drukowane','czapki-z-daszkiem','czapki-zimowe','rekawiczki','kominy-termoaktywne','kominy-polarowe-zimowe','kominiarki','chusty','nerki-saszetki'];const ids=[2,3,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26];function update(){document.querySelectorAll('a.dw-icon-link').forEach(a=>{if(a.dataset.userIcon)return;const key=(a.getAttribute('href')||'').split('/').pop().split(/[?#]/)[0].replace('.html','');const i=names.indexOf(key);if(i<0)return;a.dataset.userIcon='true';a.querySelector('.dw-menu-icon')?.remove();const icon=document.createElement('span');icon.className='dw-menu-icon dw-user-menu-icon';icon.setAttribute('aria-hidden','true');icon.style.setProperty('--menu-art',`url("${new URL(ids[i]+'.svg',base)}")`);a.prepend(icon)})}update();new MutationObserver(update).observe(document.body,{childList:true,subtree:true})})();
