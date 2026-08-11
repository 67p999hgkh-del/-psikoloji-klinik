document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-search-input]').forEach(initSearchAutocomplete);
  document.querySelectorAll('[data-appointment-search-form]').forEach(initAppointmentTypeToggle);
});

function initAppointmentTypeToggle(form) {
  const toggle = form.querySelector('[data-appointment-type-toggle]');
  const input = form.querySelector('[data-session-type-input]');
  const cityField = form.querySelector('[data-city-field]');
  const citySelect = cityField?.querySelector('select') || (cityField?.tagName === 'SELECT' ? cityField : null);
  const copyWrap = form.closest('[data-appointment-search-copy]');
  const subtitle = copyWrap?.querySelector('[data-appointment-sub]');
  const buttons = toggle?.querySelectorAll('[data-session-type]');
  if (!toggle || !input || !buttons?.length) return;

  const applyMode = (sessionType) => {
    const isOnline = sessionType === 'online';
    input.value = sessionType;
    form.classList.toggle('is-online', isOnline);
    copyWrap?.classList.toggle('is-online-mode', isOnline);

    buttons.forEach((button) => {
      const active = button.dataset.sessionType === sessionType;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', active ? 'true' : 'false');
    });

    if (citySelect) {
      if (isOnline) {
        citySelect.value = '';
        citySelect.disabled = true;
      } else {
        citySelect.disabled = false;
      }
    }

    if (subtitle) {
      subtitle.textContent = isOnline
        ? subtitle.dataset.subOnline || subtitle.textContent
        : subtitle.dataset.subInperson || subtitle.textContent;
    }
  };

  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      applyMode(button.dataset.sessionType || 'yuz_yuze');
    });
  });

  form.addEventListener('submit', () => {
    if (input.value === 'online' && citySelect) {
      citySelect.value = '';
      citySelect.disabled = false;
    }
  });

  applyMode(normalizeSessionType(input.value));
}

function normalizeSessionType(value) {
  return value === 'online' ? 'online' : 'yuz_yuze';
}

function initSearchAutocomplete(input) {
  const wrap = input.closest('.search-autocomplete-wrap');
  const list = wrap?.querySelector('[data-search-suggestions]');
  const form = input.closest('[data-search-form]');
  if (!list) return;

  let timer = null;
  let items = [];
  let activeIndex = -1;

  const hide = () => {
    list.hidden = true;
    activeIndex = -1;
  };

  const render = () => {
    list.innerHTML = '';
    if (!items.length) {
      hide();
      return;
    }
    items.forEach((item, i) => {
      const li = document.createElement('li');
      li.className = 'search-suggestion-item';
      if (i === activeIndex) li.classList.add('active');
      li.innerHTML = `
        <span class="search-suggestion-label">${escapeHtml(item.label)}</span>
        <span class="search-suggestion-meta">${escapeHtml(item.meta || '')}</span>
      `;
      li.addEventListener('mousedown', (e) => {
        e.preventDefault();
        selectItem(item);
      });
      list.appendChild(li);
    });
    list.hidden = false;
  };

  const selectItem = (item) => {
    if (item.type === 'therapist' && item.url) {
      window.location.href = item.url;
      return;
    }
    input.value = item.label;
    hide();
    form?.submit();
  };

  const fetchSuggestions = async (q) => {
    const res = await fetch(`/api/terapist-ara?q=${encodeURIComponent(q)}`);
    if (!res.ok) return [];
    return res.json();
  };

  input.addEventListener('input', () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (q.length < 2) {
      items = [];
      hide();
      return;
    }
    timer = setTimeout(async () => {
      items = await fetchSuggestions(q);
      activeIndex = -1;
      render();
    }, 220);
  });

  input.addEventListener('keydown', (e) => {
    if (list.hidden || !items.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, items.length - 1);
      render();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, 0);
      render();
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      selectItem(items[activeIndex]);
    } else if (e.key === 'Escape') {
      hide();
    }
  });

  input.addEventListener('blur', () => setTimeout(hide, 150));
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
