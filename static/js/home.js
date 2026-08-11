document.addEventListener('DOMContentLoaded', () => {
  initInfoCarousel();
  initBlogCarousel();
  initTestsCarousel();
  initTherapistCarousel();
});

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

  const getStep = () => {
    const slide = slides[0];
    const gap = parseFloat(getComputedStyle(track).gap) || 20;
    return slide.offsetWidth + gap;
  };

  const getVisibleCount = () => {
    if (window.innerWidth < 640) return 1;
    if (window.innerWidth < 960) return 2;
    return 3;
  };

  const maxIndex = () => Math.max(0, slides.length - getVisibleCount());

  const scrollToIndex = (nextIndex, smooth = true) => {
    index = Math.max(0, Math.min(nextIndex, maxIndex()));
    viewport.scrollTo({
      left: index * getStep(),
      behavior: smooth ? 'smooth' : 'auto',
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
    if (slides.length <= getVisibleCount()) return;
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
    index = Math.round(viewport.scrollLeft / step);
    updateDots();
    updateButtons();
  }, { passive: true });

  root.addEventListener('mouseenter', stopAuto);
  root.addEventListener('mouseleave', startAuto);

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

  slides.forEach((_, i) => {
    const dot = document.createElement('button');
    dot.type = 'button';
    dot.className = i === 0 ? 'active' : '';
    dot.setAttribute('aria-label', `Bilgi ${i + 1}`);
    dot.addEventListener('click', () => {
      index = i;
      render();
    });
    dotsWrap.appendChild(dot);
  });

  const render = () => {
    track.style.transform = `translateX(-${index * 100}%)`;
    dotsWrap.querySelectorAll('button').forEach((dot, i) => {
      dot.classList.toggle('active', i === index);
    });
  };

  setInterval(() => {
    index = (index + 1) % slides.length;
    render();
  }, 6000);
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

  const isMobile = () => window.innerWidth <= 640;

  const getStep = () => {
    const slide = slides[0];
    const track = viewport.querySelector('.therapists-carousel-track');
    const gap = track ? parseFloat(getComputedStyle(track).gap) || 16 : 16;
    return slide.offsetWidth + gap;
  };

  const maxIndex = () => Math.max(0, slides.length - 1);

  const scrollToIndex = (nextIndex, smooth = true) => {
    if (!isMobile()) return;
    index = Math.max(0, Math.min(nextIndex, maxIndex()));
    viewport.scrollTo({
      left: index * getStep(),
      behavior: smooth ? 'smooth' : 'auto',
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
    if (!isMobile() || slides.length <= 1) return;
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
    index = Math.round(viewport.scrollLeft / step);
    updateDots();
  }, { passive: true });

  root.addEventListener('mouseenter', stopAuto);
  root.addEventListener('mouseleave', startAuto);
  root.addEventListener('touchstart', stopAuto, { passive: true });
  root.addEventListener('touchend', () => {
    setTimeout(startAuto, 3000);
  }, { passive: true });

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
