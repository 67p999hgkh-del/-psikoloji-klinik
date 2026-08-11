document.addEventListener('DOMContentLoaded', () => {
  initInfoCarousel();
  initBlogCarousel();
  initTestsCarousel();
  initTherapistCarousel();
});

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function initHorizontalCarousel(root, options = {}) {
  if (!root) return;

  const viewport = root.querySelector(options.viewportSelector);
  const track = root.querySelector(options.trackSelector);
  const slides = root.querySelectorAll(options.slideSelector);
  const prevBtn = root.querySelector(options.prevSelector);
  const nextBtn = root.querySelector(options.nextSelector);
  const dotsWrap = root.querySelector(options.dotsSelector);
  if (!viewport || !track || slides.length === 0) return;

  let index = 0;
  let autoTimer = null;
  const interval = options.interval || 5000;
  const reduceMotion = prefersReducedMotion();

  const getStep = () => {
    const slide = slides[0];
    if (!slide) return 0;
    const gap = parseFloat(getComputedStyle(track).gap) || 20;
    const width = slide.getBoundingClientRect().width || slide.offsetWidth || 0;
    return width > 0 ? width + gap : 0;
  };

  const getVisibleCount = () => {
    if (window.innerWidth < 640) return 1;
    if (window.innerWidth < 960) return 2;
    return 3;
  };

  const maxIndex = () => Math.max(0, slides.length - getVisibleCount());

  const scrollToIndex = (nextIndex, smooth = true) => {
    const step = getStep();
    if (!step) return;
    index = Math.max(0, Math.min(nextIndex, maxIndex()));
    viewport.scrollTo({
      left: index * step,
      behavior: smooth && !reduceMotion ? 'smooth' : 'auto',
    });
    updateDots();
    updateButtons();
  };

  const updateDots = () => {
    if (!dotsWrap) return;
    dotsWrap.querySelectorAll('button').forEach((dot, i) => {
      dot.classList.toggle('active', i === index);
    });
  };

  const updateButtons = () => {
    if (prevBtn) prevBtn.disabled = index <= 0;
    if (nextBtn) nextBtn.disabled = index >= maxIndex();
  };

  const buildDots = () => {
    if (!dotsWrap || slides.length <= getVisibleCount()) {
      if (dotsWrap) dotsWrap.innerHTML = '';
      return;
    }
    dotsWrap.innerHTML = '';
    for (let i = 0; i <= maxIndex(); i += 1) {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.className = i === 0 ? 'active' : '';
      dot.setAttribute('aria-label', `${options.dotLabel || 'Slide'} ${i + 1}`);
      dot.addEventListener('click', () => scrollToIndex(i));
      dotsWrap.appendChild(dot);
    }
  };

  const startAuto = () => {
    stopAuto();
    if (reduceMotion || slides.length <= getVisibleCount()) return;
    autoTimer = setInterval(() => {
      const next = index >= maxIndex() ? 0 : index + 1;
      scrollToIndex(next);
    }, interval);
  };

  const stopAuto = () => {
    if (autoTimer) clearInterval(autoTimer);
    autoTimer = null;
  };

  prevBtn?.addEventListener('click', () => {
    stopAuto();
    scrollToIndex(index - 1);
    startAuto();
  });

  nextBtn?.addEventListener('click', () => {
    stopAuto();
    scrollToIndex(index + 1);
    startAuto();
  });

  viewport.addEventListener('scroll', () => {
    const step = getStep();
    if (!step) return;
    const next = Math.round(viewport.scrollLeft / step);
    if (next === index) return;
    index = Math.max(0, Math.min(next, maxIndex()));
    updateDots();
    updateButtons();
  }, { passive: true });

  root.addEventListener('mouseenter', stopAuto);
  root.addEventListener('mouseleave', startAuto);
  root.addEventListener('touchstart', stopAuto, { passive: true });
  root.addEventListener('touchend', () => {
    setTimeout(startAuto, 2500);
  }, { passive: true });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stopAuto();
    else startAuto();
  });

  window.addEventListener('resize', () => {
    buildDots();
    scrollToIndex(Math.min(index, maxIndex()), false);
    updateButtons();
  });

  buildDots();
  updateButtons();
  startAuto();
}

function initTestsCarousel() {
  initHorizontalCarousel(document.querySelector('[data-tests-carousel]'), {
    viewportSelector: '[data-tests-viewport]',
    trackSelector: '.tests-carousel-track',
    slideSelector: '.tests-carousel-slide',
    prevSelector: '[data-tests-prev]',
    nextSelector: '[data-tests-next]',
    dotsSelector: '[data-tests-dots]',
    dotLabel: 'Test',
    interval: 4500,
  });
}

