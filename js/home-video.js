/* Original footage in the homepage hero. Keep a still poster for reduced motion. */
(function(){
  'use strict';
  var video=document.querySelector('.dw-home-video-hero video.dw-hero-bg-video');
  if(!video)return;
  var motion=window.matchMedia && window.matchMedia('(prefers-reduced-motion:reduce)');
  function sync(){if(document.hidden || (motion && motion.matches)){video.pause();return;}
    video.muted=true;video.playsInline=true;
    var r=video.play();if(r && r.catch)r.catch(function(){});
  }
  if(motion){if(motion.addEventListener)motion.addEventListener('change',sync);else if(motion.addListener)motion.addListener(sync);}
  document.addEventListener('visibilitychange',sync);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',sync,{once:true});else sync();
})();
