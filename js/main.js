// REVEAL
var obs = new IntersectionObserver(function(entries) {
  entries.forEach(function(e) { if (e.isIntersecting) e.target.classList.add('in'); });
}, { threshold: .08 });
document.querySelectorAll('.reveal').forEach(function(el) { obs.observe(el); });


