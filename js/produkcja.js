(function(){
  var grid  = document.getElementById('procGrid');
  var svg   = document.getElementById('procSvg');
  var line1 = document.getElementById('pLine1');
  var line2 = document.getElementById('pLine2');
  var line3 = document.getElementById('pLine3');
  var dot   = document.getElementById('pDot');
  var steps = Array.from(grid.querySelectorAll('.proc-step'));

  // ── helpers ────────────────────────────────────────────────────────────────
  function nodeCenter(step) {
    var ring = step.querySelector('.proc-node-ring');
    var sr   = svg.getBoundingClientRect();
    var nr   = ring.getBoundingClientRect();
    return {
      x: (nr.left + nr.right)  / 2 - sr.left,
      y: (nr.top  + nr.bottom) / 2 - sr.top
    };
  }

  function setLine(el, p1, p2) {
    el.setAttribute('x1', p1.x); el.setAttribute('y1', p1.y);
    el.setAttribute('x2', p2.x); el.setAttribute('y2', p2.y);
    el.setAttribute('opacity', '0.35');
  }

  function drawLines() {
    var p = steps.map(nodeCenter);
    // row 1: 0→1 (left to right)
    setLine(line1, p[0], p[1]);
    // descend: 1→2
    setLine(line2, p[1], p[2]);
    // row 2: 2→3 (left to right)
    setLine(line3, p[2], p[3]);
  }

  // ── activate ───────────────────────────────────────────────────────────────
  function activate(idx) {
    steps.forEach(function(s, i) {
      s.classList.toggle('active', i === idx);
    });
  }

  // ── dot animation ──────────────────────────────────────────────────────────
  // path: 0→1, 1→2, 2→3, pause, reset
  var segments = [[0,1],[1,2],[2,3]];
  var segIdx   = 0;
  var progress = 0;
  var pausing  = 0;
  var SPEED    = 0.008;
  var PAUSE    = 45;
  var rafId    = null;
  var hovered  = false;

  function tick() {
    var pts = steps.map(nodeCenter);

    if (pausing > 0) {
      pausing--;
      rafId = requestAnimationFrame(tick);
      return;
    }

    progress += SPEED;

    if (progress >= 1) {
      progress = 0;
      var arrivedAt = segments[segIdx][1];
      activate(arrivedAt);
      segIdx = (segIdx + 1) % segments.length;
      pausing = PAUSE;

      if (segIdx === 0) {
        // full cycle — hide dot, long pause, restart from step 0
        dot.setAttribute('opacity', '0');
        pausing = PAUSE * 4;
        setTimeout(function(){ activate(0); }, PAUSE * 4 * 16);
      }
      rafId = requestAnimationFrame(tick);
      return;
    }

    var seg  = segments[segIdx];
    var from = pts[seg[0]];
    var to   = pts[seg[1]];
    var x = from.x + (to.x - from.x) * progress;
    var y = from.y + (to.y - from.y) * progress;

    dot.setAttribute('cx', x);
    dot.setAttribute('cy', y);
    dot.setAttribute('opacity', '1');

    rafId = requestAnimationFrame(tick);
  }

  function startAnim() {
    if (rafId) cancelAnimationFrame(rafId);
    segIdx = 0; progress = 0; pausing = PAUSE;
    activate(0);
    rafId = requestAnimationFrame(tick);
  }

  // ── hover ──────────────────────────────────────────────────────────────────
  steps.forEach(function(step, i) {
    step.addEventListener('mouseenter', function() {
      hovered = true;
      if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
      dot.setAttribute('opacity', '0');
      activate(i);
    });
    step.addEventListener('mouseleave', function() {
      hovered = false;
      setTimeout(function() {
        if (!hovered) startAnim();
      }, 700);
    });
  });

  // ── init ───────────────────────────────────────────────────────────────────
  function init() {
    drawLines();
    startAnim();
  }

  window.addEventListener('resize', drawLines);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function(){ setTimeout(init, 100); });
  } else {
    setTimeout(init, 100);
  }
})();