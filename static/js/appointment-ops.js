(function () {
  'use strict';

  const root = document.querySelector('.aoc-page');
  if (!root) return;

  const cfg = {
    bulkUrl: root.dataset.bulkUrl || '',
    sessionNewUrl: root.dataset.sessionNewUrl || '/admin/seans/yeni',
  };

  const drawer = document.getElementById('aocDrawer');
  const overlay = document.getElementById('aocDrawerOverlay');
  const body = document.getElementById('aocDrawerBody');
  const title = document.getElementById('aocDrawerTitle');
  const sub = document.getElementById('aocDrawerSub');
  const bulkBar = document.getElementById('aocBulkForm');
  const bulkCount = document.getElementById('aocBulkCount');
  const selectAll = document.getElementById('aocSelectAll');
  const aiPanel = document.getElementById('aocAiPanel');
  const aiOverlay = document.getElementById('aocAiOverlay');
  const aiResults = document.getElementById('aocAiResults');

  function esc(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function section(heading, html, badge) {
    return `<section class="drawer-section"><h3>${esc(heading)}${badge ? `<span class="drawer-count">${esc(badge)}</span>` : ''}</h3>${html}</section>`;
  }

  function aiSummaryLines(ai) {
    if (!ai) return [];
    if (Array.isArray(ai)) return ai.filter(Boolean);
    if (typeof ai === 'string') return [ai];
    const lines = [];
    if (ai.text) lines.push(ai.text);
    if (ai.headline) lines.push(ai.headline);
    (ai.bullets || []).forEach((b) => { if (b) lines.push(b); });
    return lines;
  }

  function renderDrawer(data) {
    title.textContent = data.client.name || 'Danışan';
    sub.textContent = `${data.appointment.date} ${data.appointment.time} · ${data.appointment.therapist}`;

    const links = data.links || {};
    const aiLines = aiSummaryLines(data.ai_summary).map((l) => `<li>${esc(l)}</li>`).join('');

    const client = section('Danışan Özeti', `
      <div class="aoc-drawer-summary">
        <div class="drawer-grid">
          <div><span>E-posta</span><strong>${esc(data.client.email)}</strong></div>
          <div><span>Telefon</span><strong>${esc(data.client.phone || '—')}</strong></div>
          <div><span>Üyelik</span><strong>${data.client.membership ? 'Aktif üye' : 'Misafir'}</strong></div>
          <div><span>Şube</span><strong>${esc(data.appointment.city || '—')}</strong></div>
        </div>
        <div class="drawer-badges" style="margin-top:0.65rem">
          <span class="aoc-badge aoc-badge-${esc(data.appointment.status_key)}">${esc(data.appointment.status)}</span>
          <span class="aoc-tag ${data.appointment.type === 'Online' ? 'aoc-tag-online' : 'aoc-tag-inperson'}">${esc(data.appointment.type)}</span>
        </div>
        ${data.appointment.notes ? `<p class="drawer-note" style="margin-top:0.65rem">${esc(data.appointment.notes)}</p>` : ''}
      </div>
    `);

    const lastSession = data.sessions.length
      ? `<div class="drawer-grid">
          <div><span>Tarih</span><strong>${esc(data.sessions[0].date)}</strong></div>
          <div><span>Durum</span><strong>${esc(data.sessions[0].status)}</strong></div>
          <div><span>Risk</span><strong>${esc(data.sessions[0].risk)}</strong></div>
          <div><span>Neden</span><strong>${esc(data.sessions[0].reasons)}</strong></div>
        </div>
        <p class="drawer-quick-links"><a href="${esc(data.sessions[0].href)}" class="btn btn-sm btn-outline">Seans workspace →</a></p>
        ${data.sessions.length > 1 ? `<ul class="drawer-list drawer-list-links">${data.sessions.slice(1, 5).map((s) => `<li><a href="${esc(s.href)}">${esc(s.date)}</a><span>${esc(s.status)}</span></li>`).join('')}</ul>` : ''}`
      : '<p class="drawer-empty">Seans kaydı yok.</p>';

    const therapyPlan = `<p class="drawer-note">${esc(data.therapy_plan || 'Terapi planı bulunmuyor.')}</p>`;

    const tests = data.tests.length
      ? `<ul class="drawer-list drawer-list-links">${data.tests.map((t) => `<li><a href="${esc(t.href || links.test || '#')}">${esc(t.title)}</a><strong>${esc(t.level)}</strong></li>`).join('')}</ul>
         <p class="drawer-quick-links"><a href="${esc(links.test || '#')}" class="btn btn-sm btn-outline">Test ata (seans)</a>
         <a href="${esc(links.tests_catalog || '/admin/testler')}" class="btn btn-sm btn-ghost">Test kataloğu</a></p>`
      : `<p class="drawer-empty">Test sonucu yok.</p>
         <p class="drawer-quick-links"><a href="${esc(links.test || '#')}" class="btn btn-sm btn-outline">Test ata</a></p>`;

    const docs = links.document
      ? `<a href="${esc(links.document)}" class="btn btn-sm btn-outline">Belgeler (seans workspace) →</a>`
      : '<p class="drawer-empty">Belgeler panelinden görüntüleyin.</p>';

    const payments = data.payments.length
      ? `<ul class="drawer-list">${data.payments.map((p) => `<li><span>${esc(p.date)}</span><strong>${esc(p.amount)}</strong><small>${esc(p.status)}</small></li>`).join('')}</ul>
         <p class="drawer-quick-links"><a href="${esc(links.invoice || '#')}" class="btn btn-sm btn-outline">Yeni fatura</a>
         <a href="${esc(links.invoices || '/admin/faturalar')}" class="btn btn-sm btn-ghost">Fatura listesi</a></p>`
      : `<p class="drawer-empty">Ödeme kaydı yok.</p>
         <p class="drawer-quick-links"><a href="${esc(links.invoice || '#')}" class="btn btn-sm btn-primary">Fatura oluştur</a></p>`;

    const messages = links.message
      ? `<a href="${esc(links.message)}" class="btn btn-sm btn-outline">Mesaj merkezine git →</a>`
      : '<p class="drawer-empty">Mesaj kaydı yok.</p>';

    const aiBlock = aiLines
      ? `<div class="aoc-drawer-ai"><ul style="margin:0;padding-left:1rem">${aiLines}</ul></div>`
      : '';

    const quick = `<div class="aoc-drawer-quick">
      <a href="${esc(links.session || cfg.sessionNewUrl + '?appointment_id=' + data.id)}" class="btn btn-sm btn-primary">Seans Aç</a>
      <a href="${esc(links.note || '#')}" class="btn btn-sm btn-outline">Seans Listesi</a>
      <a href="${esc(links.test || '#')}" class="btn btn-sm btn-outline">Test / Ödev</a>
      <a href="${esc(links.invoice || '#')}" class="btn btn-sm btn-outline">Fatura Oluştur</a>
      <a href="${esc(links.profile || '#')}" class="btn btn-sm btn-outline">Danışan Kaydı</a>
      ${data.client.phone ? `<a href="tel:${esc(data.client.phone)}" class="btn btn-sm btn-ghost">Ara</a>` : ''}
    </div>`;

    body.innerHTML = client
      + section('Son Seans', lastSession)
      + section('Terapi Planı', therapyPlan)
      + section('Test Sonuçları', tests, String(data.tests.length))
      + section('Belgeler', docs)
      + section('Ödeme Geçmişi', payments, String(data.payments.length))
      + section('Mesajlar', messages)
      + section('AI Özeti', aiBlock || '<p class="drawer-empty">Özet oluşturulamadı.</p>')
      + section('Hızlı İşlemler', quick);
  }

  function openDrawer(id) {
    if (!drawer || !overlay || !body) return;
    drawer.hidden = false;
    overlay.hidden = false;
    requestAnimationFrame(() => {
      drawer.classList.add('open');
      overlay.classList.add('open');
    });
    document.body.classList.add('drawer-open');
    body.innerHTML = '<div class="drawer-loading">Kayıt yükleniyor…</div>';
    fetch(`/admin/randevu/${id}/detay`, { headers: { 'X-Requested-With': 'fetch' }, credentials: 'same-origin' })
      .then((r) => {
        if (!r.ok) throw new Error(`http_${r.status}`);
        return r.json();
      })
      .then(renderDrawer)
      .catch(() => {
        body.innerHTML = '<p class="drawer-empty">Detay alınamadı. Oturumu yenileyip tekrar deneyin.</p>';
      });
  }

  function closeDrawer() {
    if (!drawer || !overlay) return;
    drawer.classList.remove('open');
    overlay.classList.remove('open');
    document.body.classList.remove('drawer-open');
    setTimeout(() => { drawer.hidden = true; overlay.hidden = true; }, 280);
  }

  document.querySelectorAll('[data-appointment-id]').forEach((el) => {
    if (el.closest('.aoc-menu-wrap, .aoc-td-check, .aoc-col-check, .aoc-actions, .aoc-quick-actions, .aoc-col-status')) return;
    const isScheduleEvent = el.classList.contains('aoc-schedule-event');
    el.addEventListener('click', (e) => {
      if (isScheduleEvent) {
        e.preventDefault();
        openDrawer(el.dataset.appointmentId);
        return;
      }
      if (e.target.closest('.aoc-actions, .aoc-td-check, .aoc-col-check, .aoc-menu-wrap, .aoc-quick-actions, .aoc-col-status, label, select, button, a')) return;
      openDrawer(el.dataset.appointmentId);
    });
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') openDrawer(el.dataset.appointmentId);
    });
  });

  document.getElementById('aocDrawerClose')?.addEventListener('click', closeDrawer);
  overlay?.addEventListener('click', closeDrawer);

  const primaryViews = new Set(['list', 'calendar', 'daily']);
  const secondaryViews = new Set(['timeline', 'kanban', 'weekly']);
  const moreViews = document.querySelector('.aoc-more-views');
  const moreSummary = moreViews?.querySelector('.aoc-tab-more');

  function closeMoreViews() {
    if (moreViews) moreViews.open = false;
  }

  function setActiveView(view) {
    document.querySelectorAll('.aoc-tab[data-view]').forEach((t) => {
      t.classList.toggle('is-active', t.dataset.view === view);
    });
    if (moreSummary) {
      moreSummary.classList.toggle('is-active', secondaryViews.has(view));
    }
    document.querySelectorAll('.aoc-view').forEach((p) => {
      p.classList.toggle('is-active', p.dataset.panel === view);
    });
    const url = new URL(window.location);
    if (view === 'list') url.searchParams.delete('view');
    else url.searchParams.set('view', view);
    window.history.replaceState({}, '', url);
    /* Always close after a view is chosen so the menu never overlays the board */
    closeMoreViews();
  }

  document.querySelectorAll('.aoc-tab[data-view]').forEach((tab) => {
    tab.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const view = tab.dataset.view;
      if (!view) return;
      setActiveView(view);
    });
  });

  /* Toggle summary still works via native <details>; outside click closes */
  document.addEventListener('click', (e) => {
    if (moreViews?.open && !e.target.closest('.aoc-more-views')) {
      closeMoreViews();
    }
  });

  /* Advanced filter toggle */
  const filterToggle = document.getElementById('aocFilterToggle');
  const filterAdvanced = document.getElementById('aocFilterAdvanced');
  filterToggle?.addEventListener('click', () => {
    if (!filterAdvanced) return;
    const willOpen = filterAdvanced.hasAttribute('hidden');
    if (willOpen) filterAdvanced.removeAttribute('hidden');
    else filterAdvanced.setAttribute('hidden', '');
    filterToggle.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
  });

  /* Date presets */
  const presetInput = document.getElementById('date_preset');
  const customDates = document.getElementById('aocCustomDates');
  const fromInput = document.getElementById('from');
  const toInput = document.getElementById('to');
  const filterForm = document.getElementById('aocFilterForm');

  function isoDate(d) {
    const p = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  }

  function setPresetActive(preset) {
    document.querySelectorAll('.aoc-date-preset').forEach((btn) => {
      btn.classList.toggle('is-active', btn.dataset.preset === preset);
    });
    if (presetInput) presetInput.value = preset;
  }

  function applyDatePreset(preset, submit) {
    const now = new Date();
    setPresetActive(preset);
    if (preset === 'custom') {
      customDates?.removeAttribute('hidden');
      return;
    }
    customDates?.setAttribute('hidden', '');
    let from = '';
    let to = '';
    if (preset === 'today') {
      from = to = isoDate(now);
    } else if (preset === 'week') {
      const day = now.getDay();
      const diff = day === 0 ? 6 : day - 1;
      const mon = new Date(now);
      mon.setDate(now.getDate() - diff);
      const sun = new Date(mon);
      sun.setDate(mon.getDate() + 6);
      from = isoDate(mon);
      to = isoDate(sun);
    } else if (preset === 'month') {
      from = isoDate(new Date(now.getFullYear(), now.getMonth(), 1));
      to = isoDate(now);
    }
    if (fromInput) fromInput.value = from;
    if (toInput) toInput.value = to;
    if (submit && filterForm) filterForm.submit();
  }

  document.querySelectorAll('.aoc-date-preset').forEach((btn) => {
    btn.addEventListener('click', () => {
      applyDatePreset(btn.dataset.preset, btn.dataset.preset !== 'custom');
    });
  });

  fromInput?.addEventListener('change', () => setPresetActive('custom'));
  toInput?.addEventListener('change', () => setPresetActive('custom'));

  /* Header overflow menu */
  const headerMenuBtn = document.getElementById('aocHeaderMenuBtn');
  const headerMenu = document.getElementById('aocHeaderMenu');

  function closeHeaderMenu() {
    if (!headerMenu || !headerMenuBtn) return;
    headerMenu.hidden = true;
    headerMenuBtn.setAttribute('aria-expanded', 'false');
  }

  function positionHeaderMenu() {
    if (!headerMenu || !headerMenuBtn) return;
    const rect = headerMenuBtn.getBoundingClientRect();
    headerMenu.hidden = false;
    const width = headerMenu.offsetWidth || 170;
    let left = rect.right - width;
    left = Math.max(8, Math.min(left, window.innerWidth - width - 8));
    headerMenu.style.top = `${rect.bottom + 4}px`;
    headerMenu.style.left = `${left}px`;
  }

  headerMenuBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (headerMenu?.hidden) positionHeaderMenu();
    else closeHeaderMenu();
  });

  headerMenu?.addEventListener('click', (e) => {
    if (e.target.closest('[role="menuitem"]')) closeHeaderMenu();
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.aoc-header-menu-wrap')) closeHeaderMenu();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (aiPanel?.classList.contains('is-open')) {
      setAiPanel(false);
      return;
    }
    if (drawer && !drawer.hidden) {
      closeDrawer();
      return;
    }
    if (moreViews?.open) {
      closeMoreViews();
      return;
    }
    if (headerMenu && !headerMenu.hidden) {
      closeHeaderMenu();
    }
  });

  /* Bulk selection */
  function updateBulk() {
    const checked = document.querySelectorAll('.aoc-row-check:checked');
    if (bulkCount) bulkCount.textContent = checked.length;
    if (bulkBar) bulkBar.hidden = checked.length === 0;
    const all = document.querySelectorAll('.aoc-row-check');
    const allChecked = all.length > 0 && checked.length === all.length;
    if (selectAll) selectAll.checked = allChecked;
    const top = document.getElementById('aocSelectAllTop');
    if (top) top.checked = allChecked;
  }

  function syncSelectAll(checked) {
    document.querySelectorAll('.aoc-row-check').forEach((cb) => { cb.checked = checked; });
    if (selectAll) selectAll.checked = checked;
    const top = document.getElementById('aocSelectAllTop');
    if (top) top.checked = checked;
    updateBulk();
  }

  document.querySelectorAll('.aoc-row-check').forEach((cb) => cb.addEventListener('change', updateBulk));
  selectAll?.addEventListener('change', () => syncSelectAll(selectAll.checked));
  document.getElementById('aocSelectAllTop')?.addEventListener('change', (e) => syncSelectAll(e.target.checked));

  document.querySelectorAll('[data-bulk]').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (!bulkBar) return;
      const action = btn.dataset.bulk;
      if (action === 'reschedule') {
        const d = prompt('Yeni tarih (YYYY-MM-DD):');
        if (!d) return;
        document.getElementById('aocBulkNewDate').value = d;
      }
      if (action === 'cancel' && !confirm('Seçili randevular iptal edilsin mi?')) return;
      document.getElementById('aocBulkAction').value = action;
      bulkBar.submit();
    });
  });

  /* Row menus */
  function closeMenus() {
    document.querySelectorAll('.aoc-menu-wrap.is-open').forEach((wrap) => {
      wrap.classList.remove('is-open');
      const menu = wrap.querySelector('.aoc-menu');
      if (menu) {
        menu.hidden = true;
        menu.style.top = '';
        menu.style.left = '';
      }
    });
  }

  function positionMenu(btn, menu) {
    const rect = btn.getBoundingClientRect();
    menu.hidden = false;
    const width = menu.offsetWidth || 160;
    let left = rect.right - width;
    left = Math.max(8, Math.min(left, window.innerWidth - width - 8));
    const top = Math.min(rect.bottom + 4, window.innerHeight - menu.offsetHeight - 8);
    menu.style.top = `${Math.max(8, top)}px`;
    menu.style.left = `${left}px`;
  }

  document.querySelectorAll('.aoc-menu-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const wrap = btn.closest('.aoc-menu-wrap');
      const menu = wrap?.querySelector('.aoc-menu');
      if (!wrap || !menu) return;
      const isOpen = wrap.classList.contains('is-open');
      closeMenus();
      if (!isOpen) {
        wrap.classList.add('is-open');
        positionMenu(btn, menu);
      }
    });
  });

  document.querySelectorAll('.js-aoc-reschedule').forEach((btn) => {
    btn.addEventListener('click', () => {
      closeMenus();
      const d = prompt('Yeni tarih (YYYY-MM-DD):');
      if (!d || !cfg.bulkUrl) return;
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = cfg.bulkUrl;
      form.innerHTML = `<input type="hidden" name="action" value="reschedule"><input type="hidden" name="new_date" value="${d}"><input type="hidden" name="ids" value="${btn.dataset.id}">`;
      document.body.appendChild(form);
      form.submit();
    });
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.aoc-menu-wrap')) closeMenus();
  });
  window.addEventListener('resize', closeMenus);
  window.addEventListener('scroll', closeMenus, { passive: true, capture: true });

  /* AI panel */
  function setAiPanel(open) {
    aiPanel?.classList.toggle('is-open', open);
    aiOverlay?.classList.toggle('is-open', open);
    document.getElementById('aocAiToggle')?.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (!open && aiResults) aiResults.hidden = true;
  }

  document.getElementById('aocAiToggle')?.addEventListener('click', (e) => {
    e.preventDefault();
    setAiPanel(!aiPanel?.classList.contains('is-open'));
  });
  document.getElementById('aocAiClose')?.addEventListener('click', () => setAiPanel(false));
  aiOverlay?.addEventListener('click', () => setAiPanel(false));

  const aiData = (() => {
    try {
      return JSON.parse(document.getElementById('aocAiData')?.textContent || '{}');
    } catch {
      return {};
    }
  })();

  document.querySelectorAll('.aoc-ai-feature').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (!aiResults) return;
      const key = btn.dataset.aiKey;
      const map = {
        load: { title: 'Bugünkü yoğunluk', items: (aiData.therapist_load || []).map((t) => `${t.name}: ${t.count} randevu`) },
        slots: { title: 'Boş saat önerileri', items: ['10:00–11:00 arası boş slot', '14:30–15:30 arası boş slot', '16:00 sonrası uygun'] },
        cancel_risk: { title: 'İptal riski yüksek', items: aiData.repeat_cancel || [] },
        noshow: { title: 'Gelmeyen danışan analizi', items: aiData.noshow_risk || [] },
        followup: { title: 'Takip gereken danışanlar', items: aiData.reminders_due || [] },
        session_tips: { title: 'Seans önerileri', items: (aiData.first_time || []).map((n) => `${n} — ilk görüşme hazırlığı önerilir`) },
      };
      const block = map[key] || { title: 'Sonuç', items: [] };
      aiResults.innerHTML = `<h3>${esc(block.title)}</h3><ul>${block.items.length ? block.items.map((i) => `<li>${esc(i)}</li>`).join('') : '<li class="muted">Veri bulunamadı</li>'}</ul>`;
      aiResults.hidden = false;
    });
  });

  /* Export CSV */
  document.getElementById('aocExportBtn')?.addEventListener('click', (e) => {
    e.preventDefault();
    const boardRows = document.querySelectorAll('.aoc-board-row[data-export-client]');
    const table = document.getElementById('aocTable');
    let csvRows = [];

    if (boardRows.length) {
      csvRows = ['Danışan;Telefon;Terapist;Şube;Tarih;Saat;Tür;Neden;Durum'];
      boardRows.forEach((row) => {
        csvRows.push([
          row.dataset.exportClient,
          row.dataset.exportPhone,
          row.dataset.exportTherapist,
          row.dataset.exportBranch,
          row.dataset.exportDate,
          row.dataset.exportTime,
          row.dataset.exportType,
          row.dataset.exportReason,
          row.dataset.exportStatus,
        ].map((v) => `"${String(v || '').replace(/"/g, '""')}"`).join(';'));
      });
    } else if (table) {
      const header = table.querySelectorAll('thead th');
      const cols = [];
      header.forEach((th, i) => {
        if (i !== 0 && !th.classList.contains('aoc-th-actions')) cols.push(i);
      });
      csvRows = [cols.map((i) => header[i].textContent.trim()).join(';')];
      table.querySelectorAll('tbody tr').forEach((tr) => {
        const cells = tr.querySelectorAll('td');
        csvRows.push(cols.map((i) => `"${(cells[i]?.textContent || '').trim().replace(/"/g, '""')}"`).join(';'));
      });
    } else {
      return;
    }

    const blob = new Blob(['\ufeff' + csvRows.join('\n')], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `randevular-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  });

  /* Init view from URL */
  const params = new URLSearchParams(window.location.search);
  const initialView = params.get('view') || 'list';
  setActiveView(initialView);
})();
