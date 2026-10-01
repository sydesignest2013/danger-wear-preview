/* Danger Wear | homepage hero video — desktop-safe muted autoplay + visible manual fallback. */
(function () {
  'use strict';

  var hero = document.querySelector('.dw-home-video-hero');
  var video = hero && hero.querySelector('video.dw-hero-bg-video');
  if (!hero || !video) return;

  var button = hero.querySelector('.dw-home-video-play');
  var status = hero.querySelector('.dw-home-video-status');
  var motion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
  var retryTimers = [];
  var filePath = 'hero-video/hero.mp4';
  var copies = {
    pl: ['Nie można wczytać filmu. Sprawdź synchronizację ', ' na dysku G:.', 'Film jest chwilowo niedostępny.'],
    en: ['Cannot load the video. Check that ', ' is available on your computer.', 'The video is temporarily unavailable.'],
    de: ['Das Video konnte nicht geladen werden. Prüfe, ob ', ' auf deinem Computer verfügbar ist.', 'Das Video ist vorübergehend nicht verfügbar.'],
    fr: ['Impossible de charger la vidéo. Vérifiez que ', ' est disponible sur votre ordinateur.', 'La vidéo est temporairement indisponible.']
  };
  var statusCopy = copies[document.documentElement.lang] || copies.pl;

  function isReduced() {
    return !!(motion && motion.matches);
  }

  function clearRetries() {
    retryTimers.forEach(function (id) { window.clearTimeout(id); });
    retryTimers.length = 0;
  }

  function hideButton() {
    if (button) button.hidden = true;
  }

  function showButton() {
    if (button && !isReduced()) button.hidden = false;
  }

  function setStatus(message) {
    if (!status) return;
    status.textContent = message || '';
    status.hidden = !message;
  }

  function markPlaying() {
    clearRetries();
    hero.classList.add('is-video-playing');
    hero.classList.remove('is-video-unavailable');
    hideButton();
    setStatus('');
  }

  function markUnavailable() {
    clearRetries();
    hero.classList.remove('is-video-playing');
    hero.classList.add('is-video-unavailable');
    hideButton();
    setStatus(location.protocol === 'file:'
      ? statusCopy[0] + filePath + statusCopy[1]
      : statusCopy[2]);
  }

  function requestPlay() {
    if (document.hidden || isReduced()) {
      video.pause();
      hero.classList.remove('is-video-playing');
      hideButton();
      return;
    }

    video.muted = true;
    video.defaultMuted = true;

    var attempt;
    try {
      attempt = video.play();
    } catch (_) {
      showButton();
      return;
    }

    if (attempt && typeof attempt.then === 'function') {
      attempt.then(function () {
        if (!video.paused) markPlaying();
      }).catch(function (error) {
        if (document.hidden || isReduced()) return;
        if (video.error || (error && error.name === 'NotSupportedError')) {
          markUnavailable();
        } else {
          showButton();
        }
      });
    } else if (!video.paused) {
      markPlaying();
    }
  }

  function scheduleRecovery() {
    clearRetries();
    if (document.hidden || isReduced()) return;

    [0, 180, 700, 1600].forEach(function (delay) {
      retryTimers.push(window.setTimeout(function () {
        if (!video.paused || document.hidden || isReduced()) return;
        requestPlay();
      }, delay));
    });
  }

  video.muted = true;
  video.defaultMuted = true;
  video.autoplay = true;
  video.loop = true;
  video.playsInline = true;
  video.setAttribute('muted', '');
  video.setAttribute('playsinline', '');
  video.setAttribute('webkit-playsinline', '');

  video.addEventListener('playing', markPlaying);
  video.addEventListener('loadeddata', scheduleRecovery);
  video.addEventListener('canplay', scheduleRecovery);
  video.addEventListener('error', markUnavailable);
  video.addEventListener('stalled', function () {
    if (video.error) markUnavailable();
    else scheduleRecovery();
  });
  video.addEventListener('emptied', function () {
    hero.classList.remove('is-video-playing');
  });

  if (button) {
    button.addEventListener('click', function () {
      hero.classList.remove('is-video-unavailable');
      setStatus('');
      video.muted = true;
      if (video.error) video.load();
      requestPlay();
    });
  }

  if (motion) {
    if (motion.addEventListener) motion.addEventListener('change', scheduleRecovery);
    else if (motion.addListener) motion.addListener(scheduleRecovery);
  }

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) clearRetries();
    else scheduleRecovery();
  });
  window.addEventListener('pageshow', scheduleRecovery);
  window.addEventListener('focus', scheduleRecovery);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', scheduleRecovery, {once:true});
  } else {
    scheduleRecovery();
  }
})();
