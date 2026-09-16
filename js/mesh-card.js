(() => {
  const galleries = window.DW_GALLERIES || { lifestyle: [], realizacje: [] };
  const lifestyle = Array.isArray(galleries.lifestyle) ? galleries.lifestyle : [];
  const realizacje = Array.isArray(galleries.realizacje) ? galleries.realizacje : [];

  const hero = document.getElementById("lifestyleHero");
  const title = document.getElementById("lifestyleTitle");
  const prevButton = document.getElementById("lifestylePrev");
  const nextButton = document.getElementById("lifestyleNext");
  const carouselArrowPrev = document.getElementById("carouselArrowPrev");
  const carouselArrowNext = document.getElementById("carouselArrowNext");
  const prevImage = document.getElementById("lifestylePrevImage");
  const nextImage = document.getElementById("lifestyleNextImage");

  let lifestyleIndex = 0;

  function normalizeIndex(index, length) {
    if (!length) return 0;
    return (index + length) % length;
  }

  function setLifestyle(index) {
    if (!lifestyle.length) {
      hero.removeAttribute("src");
      hero.alt = "Brak zdjęć w folderze Lifestyle";
      title.textContent = "DODAJ ZDJĘCIA DO FOLDERU LIFESTYLE";
      prevButton.hidden = true;
      nextButton.hidden = true;
      return;
    }

    lifestyleIndex = normalizeIndex(index, lifestyle.length);
    const current = lifestyle[lifestyleIndex];
    const prev = lifestyle[normalizeIndex(lifestyleIndex - 1, lifestyle.length)];
    const next = lifestyle[normalizeIndex(lifestyleIndex + 1, lifestyle.length)];

    hero.src = current.src;
    hero.alt = current.title || "Zdjęcie lifestyle";
    title.textContent = current.title || "LIFESTYLE";

    prevImage.src = prev.src;
    prevImage.alt = prev.title || "";
    nextImage.src = next.src;
    nextImage.alt = next.title || "";

    const multiple = lifestyle.length > 1;
    prevButton.hidden = !multiple;
    nextButton.hidden = !multiple;
  }

  prevButton?.addEventListener("click", () => setLifestyle(lifestyleIndex - 1));
  nextButton?.addEventListener("click", () => setLifestyle(lifestyleIndex + 1));
  carouselArrowPrev?.addEventListener("click", () => setLifestyle(lifestyleIndex - 1));
  carouselArrowNext?.addEventListener("click", () => setLifestyle(lifestyleIndex + 1));
  setLifestyle(0);

  /* === AUTOPLAY LIFESTYLE 5S === */
  const AUTOPLAY_DELAY = 5000;
  let lifestyleAutoplayTimer = null;

  function startLifestyleAutoplay() {
    stopLifestyleAutoplay();
    if (lifestyle.length <= 1) return;
    lifestyleAutoplayTimer = window.setInterval(() => {
      setLifestyle(lifestyleIndex + 1);
    }, AUTOPLAY_DELAY);
  }

  function stopLifestyleAutoplay() {
    if (lifestyleAutoplayTimer) {
      window.clearInterval(lifestyleAutoplayTimer);
      lifestyleAutoplayTimer = null;
    }
  }

  function restartLifestyleAutoplay() {
    stopLifestyleAutoplay();
    startLifestyleAutoplay();
  }

  carouselArrowPrev?.addEventListener("click", restartLifestyleAutoplay);
  carouselArrowNext?.addEventListener("click", restartLifestyleAutoplay);
  prevButton?.addEventListener("click", restartLifestyleAutoplay);
  nextButton?.addEventListener("click", restartLifestyleAutoplay);

  const lifestyleStage = document.getElementById("lifestyleStage");
  lifestyleStage?.addEventListener("mouseenter", stopLifestyleAutoplay);
  lifestyleStage?.addEventListener("mouseleave", startLifestyleAutoplay);
  lifestyleStage?.addEventListener("focusin", stopLifestyleAutoplay);
  lifestyleStage?.addEventListener("focusout", startLifestyleAutoplay);

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stopLifestyleAutoplay();
    else startLifestyleAutoplay();
  });

  startLifestyleAutoplay();
  /* === KONIEC AUTOPLAY LIFESTYLE === */


  const track = document.getElementById("realizationsTrack");
  const lightbox = document.getElementById("realizationLightbox");
  const lightboxImage = document.getElementById("lightboxImage");
  const lightboxCaption = document.getElementById("lightboxCaption");
  const lightboxPrev = document.getElementById("lightboxPrev");
  const lightboxNext = document.getElementById("lightboxNext");
  let realizationIndex = 0;

  function renderRealizations() {
    if (!track) return;
    track.innerHTML = "";

    if (!realizacje.length) {
      const empty = document.createElement("div");
      empty.className = "empty-gallery";
      empty.textContent = "Dodaj pliki do folderu Realizacje i uruchom ODSWIEZ_GALERIE.bat.";
      track.appendChild(empty);
      return;
    }

    realizacje.forEach((item, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "realization-thumb";
      button.setAttribute("aria-label", `Powiększ: ${item.title || "realizacja"}`);
      button.innerHTML = `<img src="${item.src}" alt="${escapeHtml(item.title || "Realizacja")}" loading="lazy"><span>${escapeHtml(item.title || "REALIZACJA")}</span>`;
      button.addEventListener("click", () => openLightbox(index));
      track.appendChild(button);
    });
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function setLightbox(index) {
    if (!realizacje.length) return;
    realizationIndex = normalizeIndex(index, realizacje.length);
    const item = realizacje[realizationIndex];
    lightboxImage.src = item.src;
    lightboxImage.alt = item.title || "Powiększona realizacja";
    lightboxCaption.textContent = item.title || "REALIZACJA";
    const multiple = realizacje.length > 1;
    lightboxPrev.hidden = !multiple;
    lightboxNext.hidden = !multiple;
  }

  function openLightbox(index) {
    if (!realizacje.length) return;
    setLightbox(index);
    lightbox.classList.add("open");
    lightbox.setAttribute("aria-hidden", "false");
    document.body.classList.add("lightbox-open");
    requestAnimationFrame(() => document.querySelector(".lightbox-close")?.focus());
  }

  function closeLightbox() {
    lightbox.classList.remove("open");
    lightbox.setAttribute("aria-hidden", "true");
    document.body.classList.remove("lightbox-open");
  }

  lightboxPrev?.addEventListener("click", () => setLightbox(realizationIndex - 1));
  lightboxNext?.addEventListener("click", () => setLightbox(realizationIndex + 1));
  document.querySelectorAll("[data-lightbox-close]").forEach((node) => {
    node.addEventListener("click", closeLightbox);
  });

  document.addEventListener("keydown", (event) => {
    if (!lightbox?.classList.contains("open")) return;
    if (event.key === "Escape") closeLightbox();
    if (event.key === "ArrowLeft") setLightbox(realizationIndex - 1);
    if (event.key === "ArrowRight") setLightbox(realizationIndex + 1);
  });

  renderRealizations();

  document.querySelectorAll("details").forEach((details) => {
    details.addEventListener("toggle", () => {
      if (!details.open) return;
      document.querySelectorAll("details").forEach((other) => {
        if (other !== details) other.open = false;
      });
    });
  });

  const panel = document.getElementById("mobPanel");
  const burger = document.getElementById("burger");
  const close = document.getElementById("mobClose");

  function openMobilePanel() {
    panel?.classList.add("open");
    panel?.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    close?.focus();
  }

  function closeMobilePanel() {
    panel?.classList.remove("open");
    panel?.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    burger?.focus();
  }

  burger?.addEventListener("click", openMobilePanel);
  close?.addEventListener("click", closeMobilePanel);
  panel?.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMobilePanel));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && panel?.classList.contains("open")) closeMobilePanel();
  });

  // Touch navigation for mobile: swipe the lifestyle carousel and realization lightbox.
  function addSwipe(target, onLeft, onRight) {
    if (!target) return;
    let startX = 0;
    let startY = 0;
    target.addEventListener("touchstart", (event) => {
      const touch = event.changedTouches[0];
      startX = touch.clientX;
      startY = touch.clientY;
    }, { passive: true });
    target.addEventListener("touchend", (event) => {
      const touch = event.changedTouches[0];
      const dx = touch.clientX - startX;
      const dy = touch.clientY - startY;
      if (Math.abs(dx) < 48 || Math.abs(dx) < Math.abs(dy) * 1.15) return;
      if (dx < 0) onLeft(); else onRight();
    }, { passive: true });
  }

  addSwipe(lifestyleStage, () => { setLifestyle(lifestyleIndex + 1); restartLifestyleAutoplay(); }, () => { setLifestyle(lifestyleIndex - 1); restartLifestyleAutoplay(); });
  addSwipe(lightbox, () => setLightbox(realizationIndex + 1), () => setLightbox(realizationIndex - 1));
})();
