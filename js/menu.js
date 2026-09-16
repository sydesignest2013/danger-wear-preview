// NAV — desktop + mobile, defensive on every page
var lastY = window.scrollY || 0;
var nav = document.getElementById('mainNav');
if (nav) {
  window.addEventListener('scroll', function() {
    var y = window.scrollY || 0;
    var delta = y - lastY;
    if (Math.abs(delta) > 4) nav.style.transform = (delta > 0 && y > 110) ? 'translateY(-100%)' : 'translateY(0)';
    lastY = y;
  }, { passive: true });
}
function toggleProj() { var el=document.getElementById('projLi'); if(el) el.classList.toggle('open'); }
document.addEventListener('click', function(e) { var li=document.getElementById('projLi'); if(li && !li.contains(e.target)) li.classList.remove('open'); });
document.addEventListener('keydown', function(e) { if(e.key==='Escape'){ var li=document.getElementById('projLi'); if(li) li.classList.remove('open'); closeMob(); } });
function toggleMob() {
  var b=document.getElementById('hamburger'), m=document.getElementById('mobMenu'), o=document.getElementById('mobOverlay');
  if(!m) return; if(b) b.classList.toggle('open'); m.classList.toggle('open'); if(o) o.classList.toggle('open');
  document.body.style.overflow=m.classList.contains('open')?'hidden':'';
}
function closeMob() {
  var b=document.getElementById('hamburger'), m=document.getElementById('mobMenu'), o=document.getElementById('mobOverlay');
  if(b) b.classList.remove('open'); if(m) m.classList.remove('open'); if(o) o.classList.remove('open'); document.body.style.overflow='';
}
function toggleMobSub() { var b=document.getElementById('mobProjBtn'), s=document.getElementById('mobSub'); if(b) b.classList.toggle('open'); if(s) s.classList.toggle('open'); }

// Mobile ergonomics: close drawer after navigation and restore scrolling on viewport changes.
document.querySelectorAll('#mobMenu a').forEach(function(link){ link.addEventListener('click', closeMob); });
window.addEventListener('resize', function(){ if(window.innerWidth > 900) closeMob(); }, { passive:true });
