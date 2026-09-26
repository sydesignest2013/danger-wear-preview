/* Danger Wear: authentic, unedited method footage, lazy-loaded on hover or tap. */
(function () {
  'use strict';
  var lang = (document.documentElement.lang || 'pl').slice(0,2);
  var dictionary = {
    pl: { watch:'Odtwórz film przedstawiający', stop:'Zatrzymaj film', video:'WIDEO', names:{sublimacja:'druk sublimacyjny','haft-komputerowy':'haft komputerowy',dtf:'transfer DTF'} },
    en: { watch:'Play video showing', stop:'Pause video', video:'VIDEO', names:{sublimacja:'sublimation printing','haft-komputerowy':'machine embroidery',dtf:'DTF heat transfer'} },
    de: { watch:'Video abspielen:', stop:'Video anhalten', video:'VIDEO', names:{sublimacja:'Sublimationsdruck','haft-komputerowy':'Maschinenstickerei',dtf:'DTF-Transfer'} },
    fr: { watch:'Lire la vidéo :', stop:'Mettre la vidéo en pause', video:'VIDÉO', names:{sublimacja:'impression par sublimation','haft-komputerowy':'broderie machine',dtf:'transfert DTF'} }
  };
  var copy=dictionary[lang] || dictionary.pl;
  var finePointer=window.matchMedia && window.matchMedia('(hover:hover) and (pointer:fine)').matches;
  var reduce=window.matchMedia && window.matchMedia('(prefers-reduced-motion:reduce)').matches;
  var sessions=[];
  function stop(entry) {
    if (!entry) return;
    var v=entry.video;
    v.pause();
    try{v.currentTime=0;}catch(e){}
    entry.surface.classList.remove('is-video-playing');
    if(entry.control){entry.control.setAttribute('aria-pressed','false');entry.control.setAttribute('aria-label',copy.watch+' '+entry.name);}
  }
  function stopAll(except){sessions.forEach(function(item){if(item!==except)stop(item);});}
  function start(entry) {
    if (document.hidden) return;
    stopAll(entry);
    var v=entry.video;
    if (!v.getAttribute('src')){
      v.src=v.dataset.src;
      v.load();
    }
    v.muted=true;
    v.playsInline=true;
    var playing=v.play();
    if(playing && playing.catch)playing.catch(function(){stop(entry);});
  }
  document.querySelectorAll('.dw-prod-method .dw-method-visual[data-dw-video]').forEach(function(surface){
    var method=surface.getAttribute('data-dw-video');
    var video=surface.querySelector('video.dw-method-video[data-src]');
    var control=surface.querySelector('button.dw-method-video-toggle');
    if(!video || !control) return;
    var entry={surface:surface,video:video,control:control,name:copy.names[method]||method};
    sessions.push(entry);
    control.setAttribute('aria-label',copy.watch+' '+entry.name);
    var word=control.querySelector('span:last-child');if(word)word.textContent=copy.video;
    video.addEventListener('playing',function(){surface.classList.add('is-video-playing');control.setAttribute('aria-pressed','true');control.setAttribute('aria-label',copy.stop+' '+entry.name);});
    video.addEventListener('error',function(){stop(entry);});
    control.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();if(!video.paused)stop(entry);else start(entry);});
    if(finePointer && !reduce){surface.addEventListener('mouseenter',function(){start(entry);});surface.addEventListener('mouseleave',function(){stop(entry);});}
  });
  var sewing=document.querySelector('.dw-prod-stage[data-stage="2"]');
  if(sewing){
    var sewingVideo=sewing.querySelector('video.dw-stage-video[data-src]');
    if(sewingVideo){
      var stage={surface:sewing,video:sewingVideo,control:null,name:'sewing'};
      sessions.push(stage);
      sewingVideo.addEventListener('playing',function(){sewing.classList.add('is-video-playing');});
      sewingVideo.addEventListener('error',function(){stop(stage);});
      if(finePointer && !reduce){sewing.addEventListener('mouseenter',function(){start(stage);});sewing.addEventListener('mouseleave',function(){stop(stage);});}
      if(!finePointer){sewing.addEventListener('click',function(){if(sewingVideo.paused)start(stage);else stop(stage);});}
    }
  }
  if('IntersectionObserver' in window){
    var observer=new IntersectionObserver(function(records){records.forEach(function(record){if(!record.isIntersecting){sessions.forEach(function(item){if(item.surface===record.target)stop(item);});}});},{threshold:.05});
    sessions.forEach(function(item){observer.observe(item.surface);});
  }
  document.addEventListener('visibilitychange',function(){if(document.hidden)stopAll();});
})();