function initInfoCarousel() {
  const panel = document.querySelector('[data-info-carousel]');
  if (!panel) return;

  const track = panel.querySelector('.info-carousel-track');
  const slides = panel.querySelectorAll('.info-slide');
  const dotsWrap = panel.querySelector('[data-info-dots]');
  if (!track || slides.length <= 1 || !dotsWrap) return;

  let index = 0;
  let timer = null;
  const reduceMotion = prefersReducedMotion();

  slides.forEach((_, i) => {
    const dot = document.createElement('button');
    dot.type = 'button';
    dot.className = i === 0 ? 'active' : '';
    dot.setAttribute('aria-label', `Bilgi ${i + 1}`);
    dot.addEventListener('click', () => {
      index = i;
      render();
      restart();
    });
    dotsWrap.appendChild(dot);
  });

  const render = () => {
    track.style.transition = reduceMotion ? 'none' : 'transform 0.5s ease';
    track.style.transform = `translateX(-${index * 100}%)`;
    dotsWrap.querySelectorAll('button').forEach((dot, i) => {
      dot.classList.toggle('active', i === index);
    });
  };

  const stop = () => {
    if (timer) clearInterval(timer);
    timer = null;
  };

  const start = () => {
    stop();
    if (reduceMotion) return;
    timer = setInterval(() => {
      index = (index + 1) % slides.length;
      render();
    }, 6000);
  };

  const restart = () => start();

  panel.addEventListener('mouseenter', stop);
  panel.addEventListener('mouseleave', start);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stop();
    else start();
  });

  render();
  start();
}

function initBlogCarousel() {
  initHorizontalCarousel(document.querySelector('[data-blog-carousel]'), {
    viewportSelector: '[data-blog-viewport]',
    trackSelector: '.blog-carousel-track',
    slideSelector: '.blog-carousel-slide',
    prevSelector: '[data-blog-prev]',
    nextSelector: '[data-blog-next]',
    dotsSelector: '[data-blog-dots]',
    dotLabel: 'Yazı',
    interval: 5000,
  });
}

function initTherapistCarousel() {
  const root = document.querySelector('[data-therapist-carousel]');
  if (!root) return;

  const viewport = root.querySelector('[data-therapist-viewport]');
  const slides = root.querySelectorAll('.therapist-carousel-slide');
  const dotsWrap = root.querySelector('[data-therapist-dots]');
  if (!viewport || slides.length === 0) return;

  let index = 0;
  let autoTimer = null;
  const reduceMotion = prefersReducedMotion();

  const isMobile = () => window.innerWidth <= 640;

  const getStep = () => {
    const slide = slides[0];
    if (!slide) return 0;
    const track = viewport.querySelector('.therapists-carousel-track');
    const gap = track ? parseFloat(getComputedStyle(track).gap) || 16 : 16;
    const width = slide.getBoundingClientRect().width || slide.offsetWidth || 0;
    return width > 0 ? width + gap : 0;
  };

  const maxIndex = () => Math.max(0, slides.length - 1);

  const scrollToIndex = (nextIndex, smooth = true) => {
    if (!isMobile()) return;
    const step = getStep();
    if (!step) return;
    index = Math.max(0, Math.min(nextIndex, maxIndex()));
    viewport.scrollTo({
      left: index * step,
      behavior: smooth && !reduceMotion ? 'smooth' : 'auto',
    });
    updateDots();
  };

  const updateDots = () => {
    if (!dotsWrap) return;
    dotsWrap.querySelectorAll('button').forEach((dot, i) => {
      dot.classList.toggle('active', i === index);
    });
  };

  const buildDots = () => {
    if (!dotsWrap) return;
    dotsWrap.innerHTML = '';
    if (!isMobile() || slides.length <= 1) return;
    slides.forEach((_, i) => {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.className = i === 0 ? 'active' : '';
      dot.setAttribute('aria-label', `Terapist ${i + 1}`);
      dot.addEventListener('click', () => {
        stopAuto();
        scrollToIndex(i);
        startAuto();
      });
      dotsWrap.appendChild(dot);
    });
  };

  const startAuto = () => {
    stopAuto();
    if (reduceMotion || !isMobile() || slides.length <= 1) return;
    autoTimer = setInterval(() => {
      const next = index >= maxIndex() ? 0 : index + 1;
      scrollToIndex(next);
    }, 4500);
  };

  const stopAuto = () => {
    if (autoTimer) clearInterval(autoTimer);
    autoTimer = null;
  };

  viewport.addEventListener('scroll', () => {
    if (!isMobile()) return;
    const step = getStep();
    if (!step) return;
    const next = Math.round(viewport.scrollLeft / step);
    if (next === index) return;
    index = Math.max(0, Math.min(next, maxIndex()));
    updateDots();
  }, { passive: true });

  root.addEventListener('mouseenter', stopAuto);
  root.addEventListener('mouseleave', startAuto);
  root.addEventListener('touchstart', stopAuto, { passive: true });
  root.addEventListener('touchend', () => {
    setTimeout(startAuto, 3000);
  }, { passive: true });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stopAuto();
    else startAuto();
  });

  window.addEventListener('resize', () => {
    buildDots();
    if (!isMobile()) {
      stopAuto();
      viewport.scrollTo({ left: 0, behavior: 'auto' });
      index = 0;
      return;
    }
    scrollToIndex(Math.min(index, maxIndex()), false);
    startAuto();
  });

  buildDots();
  startAuto();
}
