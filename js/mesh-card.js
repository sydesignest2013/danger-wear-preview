(() => {
  const galleries = window.DW_GALLERIES || { lifestyle: [], realizacje: [] };
  const lifestyle = Array.isArray(galleries.lifestyle) ? galleries.lifestyle : [];
  const realizacje = Array.isArray(galleries.realizacje) ? galleries.realizacje : [];

  const hero = document.getElementById("lifestyleHero");
  const title = document.getElementById("lifestyleTitle");
  const subtitle = document.getElementById("lifestyleSubtitle");
  const fallbackSubtitle = subtitle?.textContent || "";
  const prevButton = document.getElementById("lifestylePrev");
  const nextButton = document.getElementById("lifestyleNext");
  const carouselArrowPrev = document.getElementById("carouselArrowPrev");
  const carouselArrowNext = document.getElementById("carouselArrowNext");
  const prevImage = document.getElementById("lifestylePrevImage");
  const nextImage = document.getElementById("lifestyleNextImage");
  const lifestyleStage = document.getElementById("lifestyleStage");
  const lifestyleDots = document.getElementById("lifestyleDots");
  const mainCard = hero?.closest(".main-card");
  const isMeshPage = document.body.classList.contains("sw-mesh-page");
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;

  let lifestyleIndex = 0;
  let lifestyleAnimating = false;
  let queuedLifestyle = null;

  function normalizeIndex(index, length) {
    if (!length) return 0;
    return (index + length) % length;
  }

  function renderLifestyleDots() {
    if (!lifestyleDots) return;
    if (lifestyle.length <= 1) {
      lifestyleDots.innerHTML = "";
      return;
    }
    const dotCount = Math.min(5, lifestyle.length);
    const activeDot = lifestyle.length <= dotCount
      ? lifestyleIndex
      : Math.round((lifestyleIndex / Math.max(1, lifestyle.length - 1)) * (dotCount - 1));
    lifestyleDots.innerHTML = Array.from({ length: dotCount }, (_, dotIndex) =>
      `<span class="mesh-carousel-dot${dotIndex === activeDot ? " is-active" : ""}"></span>`
    ).join("");
  }

  function renderLifestyle(index) {
    if (!lifestyle.length) {
      hero.removeAttribute("src");
      hero.alt = "Miejsce na zdjęcie lifestyle";
      prevImage?.removeAttribute("src");
      nextImage?.removeAttribute("src");
      lifestyleStage?.classList.add("is-empty-media");
      mainCard?.classList.add("is-empty-media");
      title.textContent = galleries.emptyLifestyleText || "MIEJSCE NA ZDJĘCIE — LIFESTYLE";
      if (subtitle) subtitle.textContent = "";
      [prevButton, nextButton, carouselArrowPrev, carouselArrowNext].forEach((button) => {
        if (button) button.hidden = true;
      });
      renderLifestyleDots();
      return;
    }

    lifestyleStage?.classList.remove("is-empty-media");
    mainCard?.classList.remove("is-empty-media");
    lifestyleIndex = normalizeIndex(index, lifestyle.length);
    const current = lifestyle[lifestyleIndex];
    const prev = lifestyle[normalizeIndex(lifestyleIndex - 1, lifestyle.length)];
    const next = lifestyle[normalizeIndex(lifestyleIndex + 1, lifestyle.length)];

    hero.src = current.src;
    hero.alt = current.title || "Zdjęcie lifestyle";
    title.textContent = current.title || "LIFESTYLE";
    if (subtitle) subtitle.textContent = current.subtitle || fallbackSubtitle;

    prevImage.src = prev.src;
    prevImage.alt = prev.title || "";
    nextImage.src = next.src;
    nextImage.alt = next.title || "";

    const multiple = lifestyle.length > 1;
    prevButton.hidden = !multiple;
    nextButton.hidden = !multiple;
    if (carouselArrowPrev) carouselArrowPrev.hidden = !multiple;
    if (carouselArrowNext) carouselArrowNext.hidden = !multiple;
    renderLifestyleDots();
  }

  function finishQueuedLifestyle() {
    lifestyleAnimating = false;
    if (!queuedLifestyle) return;
    const queued = queuedLifestyle;
    queuedLifestyle = null;
    setLifestyle(queued.index, queued.direction);
  }

  function setLifestyle(index, direction = 0, animate = true) {
    if (!lifestyle.length) {
      renderLifestyle(index);
      return;
    }

    const target = normalizeIndex(index, lifestyle.length);
    if (target === lifestyleIndex && hero?.getAttribute("src")) return;

    const resolvedDirection = direction || (target > lifestyleIndex ? 1 : -1);
    const use3D = isMeshPage && lifestyleStage && animate && lifestyle.length > 1;

    if (!use3D) {
      renderLifestyle(target);
      return;
    }

    if (lifestyleAnimating) {
      queuedLifestyle = { index: target, direction: resolvedDirection };
      return;
    }

    lifestyleAnimating = true;
    const slideClass = resolvedDirection < 0 ? "mesh-slide-prev" : "mesh-slide-next";
    lifestyleStage.classList.remove("mesh-slide-next", "mesh-slide-prev", "mesh-resetting");
    lifestyleStage.classList.add(slideClass);

    window.setTimeout(() => {
      /* Reset bez animacji jest wykonywany w jednej klatce, więc użytkownik widzi
         płynne przejście fizycznych kart, a nie podmianę zdjęcia w połowie ruchu. */
      lifestyleStage.classList.add("mesh-resetting");
      renderLifestyle(target);
      lifestyleStage.classList.remove(slideClass);

      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          lifestyleStage.classList.remove("mesh-resetting");
          finishQueuedLifestyle();
        });
      });
    }, 980);
  }

  function goLifestyle(delta) {
    setLifestyle(lifestyleIndex + delta, delta > 0 ? 1 : -1);
  }

  prevButton?.addEventListener("click", () => goLifestyle(-1));
  nextButton?.addEventListener("click", () => goLifestyle(1));
  carouselArrowPrev?.addEventListener("click", () => goLifestyle(-1));
  carouselArrowNext?.addEventListener("click", () => goLifestyle(1));
  renderLifestyle(0);

  /* === AUTOPLAY LIFESTYLE 5S === */
  const AUTOPLAY_DELAY = 5000;
  let lifestyleAutoplayTimer = null;

  function startLifestyleAutoplay() {
    stopLifestyleAutoplay();
    if (lifestyle.length <= 1) return;
    lifestyleAutoplayTimer = window.setInterval(() => {
      goLifestyle(1);
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

  function buildAssetCandidates(src) {
    const base = String(src || "").trim();
    const candidates = [];
    const push = (value) => {
      const normalized = String(value || "").trim();
      if (normalized && !candidates.includes(normalized)) candidates.push(normalized);
    };
    push(base);
    const filename = base.split("/").pop();
    if (filename && filename !== base) push(filename);
    if (filename) {
      push(`Realizacje/${filename}`);
      push(`Lifestyle/${filename}`);
      push(`images/${filename}`);
      push(`assets/${filename}`);
    }
    return candidates;
  }

  function attachFallbackSource(img, src) {
    const candidates = buildAssetCandidates(src);
    let currentIndex = 0;
    const apply = () => {
      img.src = candidates[currentIndex] || "";
    };
    const handleError = () => {
      currentIndex += 1;
      if (currentIndex < candidates.length) {
        apply();
      } else {
        img.removeEventListener("error", handleError);
      }
    };
    img.addEventListener("error", handleError);
    apply();
  }


  function renderRealizations() {
    if (!track) return;
    track.innerHTML = "";

    if (!realizacje.length) {
      const empty = document.createElement("div");
      empty.className = "empty-gallery";
      empty.textContent = galleries.emptyRealizationsText || "MIEJSCE NA ZDJĘCIA — REALIZACJE";
      track.appendChild(empty);
      return;
    }

    realizacje.forEach((item, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "realization-thumb";
      button.setAttribute("aria-label", `Powiększ: ${item.title || "realizacja"}`);
      const img = document.createElement("img");
      img.alt = escapeHtml(item.title || "Realizacja");
      img.loading = "lazy";
      attachFallbackSource(img, item.src);
      const label = document.createElement("span");
      label.textContent = item.title || "REALIZACJA";
      button.appendChild(img);
      button.appendChild(label);
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
    lightboxImage.alt = item.title || "Powiększona realizacja";
    attachFallbackSource(lightboxImage, item.src);
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

  // UNIFIED FW/SW REFERENCE CHROME 2026-09-16
  const fwPage = document.body.classList.contains("fw-reference-page");
  const meshPage = isMeshPage;
  if (fwPage && !meshPage) {
    const card = document.querySelector(".fw-lifestyle .main-card");
    const info = document.querySelector(".fw-info");
    const heading = info?.querySelector("h1");
    const captionWrap = card?.querySelector(".caption > div");

    if (card && !card.querySelector(".fw-ref-brand")) {
      const brand = document.createElement("div");
      brand.className = "fw-ref-brand";
      brand.innerHTML = "<strong>DANGER WEAR</strong><span>PRODUCTION</span>";
      card.appendChild(brand);
    }

    if (captionWrap && heading && !captionWrap.querySelector(".fw-ref-product-title")) {
      const productTitle = document.createElement("strong");
      productTitle.className = "fw-ref-product-title";
      productTitle.textContent = heading.textContent.trim();
      captionWrap.prepend(productTitle);
    }

    if (info && !info.querySelector(".fw-ref-actions")) {
      const isSportswear = document.body.classList.contains("sw-reference-page");
      const file = window.location.pathname.split("/").pop() || "produkt.html";
      const slug = file.replace(/\.html$/i, "");
      const actions = document.createElement("div");
      actions.className = "fw-ref-actions";
      actions.innerHTML = '<a class="fw-ref-primary" href="kontakt.html?produkt=' + encodeURIComponent(slug) + '">ZAPYTAJ O PRODUKCJĘ <span aria-hidden="true">→</span></a>' +
        '<a class="fw-ref-secondary" href="fightwear.html#' + (isSportswear ? 'sportswear' : 'fightwear') + '">WRÓĆ DO ' + (isSportswear ? 'SPORTSWEAR' : 'FIGHTWEAR') + '</a>';
      info.appendChild(actions);
    }
  }

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

  addSwipe(lifestyleStage, () => { goLifestyle(1); restartLifestyleAutoplay(); }, () => { goLifestyle(-1); restartLifestyleAutoplay(); });
  addSwipe(lightbox, () => setLightbox(realizationIndex + 1), () => setLightbox(realizationIndex - 1));

  // PRODUCT TITLE GLITCH TEXT — VIDEO REFERENCE 2026-09-17
  document.querySelectorAll(".mesh-ref-info h1, .mesh-mobile-heading h1").forEach((title) => {
    title.dataset.glitchText = title.textContent.trim();
  });
})();
