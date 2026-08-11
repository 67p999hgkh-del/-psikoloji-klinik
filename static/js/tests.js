document.addEventListener('DOMContentLoaded', () => {
  initTestFilters();
  initTestProgress();
  initTestimonialsCarousel();
});

function initTestFilters() {
  const filters = document.querySelectorAll('.tests-filter[data-test-group]');
  const cards = document.querySelectorAll('.test-card-v2[data-test-group]');
  if (!filters.length || !cards.length) return;

  filters.forEach((button) => {
    button.addEventListener('click', () => {
      filters.forEach((item) => item.classList.remove('active'));
      button.classList.add('active');
      const group = button.dataset.testGroup;
      cards.forEach((card) => {
        const show = group === 'all' || card.dataset.testGroup === group;
        card.style.display = show ? '' : 'none';
      });
    });
  });
}

function initTestProgress() {
  const form = document.getElementById('test-form');
  if (!form) return;

  const fields = form.querySelectorAll('.test-question');
  const fill = document.getElementById('test-progress-fill');
  const text = document.getElementById('test-progress-text');
  const total = fields.length;

  const update = () => {
    let answered = 0;
    fields.forEach((field) => {
      if (field.querySelector('input:checked')) answered += 1;
    });
    const pct = total ? (answered / total) * 100 : 0;
    if (fill) fill.style.width = `${pct}%`;
    if (text) text.textContent = `${answered} / ${total}`;
  };

  form.querySelectorAll('input[type="radio"]').forEach((input) => {
    input.addEventListener('change', update);
  });
  update();
}

function initTestimonialsCarousel() {
  document.querySelectorAll('[data-testimonials-carousel]').forEach((carousel) => {
    const track = carousel.querySelector('.testimonials-track');
    const slides = carousel.querySelectorAll('.testimonial-slide');
    const dotsWrap = carousel.querySelector('[data-testimonials-dots]');
    if (!track || slides.length <= 1 || !dotsWrap) return;

    let index = 0;
    slides.forEach((_, i) => {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.className = i === 0 ? 'active' : '';
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
    }, 5000);
  });
}
