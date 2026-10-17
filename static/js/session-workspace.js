(function () {
  'use strict';

  const drawer = document.getElementById('swsDrawer');
  const overlay = document.getElementById('swsDrawerOverlay');
  const body = document.getElementById('swsDrawerBody');
  const title = document.getElementById('swsDrawerTitle');
  const sub = document.getElementById('swsDrawerSub');
  if (!drawer || !overlay || !body) return;

  let currentData = null;
  let currentId = null;
  let autosaveTimer = null;
  let dirty = false;
  let activeTab = 'overview';
  let timerInterval = null;
  let timerState = null;

  const TABS = [
    { id: 'overview', label: 'Genel Bakış' },
    { id: 'note', label: 'Seans Notu', perm: 'clinical' },
    { id: 'plan', label: 'Terapi Planı', perm: 'clinical' },
    { id: 'goals', label: 'Hedefler', perm: 'clinical' },
    { id: 'homework', label: 'Ödevler', perm: 'clinical' },
    { id: 'tests', label: 'Testler', perm: 'clinical' },
    { id: 'documents', label: 'Belgeler', perm: 'clinical' },
    { id: 'supervision', label: 'Süpervizyon', perm: 'supervision' },
  ];

  const HW_STATUS = { taslak: 'Taslak', atandi: 'Atandı', baslandi: 'Başlandı', tamamlandi: 'Tamamlandı', gecikti: 'Gecikti', iptal: 'İptal Edildi' };
  const GOAL_STATUS = { devam: 'Devam', tamamlandi: 'Tamamlandı', iptal: 'İptal' };
  const TEST_PHASE = { on_test: 'Ön test', ara_test: 'Ara test', son_test: 'Son test' };

  const esc = (v) => String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  function toast(msg, type) {
    let el = document.getElementById('swsToast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'swsToast';
      el.className = 'sws-toast';
      el.setAttribute('role', 'status');
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.className = 'sws-toast sws-toast-' + (type || 'success') + ' show';
    setTimeout(() => el.classList.remove('show'), 3200);
  }

  function setAutosave(text, state) {
    const el = body.querySelector('#swsAutosaveInner');
    if (!el) return;
    el.className = 'sws-autosave' + (state ? ' ' + state : '');
    el.textContent = text || '';
  }

  function timerStorageKey(id) { return 'sws_timer_' + id; }

  function loadTimerFromStorage(id) {
    try { return JSON.parse(localStorage.getItem(timerStorageKey(id)) || 'null'); } catch { return null; }
  }

  function saveTimerToStorage(id, state) {
    localStorage.setItem(timerStorageKey(id), JSON.stringify(state));
  }

  function formatTimerDisplay(seconds, planned) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${String(s).padStart(2, '0')} / ${planned} dk`;
  }

  function stopTimerInterval() {
    if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
  }

  function syncTimerUI() {
    const display = body.querySelector('#swsTimerDisplay');
    if (!display || !timerState) return;
    const planned = timerState.planned_minutes || 50;
    display.textContent = formatTimerDisplay(timerState.elapsed_seconds || 0, planned);
    const startBtn = body.querySelector('[data-timer="start"]');
    const pauseBtn = body.querySelector('[data-timer="pause"]');
    if (startBtn) startBtn.textContent = timerState.running ? 'Devam Ettir' : (timerState.paused ? 'Devam Ettir' : 'Başlat');
    if (pauseBtn) pauseBtn.disabled = !timerState.running;
  }

  function persistTimer() {
    if (!currentId || !timerState) return;
    saveTimerToStorage(currentId, timerState);
    postAction('timer', timerState, true);
  }

  function initTimer(data) {
    stopTimerInterval();
    const stored = loadTimerFromStorage(data.id);
    timerState = stored || { ...(data.timer || {}), planned_minutes: data.timer?.planned_minutes || data.session_meta?.duration_minutes || 50, elapsed_seconds: data.timer?.elapsed_seconds || 0, running: false, paused: false, finished: data.timer?.finished || false };
    syncTimerUI();
    if (timerState.running) startTimerTick();
  }

  function startTimerTick() {
    stopTimerInterval();
    timerState.running = true;
    timerState.paused = false;
    timerState.finished = false;
    timerInterval = setInterval(() => {
      timerState.elapsed_seconds = (timerState.elapsed_seconds || 0) + 1;
      syncTimerUI();
      const planned = (timerState.planned_minutes || 50) * 60;
      if (timerState.elapsed_seconds === planned - 300) toast('Seans bitimine 5 dakika kaldı.', 'info');
      if (timerState.elapsed_seconds % 15 === 0) saveTimerToStorage(currentId, timerState);
    }, 1000);
    syncTimerUI();
    persistTimer();
  }

  function pauseTimer() {
    if (!timerState?.running) return;
    stopTimerInterval();
    timerState.running = false;
    timerState.paused = true;
    syncTimerUI();
    persistTimer();
  }

  function stopTimer(askComplete) {
    if (!timerState) return;
    stopTimerInterval();
    timerState.running = false;
    timerState.paused = false;
    timerState.finished = true;
    syncTimerUI();
    persistTimer();
    if (askComplete && confirm('Zamanlayıcı durduruldu. Seansı tamamlamak ister misiniz?')) openCompleteModal();
  }

  function bindTimerEvents() {
    body.querySelector('[data-timer="start"]')?.addEventListener('click', () => {
      if (timerState.running) return;
      if (timerState.finished) timerState.elapsed_seconds = 0;
      startTimerTick();
    });
    body.querySelector('[data-timer="pause"]')?.addEventListener('click', pauseTimer);
    body.querySelector('[data-timer="stop"]')?.addEventListener('click', () => stopTimer(true));
  }

  function openDrawer(id, initialTab) {
    currentId = id;
    activeTab = initialTab || window.SWS_PENDING_TAB || 'overview';
    window.SWS_PENDING_TAB = null;
    drawer.hidden = false;
    overlay.hidden = false;
    requestAnimationFrame(() => {
      drawer.classList.add('open');
      overlay.classList.add('open');
    });
    document.body.classList.add('drawer-open');
    title.textContent = 'Yükleniyor…';
    sub.textContent = '';
    body.innerHTML = '<div class="sws-skeleton"></div><div class="sws-skeleton"></div>';
    loadWorkspace(id, activeTab !== 'overview' ? activeTab : undefined);
  }

  function loadWorkspace(id, keepTab) {
    return fetch(`/admin/seans/${id}/workspace`, { headers: { 'X-Requested-With': 'fetch' } })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((data) => {
        currentData = data;
        currentId = id;
        title.textContent = data.header.title;
        sub.textContent = data.header.subtitle + ' · ' + data.header.status;
        renderWorkspace(data);
        if (keepTab) switchToTab(keepTab);
        initTimer(data);
      })
      .catch(() => {
        title.textContent = 'Kayıt yüklenemedi';
        sub.textContent = '';
        body.innerHTML = '<p class="drawer-empty">Detay bilgisi alınamadı. Sayfayı yenileyip tekrar deneyin.</p>';
      });
  }

  function closeDrawer() {
    if (dirty && !confirm('Kaydedilmemiş değişiklikler var. Kapatmak istiyor musunuz?')) return;
    stopTimerInterval();
    drawer.classList.remove('open');
    overlay.classList.remove('open');
    document.body.classList.remove('drawer-open');
    closeModal();
    setTimeout(() => { drawer.hidden = true; overlay.hidden = true; }, 220);
    currentData = null;
    currentId = null;
  }

  function visibleTabs(data) {
    return TABS.filter((t) => !t.perm || (data.permissions && data.permissions[t.perm]));
  }

  function renderToolbar(data) {
    const p = data.permissions || {};
    const primary = [];
    if (p.complete) primary.push('<button type="button" class="btn btn-xs btn-primary" data-action="complete" aria-label="Seansı tamamla">Seansı Tamamla</button>');
    if (p.clinical) primary.push('<button type="button" class="btn btn-xs btn-primary" data-action="save-note" aria-label="Notu kaydet">Notu Kaydet</button>');
    if (p.sign) primary.push('<button type="button" class="btn btn-xs btn-outline" data-action="sign" aria-label="Notu imzala">Notu İmzala</button>');
    const secondary = [];
    if (p.clinical) {
      secondary.push('<button type="button" class="btn btn-xs btn-outline" data-action="test">Test Ata</button>');
      secondary.push('<button type="button" class="btn btn-xs btn-outline" data-action="homework">Ödev Oluştur</button>');
    }
    secondary.push('<button type="button" class="btn btn-xs btn-outline" data-action="appointment">Randevu Oluştur</button>');
    const other = [];
    if (p.print) other.push('<button type="button" class="btn btn-xs btn-ghost" data-action="print">Yazdır</button>');
    return `<div class="sws-toolbar">
      <div class="sws-toolbar-group sws-toolbar-primary">${primary.join('')}</div>
      <div class="sws-toolbar-group sws-toolbar-secondary">${secondary.join('')}</div>
      <details class="sws-toolbar-more"><summary>Diğer İşlemler</summary><div class="sws-toolbar-group">${other.join('')}<button type="button" class="btn btn-xs btn-ghost" data-action="document">Belge Yükle</button></div></details>
      <span class="sws-autosave" id="swsAutosaveInner"></span>
    </div>`;
  }

  function renderWorkspace(data) {
    const tabs = visibleTabs(data);
    const idx = Math.max(0, tabs.findIndex((t) => t.id === activeTab));
    activeTab = tabs[idx]?.id || tabs[0]?.id || 'overview';

    const tabsHtml = tabs.map((t) =>
      `<button type="button" role="tab" aria-selected="${t.id === activeTab}" class="sws-tab ${t.id === activeTab ? 'active' : ''}" data-tab="${t.id}">${esc(t.label)}</button>`
    ).join('');

    const panels = tabs.map((t) =>
      `<div class="sws-tab-panel ${t.id === activeTab ? 'active' : ''}" role="tabpanel" data-panel="${t.id}">${renderPanel(t.id, data)}</div>`
    ).join('');

    body.innerHTML = `
      <div class="sws-drawer-inner">
        ${renderTimerBar(data)}
        ${renderToolbar(data)}
        <div class="sws-tabs-wrap" id="swsTabsWrap">
          <button type="button" class="sws-tabs-scroll sws-tabs-scroll-left" aria-label="Sola kaydır" hidden>‹</button>
          <div class="sws-tabs" role="tablist">${tabsHtml}</div>
          <button type="button" class="sws-tabs-scroll sws-tabs-scroll-right" aria-label="Sağa kaydır">›</button>
        </div>
        <div class="sws-panels">${panels}</div>
      </div>`;

    bindTabEvents();
    bindToolbar(data);
    bindFormEvents(data);
    bindTimerEvents();
    bindOverviewActions();
    bindHomeworkListActions();
    bindHomeworkItemActions();
    bindGoalsListActions();
    bindDocumentListActions();
    setupTabScroll();
    switchToTab(activeTab);
  }

  function renderTimerBar(data) {
    const t = data.timer || {};
    const planned = t.planned_minutes || data.session_meta?.duration_minutes || 50;
    return `<div class="sws-timer-bar">
      <span class="sws-timer-display" id="swsTimerDisplay">0:00 / ${planned} dk</span>
      <button type="button" class="btn btn-xs btn-primary" data-timer="start" aria-label="Zamanlayıcıyı başlat">Başlat</button>
      <button type="button" class="btn btn-xs btn-outline" data-timer="pause" aria-label="Zamanlayıcıyı duraklat" disabled>Duraklat</button>
      <button type="button" class="btn btn-xs btn-outline" data-timer="stop" aria-label="Zamanlayıcıyı bitir" title="Yalnızca süreyi durdurur; seans kaydını tamamlamaz">Bitir</button>
      <small class="sws-timer-hint">Bitir = süreyi durdurur · Seansı Tamamla = klinik kaydı kapatır</small>
    </div>`;
  }

  function switchToTab(tabId) {
    const tabEl = body.querySelector(`.sws-tab[data-tab="${tabId}"]`);
    const panelEl = body.querySelector(`.sws-tab-panel[data-panel="${tabId}"]`);
    if (!tabEl || !panelEl) return false;
    activeTab = tabId;
    body.querySelectorAll('.sws-tab').forEach((tab) => {
      const on = tab.dataset.tab === tabId;
      tab.classList.toggle('active', on);
      tab.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    body.querySelectorAll('.sws-tab-panel').forEach((p) => p.classList.toggle('active', p.dataset.panel === tabId));
    tabEl.scrollIntoView({ inline: 'nearest', block: 'nearest', behavior: 'smooth' });
    setupTabScroll();
    return true;
  }

  function navigateToTab(tabId) {
    if (switchToTab(tabId)) return true;
    toast('Bu sekme yüklenemedi. Sayfayı Ctrl+F5 ile yenileyin.', 'error');
    return false;
  }

  function setupTabScroll() {
    const wrap = body.querySelector('#swsTabsWrap');
    const tabs = wrap?.querySelector('.sws-tabs');
    const left = wrap?.querySelector('.sws-tabs-scroll-left');
    const right = wrap?.querySelector('.sws-tabs-scroll-right');
    if (!wrap || !tabs) return;
    const update = () => {
      const max = tabs.scrollWidth - tabs.clientWidth;
      if (left) left.hidden = tabs.scrollLeft <= 4;
      if (right) right.hidden = tabs.scrollLeft >= max - 4;
    };
    tabs.onscroll = update;
    left?.addEventListener('click', () => { tabs.scrollBy({ left: -120, behavior: 'smooth' }); });
    right?.addEventListener('click', () => { tabs.scrollBy({ left: 120, behavior: 'smooth' }); });
    update();
  }

  function renderPanel(id, data) {
    const map = { overview: renderOverview, note: renderNote, plan: renderPlan, tests: renderTests, goals: renderGoals, homework: renderHomework, risk: renderRisk, documents: renderDocuments, payments: renderPayments, history: renderHistory, tasks: renderTasks, supervision: renderSupervision };
    const fn = map[id];
    if (fn) return fn(data);
    return emptyState('İçerik yok');
  }

  function emptyState(msg, hint) {
    return `<div class="sws-empty-state"><strong>${esc(msg)}</strong><span>${esc(hint || 'Kayıt bulunamadı.')}</span></div>`;
  }

  function overviewField(label, value, action) {
    const act = action ? `<button type="button" class="sws-link-btn" data-overview-action="${action}">Ekle</button>` : '';
    return `<div class="sws-overview-card"><span>${esc(label)}</span><strong>${esc(value)}</strong>${act}</div>`;
  }

  function renderOverview(data) {
    const o = data.overview || {};
    const canEdit = data.permissions?.clinical;
    const goals = (o.active_goals || []).length
      ? (o.active_goals || []).map((g) => `<li>${esc(g.name || g.title)}</li>`).join('')
      : `<li class="sws-muted">Aktif hedef bulunmuyor${canEdit ? ' · <button type="button" class="sws-link-btn" data-overview-action="goals">Ekle</button>' : ''}</li>`;
    const tasks = (o.open_tasks || []).length
      ? (o.open_tasks || []).map((t) => `<li>${esc(t.title)}</li>`).join('')
      : `<li class="sws-muted">Açık görev bulunmuyor</li>`;
    const tests = (o.recent_tests || []).length
      ? (o.recent_tests || []).map((t) => `<li>${esc(t.title)} — ${esc(t.level)}</li>`).join('')
      : `<li class="sws-muted">Test kaydı bulunmuyor${canEdit ? ' · <button type="button" class="sws-link-btn" data-overview-action="test">Ata</button>' : ''}</li>`;

    return `<div class="sws-overview-grid">
      ${overviewField('Danışan', o.name || '—')}
      ${overviewField('İletişim', (o.email || '—') + (o.phone ? ' · ' + o.phone : ''))}
      ${overviewField('Yaş Grubu', o.age_group_label, canEdit && !o.age_group ? 'age_group' : null)}
      ${overviewField('Başvuru Nedeni', (o.reasons || []).join(', ') || 'Belirtilmedi')}
      ${overviewField('Toplam Seans', o.total_sessions ?? '—')}
      ${overviewField('Sonraki Randevu', o.next_appointment_label, canEdit && !data.next_appointment ? 'appointment' : null)}
      ${overviewField('Terapi Yaklaşımı', o.approach_label, canEdit && !o.approach ? 'plan' : null)}
      ${overviewField('Seans Durumu', o.display_status || '—')}
      ${overviewField('Ödeme', o.payment_status || '—')}
    </div>
    <div class="sws-overview-compact">
      <article class="sws-compact-card"><h4>Son Klinik Not</h4><p>${esc(o.note_preview_label)}</p>${canEdit ? '<button type="button" class="sws-link-btn" data-overview-action="note">Nota git →</button>' : ''}</article>
      <article class="sws-compact-card"><h4>Terapi Planı</h4><p>${esc(o.plan_summary_label)}</p>${canEdit ? '<button type="button" class="sws-link-btn" data-overview-action="plan">Planla →</button>' : ''}</article>
      <article class="sws-compact-card"><h4>Aktif Ödev</h4><p>${o.active_homework_count || 0} açık ödev</p>${canEdit ? '<button type="button" class="sws-link-btn" data-overview-action="homework">Ödev ver →</button>' : ''}</article>
    </div>
    <div class="sws-overview-lists">
      <div><h4>Aktif Hedefler</h4><ul>${goals}</ul></div>
      <div><h4>Son Testler</h4><ul>${tests}</ul></div>
      <div><h4>Açık Görevler</h4><ul>${tasks}</ul></div>
    </div>`;
  }

  function bindOverviewActions() {
    body.querySelectorAll('[data-overview-action]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const a = btn.dataset.overviewAction;
        if (a === 'homework') openHomeworkModal();
        else if (a === 'test') openTestModal();
        else if (a === 'appointment') openAppointmentModal();
        else if (a === 'age_group') openAgeGroupModal();
        else if (a === 'goals') { if (!switchToTab('goals')) openGoalModal(null); }
        else if (a === 'plan') navigateToTab('plan');
        else if (a === 'note') navigateToTab('note');
        else navigateToTab(a);
      });
    });
  }

  const AGE_GROUP_OPTIONS = ['Çocuk', 'Ergen', 'Yetişkin', 'Çift', 'Aile'];

  function openAgeGroupModal() {
    const current = (currentData?.overview?.age_group || '').trim();
    const opts = AGE_GROUP_OPTIONS.map((o) => `<option value="${esc(o)}" ${current === o ? 'selected' : ''}>${esc(o)}</option>`).join('');
    openModal('Yaş grubu', `
      <div class="sws-field"><label for="swsAgeGroup">Danışan yaş grubu</label>
      <select id="swsAgeGroup" required><option value="">Seçin</option>${opts}</select></div>`, () => {
      setModalLoading(true);
      const val = document.getElementById('swsAgeGroup')?.value?.trim();
      if (!val) { setModalLoading(false); toast('Lütfen yaş grubu seçin.', 'error'); return; }
      postSave({ section: 'age_group', data: val }).then(() => {
        closeModal();
        toast('Yaş grubu kaydedildi.');
        loadWorkspace(currentId, 'overview');
      }).catch((e) => { setModalLoading(false); toast(e.message, 'error'); });
    });
  }

  function renderNote(data) {
    if (!data.permissions?.clinical) return emptyState('Erişim yok', 'Klinik notları görüntüleme yetkiniz yok.');
    const note = data.note || { template: 'free', fields: {}, status: 'taslak' };
    const tpl = note.template || 'free';
    const fields = note.fields || {};
    const fieldDefs = (data.note_template_fields && data.note_template_fields[tpl]) || ['body'];
    const tplOptions = Object.entries(data.note_templates || {}).map(([k, v]) => `<option value="${k}" ${k === tpl ? 'selected' : ''}>${esc(v)}</option>`).join('');
    const fieldsHtml = fieldDefs.map((f) => {
      const label = (data.note_field_labels && data.note_field_labels[f]) || f;
      const ro = note.status === 'imzalandi' ? 'readonly' : '';
      return `<div class="sws-field"><label for="note_${f}">${esc(label)}</label><textarea id="note_${f}" name="note_${f}" data-note-field="${f}" ${ro}>${esc(fields[f] || '')}</textarea></div>`;
    }).join('');
    const noteStatusText = (data.note_status_labels || {})[note.status] || note.status || 'Taslak';
    const aiHtml = data.ai_summary ? renderAiSummary(data) : `<button type="button" class="btn btn-sm btn-outline" id="swsGenAi">AI Özet Taslağı Oluştur</button>`;
    return `<div class="sws-form-grid" id="swsNoteForm">
      <div class="sws-field"><label for="swsNoteTemplate">Not Şablonu</label><select id="swsNoteTemplate">${tplOptions}</select></div>
      ${fieldsHtml}
      ${note.status === 'imzalandi' ? `<p class="sws-signed-banner">İmzalandı · ${esc(note.signed_by || '')} · ${esc(note.signed_at || '')}. Değişiklik için gerekçe gerekir.</p>` : ''}
      <div class="sws-form-actions">
        <button type="button" class="btn btn-sm btn-primary" id="swsSaveNote">Kaydet</button>
        <span class="muted sws-note-status">Durum: ${esc(noteStatusText)}</span>
      </div>
      <hr><h3 class="sws-section-title">AI Destekli Özet</h3>
      <div class="sws-ai-banner">${esc(data.ai_disclaimer)}</div>
      <div id="swsAiArea">${aiHtml}</div>
    </div>`;
  }

  function renderAiSummary(data) {
    const s = (data.ai_summary && data.ai_summary.sections) || {};
    const keys = ['summary', 'themes', 'interventions', 'responses', 'follow_up', 'next_agenda', 'homework_draft'];
    const labels = ['Seans Özeti', 'Ana Temalar', 'Müdahaleler', 'Tepkiler', 'Takip Konuları', 'Gelecek Gündem', 'Ev Ödevi Taslağı'];
    return keys.map((k, i) => `<div class="sws-ai-section"><h4>${labels[i]}</h4><textarea data-ai-field="${k}">${esc(s[k] || '')}</textarea></div>`).join('');
  }

  function renderPlan(data) {
    const p = data.therapy_plan || {};
    const ag = (data.overview?.age_group || '').trim();
    const ageOpts = AGE_GROUP_OPTIONS.map((o) => `<option value="${esc(o)}" ${ag === o ? 'selected' : ''}>${esc(o)}</option>`).join('');
    const approaches = (data.therapy_approaches || []).map((a) => `<option value="${esc(a)}" ${p.approach === a ? 'selected' : ''}>${esc(a)}</option>`).join('');
    return `<div class="sws-form-grid" id="swsPlanForm">
      <div class="sws-field"><label>Yaş grubu</label><select name="age_group"><option value="">Seçin</option>${ageOpts}</select></div>
      <div class="sws-field"><label>Ana başvuru nedeni</label><input name="primary_reason" value="${esc(p.primary_reason || '')}"></div>
      <div class="sws-field"><label>Kullanılan yaklaşım</label><select name="approach"><option value="">Seçin</option>${approaches}</select></div>
      <div class="sws-field"><label>Terapötik hedefler</label><textarea name="goals_text">${esc(p.goals_text || '')}</textarea></div>
      <div class="sws-field"><label>Planlanan sıklık</label><input name="frequency" value="${esc(p.frequency || '')}" placeholder="Haftada 1"></div>
      <div class="sws-field"><label>Plan durumu</label><select name="status">${Object.entries(data.plan_status_labels || {}).map(([k,v]) => `<option value="${k}" ${p.status === k ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select></div>
      <button type="button" class="btn btn-sm btn-primary" id="swsSavePlan">Planı Kaydet</button>
    </div>`;
  }

  function renderTests(data) {
    const assigned = (data.assigned_tests || []).map((t) => ({
      title: t.title,
      date: t.assigned_date || t.date || '',
      phase: t.phase,
      level: t.status || 'Atandı',
      score: '—',
    }));
    const tests = assigned.length ? assigned : (data.tests || []);
    if (!tests.length) {
      return emptyState('Test veya ölçek kaydı yok', 'Danışana test atayarak başlayın.')
        + `<button type="button" class="btn btn-sm btn-outline" data-action="test">Test Ata</button>`;
    }
    return tests.map((t) => `<div class="sws-list-item"><div><strong>${esc(t.title)}</strong><br><small>${esc(t.date)} · ${esc(TEST_PHASE[t.phase] || t.phase || '')}</small></div><span class="badge-soft">${esc(t.level)} ${t.score !== '—' ? '· ' + t.score : ''}</span></div>`).join('');
  }

  function renderHomework(data) {
    const canEdit = data.permissions?.clinical;
    const items = data.homework || [];
    if (!items.length) {
      return emptyState('Atanmış ödev yok', 'Terapist danışana ödev atayabilir.')
        + (canEdit ? `<button type="button" class="btn btn-sm btn-primary" id="swsAddHomework" data-action="homework">Ödev Oluştur</button>` : '');
    }
    const rows = items.map((h) => {
      const vis = h.visible_to_client !== false ? '<span class="sws-badge sws-badge-ok">Danışana açık</span>' : '<span class="sws-badge sws-badge-muted">Gizli</span>';
      const clientLine = h.client_response ? `<p class="sws-muted sws-hw-client">${esc(h.client_response)}</p>` : '';
      const actions = canEdit ? `<div class="sws-list-actions">
          <select class="sws-inline-select" data-hw-status="${esc(h.id)}" aria-label="Ödev durumu">${Object.entries(HW_STATUS).map(([k, v]) => `<option value="${k}" ${h.status === k ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select>
          <button type="button" class="btn btn-xs btn-outline" data-hw-edit="${esc(h.id)}">Düzenle</button>
          <button type="button" class="btn btn-xs btn-ghost sws-danger-text" data-hw-remove="${esc(h.id)}">Sil</button>
        </div>` : '';
      return `<div class="sws-list-item sws-hw-item" data-hw-id="${esc(h.id)}">
        <div class="sws-list-main"><strong>${esc(h.title)}</strong> ${vis}
          <br><small>${esc(h.template || '')} · Teslim: ${esc(h.due_date || '—')}</small>
          ${h.description ? `<p class="sws-muted">${esc(h.description)}</p>` : ''}${clientLine}
        </div>
        <div class="sws-list-side"><span class="badge-soft">${esc(HW_STATUS[h.status] || h.status)}</span>${actions}</div>
      </div>`;
    }).join('');
    return rows + (canEdit ? `<button type="button" class="btn btn-sm btn-outline" id="swsAddHomework" data-action="homework">+ Yeni Ödev</button>` : '');
  }

  function bindHomeworkItemActions() {
    body.querySelectorAll('[data-hw-status]').forEach((sel) => {
      sel.addEventListener('change', () => {
        const id = sel.dataset.hwStatus;
        postAction('update_homework', { id: isNaN(Number(id)) ? id : Number(id), status: sel.value })
          .then(() => toast('Ödev durumu güncellendi.'))
          .catch((e) => toast(e.message, 'error'));
      });
    });
    body.querySelectorAll('[data-hw-edit]').forEach((btn) => {
      btn.addEventListener('click', () => openHomeworkModal(findHomework(btn.dataset.hwEdit)));
    });
    body.querySelectorAll('[data-hw-remove]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.hwRemove;
        if (!confirm('Bu ödev silinsin mi?')) return;
        const numId = isNaN(Number(id)) ? id : Number(id);
        postAction('remove_homework', { id: numId })
          .then(() => toast('Ödev silindi.'))
          .catch((e) => toast(e.message, 'error'));
      });
    });
  }

  function findHomework(id) {
    const items = currentData?.homework || [];
    return items.find((h) => String(h.id) === String(id)) || null;
  }

  function bindHomeworkListActions() {
    body.querySelectorAll('#swsAddHomework,[data-action="homework"]').forEach((btn) => {
      if (btn.closest('.sws-toolbar')) return;
      btn.addEventListener('click', (e) => { e.stopPropagation(); openHomeworkModal(); });
    });
  }

  function renderGoals(data) {
    const canEdit = data.permissions?.clinical;
    const goals = data.goals || [];
    const header = canEdit ? `<div class="sws-section-head"><button type="button" class="btn btn-sm btn-primary" id="swsAddGoal">+ Hedef Ekle</button></div>` : '';
    if (!goals.length) {
      return header + emptyState('Tanımlı hedef yok', 'Seans hedeflerini buradan ekleyebilirsiniz.');
    }
    const rows = goals.map((g) => {
      const actions = canEdit ? `<div class="sws-list-actions">
          <button type="button" class="btn btn-xs btn-outline" data-goal-edit="${esc(g.id)}">Düzenle</button>
          <button type="button" class="btn btn-xs btn-ghost sws-danger-text" data-goal-remove="${esc(g.id)}">Sil</button>
        </div>` : '';
      return `<div class="sws-list-item"><div><strong>${esc(g.name || 'Hedef')}</strong><br><small>${esc(g.description || '')}</small></div>
        <div class="sws-list-side"><span>${esc(GOAL_STATUS[g.status] || g.status || 'devam')} · %${esc(g.progress ?? 0)}</span>${actions}</div></div>`;
    }).join('');
    return header + rows;
  }

  function bindGoalsListActions() {
    body.querySelector('#swsAddGoal')?.addEventListener('click', () => openGoalModal(null));
    body.querySelectorAll('[data-goal-edit]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const g = (currentData?.goals || []).find((x) => String(x.id) === String(btn.dataset.goalEdit));
        openGoalModal(g);
      });
    });
    body.querySelectorAll('[data-goal-remove]').forEach((btn) => {
      btn.addEventListener('click', () => {
        if (!confirm('Bu hedef silinsin mi?')) return;
        postAction('remove_goal', { id: btn.dataset.goalRemove })
          .then(() => toast('Hedef silindi.'))
          .catch((e) => toast(e.message, 'error'));
      });
    });
  }

  function openGoalModal(existing) {
    const g = existing || {};
    const statusOpts = Object.entries(GOAL_STATUS).map(([k, v]) => `<option value="${k}" ${(g.status || 'devam') === k ? 'selected' : ''}>${esc(v)}</option>`).join('');
    openModal(existing ? 'Hedefi Düzenle' : 'Yeni Hedef', `
      <div class="sws-form-grid">
        <div class="sws-field"><label for="goal_name">Hedef adı</label><input id="goal_name" required value="${esc(g.name || '')}"></div>
        <div class="sws-field"><label for="goal_desc">Açıklama</label><textarea id="goal_desc">${esc(g.description || '')}</textarea></div>
        <div class="sws-field"><label for="goal_status">Durum</label><select id="goal_status">${statusOpts}</select></div>
        <div class="sws-field"><label for="goal_progress">İlerleme (%)</label><input type="number" id="goal_progress" min="0" max="100" value="${esc(g.progress ?? 0)}"></div>
      </div>`, () => {
      setModalLoading(true);
      const payload = {
        name: document.getElementById('goal_name').value.trim(),
        description: document.getElementById('goal_desc').value.trim(),
        status: document.getElementById('goal_status').value,
        progress: parseInt(document.getElementById('goal_progress').value, 10) || 0,
      };
      const action = existing ? 'update_goal' : 'add_goal';
      if (existing) payload.id = g.id;
      postAction(action, payload).then(() => {
        closeModal();
        toast(existing ? 'Hedef güncellendi.' : 'Hedef eklendi.');
        switchToTab('goals');
      }).catch((e) => { setModalLoading(false); toast(e.message, 'error'); });
    });
  }

  function renderRisk(data) {
    if (!data.permissions?.risk) return emptyState('Erişim kısıtlı', 'Risk alanı için yetki gerekir.');
    const r = data.risk || {};
    return `<div class="sws-form-grid sws-risk-form" id="swsRiskForm">
      <div class="sws-field"><label>Risk seviyesi</label><select name="level">${Object.entries(data.risk_level_labels || {}).map(([k,v]) => `<option value="${k}" ${r.level === k ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select></div>
      <div class="sws-field"><label>Kriz notu</label><textarea name="notes">${esc(r.notes || '')}</textarea></div>
      <div class="sws-field"><label>Güvenlik planı</label><textarea name="safety_plan">${esc(r.safety_plan || '')}</textarea></div>
      <button type="button" class="btn btn-sm btn-primary" id="swsSaveRisk">Kaydet</button>
      <small class="muted">Sistem otomatik risk kararı vermez.</small>
    </div>`;
  }

  function renderDocuments(data) {
    const canEdit = data.permissions?.clinical;
    const docs = data.documents || [];
    const header = canEdit ? `<div class="sws-section-head"><button type="button" class="btn btn-sm btn-primary" data-action="document">+ Belge Yükle</button></div>` : '';
    if (!docs.length) {
      return header + emptyState('Yüklenmiş belge yok', 'Onam formu, rapor veya seans ekleri buradan eklenebilir.');
    }
    const rows = docs.map((d) => {
      const href = d.storage_path ? `/static/${d.storage_path.replace(/^\/+/, '')}` : '#';
      const sizeKb = d.size_bytes ? `${Math.round(d.size_bytes / 1024)} KB` : '';
      const actions = canEdit ? `<button type="button" class="btn btn-xs btn-ghost sws-danger-text" data-doc-remove="${esc(d.id)}">Sil</button>` : '';
      return `<div class="sws-list-item">
        <div class="sws-list-main"><strong>${esc(d.title || d.file_name || 'Belge')}</strong>
          <br><small>${esc(d.doc_type || '')} · ${esc(d.file_name || '')}${sizeKb ? ' · ' + sizeKb : ''}</small>
          ${d.notes ? `<p class="sws-muted">${esc(d.notes)}</p>` : ''}
        </div>
        <div class="sws-list-side">
          ${d.storage_path ? `<a class="btn btn-xs btn-outline" href="${esc(href)}" target="_blank" rel="noopener">Aç</a>` : ''}${actions}
        </div>
      </div>`;
    }).join('');
    return header + rows;
  }

  function bindDocumentListActions() {
    body.querySelectorAll('[data-action="document"]').forEach((btn) => {
      if (btn.closest('.sws-toolbar-more')) {
        btn.addEventListener('click', (e) => { e.preventDefault(); openDocumentModal(); });
      } else {
        btn.addEventListener('click', (e) => { e.stopPropagation(); openDocumentModal(); });
      }
    });
    body.querySelectorAll('[data-doc-remove]').forEach((btn) => {
      btn.addEventListener('click', () => {
        if (!confirm('Bu belge kaydı silinsin mi? (Dosya sunucuda kalabilir.)')) return;
        postAction('remove_document', { id: btn.dataset.docRemove })
          .then(() => toast('Belge silindi.'))
          .catch((err) => toast(err.message, 'error'));
      });
    });
  }

  function openDocumentModal() {
    const types = (currentData?.document_types || []).map((t) => `<option value="${esc(t)}">${esc(t)}</option>`).join('');
    openModal('Belge Yükle', `
      <div class="sws-form-grid">
        <div class="sws-field"><label for="doc_title">Başlık</label><input id="doc_title" placeholder="Örn. Onam formu"></div>
        <div class="sws-field"><label for="doc_type">Belge türü</label><select id="doc_type"><option value="">Seçin</option>${types}</select></div>
        <div class="sws-field"><label for="doc_file">Dosya</label><input type="file" id="doc_file" required accept=".pdf,.png,.jpg,.jpeg,.webp,.gif,.doc,.docx,.txt"></div>
        <div class="sws-field"><label for="doc_notes">Not</label><textarea id="doc_notes" rows="2"></textarea></div>
        <div class="sws-field"><label><input type="checkbox" id="doc_visible"> Danışan portalında göster</label></div>
        <small class="muted">PDF, görsel veya metin; en fazla 10 MB.</small>
      </div>`, (root) => {
      setModalLoading(true);
      const fileInput = root.querySelector('#doc_file');
      if (!fileInput?.files?.length) {
        setModalLoading(false);
        toast('Lütfen dosya seçin.', 'error');
        return;
      }
      const fd = new FormData();
      fd.append('file', fileInput.files[0]);
      fd.append('title', root.querySelector('#doc_title')?.value || fileInput.files[0].name);
      fd.append('doc_type', root.querySelector('#doc_type')?.value || 'Diğer');
      fd.append('notes', root.querySelector('#doc_notes')?.value || '');
      if (root.querySelector('#doc_visible')?.checked) fd.append('visible_to_client', '1');
      fetch(`/admin/seans/${currentId}/workspace/document`, {
        method: 'POST',
        headers: { 'X-Requested-With': 'fetch' },
        body: fd,
      }).then((r) => r.json().then((j) => ({ ok: r.ok, j }))).then(({ ok, j }) => {
        if (!ok) throw new Error(j.error || 'Yükleme hatası');
        closeModal();
        toast('Belge yüklendi.');
        loadWorkspace(currentId, 'documents');
      }).catch((e) => { setModalLoading(false); toast(e.message, 'error'); });
    }, 'Yükle');
  }

  function renderPayments(data) {
    const p = data.payments || [];
    if (!p.length) return emptyState('Ödeme kaydı yok', 'Muhasebe modülünden fatura oluşturulabilir.');
    return p.map((pay) => `<div class="sws-list-item"><div><strong>${esc(pay.amount)}</strong><br><small>${esc(pay.date)}</small></div><span>${esc(pay.status)}</span></div>`).join('');
  }

  function renderHistory(data) {
    const h = data.history || [];
    if (!h.length) return emptyState('Geçmiş seans yok');
    return `<ul class="sws-timeline-list">${h.map((item) => `<li class="${item.current ? 'current' : ''}" data-open-session="${item.id}"><strong>${esc(item.date)}</strong><small>${esc(item.therapist)} · ${esc(item.note_status)}</small></li>`).join('')}</ul>`;
  }

  function renderTasks(data) {
    return emptyState('Takip görevi yok', 'Seans sonrası görev oluşturabilirsiniz.');
  }

  function renderSupervision(data) {
    if (!data.permissions?.supervision) return emptyState('Erişim kısıtlı');
    return emptyState('Süpervizyon kaydı yok', 'Vaka özeti ile talep oluşturabilirsiniz.');
  }

  function bindTabEvents() {
    body.querySelectorAll('.sws-tab').forEach((tab) => {
      tab.addEventListener('click', () => switchToTab(tab.dataset.tab));
      tab.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); switchToTab(tab.dataset.tab); } });
    });
    body.querySelectorAll('[data-open-session]').forEach((el) => el.addEventListener('click', () => openDrawer(el.dataset.openSession)));
  }

  function bindToolbar(data) {
    body.querySelector('[data-action="save-note"]')?.addEventListener('click', () => saveNote(false));
    body.querySelector('[data-action="sign"]')?.addEventListener('click', openSignModal);
    body.querySelector('[data-action="complete"]')?.addEventListener('click', openCompleteModal);
    body.querySelector('[data-action="homework"]')?.addEventListener('click', openHomeworkModal);
    body.querySelector('[data-action="test"]')?.addEventListener('click', openTestModal);
    body.querySelector('[data-action="appointment"]')?.addEventListener('click', openAppointmentModal);
    body.querySelector('[data-action="print"]')?.addEventListener('click', printSession);
    body.querySelector('[data-action="document"]')?.addEventListener('click', (e) => {
      e.preventDefault();
      openDocumentModal();
    });
    body.querySelector('#swsGenAi')?.addEventListener('click', generateAi);
  }

  function bindFormEvents() {
    body.querySelector('#swsSaveNote')?.addEventListener('click', () => saveNote(false));
    body.querySelectorAll('[data-note-field]').forEach((el) => el.addEventListener('input', () => { dirty = true; scheduleAutosave(); }));
    body.querySelector('#swsSavePlan')?.addEventListener('click', savePlan);
    body.querySelector('#swsSaveRisk')?.addEventListener('click', saveRisk);
  }

  function scheduleAutosave() {
    setAutosave('Kaydediliyor…', 'saving');
    clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(() => saveNote(true), 2000);
  }

  function saveNote(silent) {
    const form = body.querySelector('#swsNoteForm');
    if (!form || !currentData) return Promise.resolve();
    const tpl = form.querySelector('#swsNoteTemplate')?.value || 'free';
    const fields = {};
    form.querySelectorAll('[data-note-field]').forEach((el) => { fields[el.dataset.noteField] = el.value; });
    return postSave({ section: 'note', data: { template: tpl, status: currentData.note?.status || 'taslak', fields } }, silent);
  }

  function savePlan() {
    const planForm = body.querySelector('#swsPlanForm');
    if (!planForm) return;
    const data = {};
    let ageGroup = '';
    planForm.querySelectorAll('[name]').forEach((el) => {
      if (el.name === 'age_group') ageGroup = el.value;
      else data[el.name] = el.value;
    });
    const chain = postSave({ section: 'therapy_plan', data });
    const done = () => { toast('Terapi planı kaydedildi.'); loadWorkspace(currentId, 'plan'); };
    if (ageGroup) {
      chain.then(() => postSave({ section: 'age_group', data: ageGroup })).then(done);
    } else {
      chain.then(done);
    }
  }

  function saveRisk() {
    const riskForm = body.querySelector('#swsRiskForm');
    if (!riskForm) return;
    const data = {};
    riskForm.querySelectorAll('[name]').forEach((el) => { data[el.name] = el.value; });
    postSave({ section: 'risk', data }).then(() => toast('Risk kaydı güncellendi.'));
  }

  function postSave(payload, silent) {
    return fetch(`/admin/seans/${currentId}/workspace/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'fetch' },
      body: JSON.stringify(payload),
    }).then((r) => r.json().then((j) => ({ ok: r.ok, j }))).then(({ ok, j }) => {
      if (!ok) throw new Error(j.error || 'Kayıt hatası');
      dirty = false;
      setAutosave(silent ? 'Otomatik kaydedildi' : 'Kaydedildi', 'saved');
      setTimeout(() => setAutosave('', ''), 2500);
    }).catch((e) => { setAutosave(e.message, 'error'); if (!silent) toast(e.message, 'error'); });
  }

  function postAction(action, data, silent) {
    return fetch(`/admin/seans/${currentId}/workspace/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'fetch' },
      body: JSON.stringify({ action, data }),
    }).then((r) => r.json().then((j) => ({ ok: r.ok, j }))).then(({ ok, j }) => {
      if (!ok) throw new Error(j.error || 'İşlem hatası');
      if (j.payload) {
        currentData = j.payload;
        renderWorkspace(j.payload);
        initTimer(j.payload);
      } else if (currentId) {
        const tab = activeTab;
        return loadWorkspace(currentId, tab).then(() => j);
      }
      if (!silent) toast('İşlem başarılı.');
      return j;
    });
  }

  function openModal(title, html, onSubmit, submitLabel) {
    closeModal();
    const root = document.getElementById('swsModalRoot') || (() => {
      const d = document.createElement('div');
      d.id = 'swsModalRoot';
      document.body.appendChild(d);
      return d;
    })();
    root.innerHTML = `<div class="sws-modal-overlay" id="swsModalOverlay"><div class="sws-modal" role="dialog" aria-labelledby="swsModalTitle"><header class="sws-modal-head"><h3 id="swsModalTitle">${esc(title)}</h3><button type="button" class="sws-modal-close" aria-label="Kapat">×</button></header><div class="sws-modal-body">${html}</div><footer class="sws-modal-foot"><button type="button" class="btn btn-sm btn-ghost" data-modal-cancel>İptal</button><button type="button" class="btn btn-sm btn-primary" data-modal-submit>${esc(submitLabel || 'Kaydet')}</button></footer></div></div>`;
    root.hidden = false;
    requestAnimationFrame(() => root.querySelector('.sws-modal-overlay')?.classList.add('open'));
    root.querySelector('.sws-modal-close').onclick = closeModal;
    root.querySelector('[data-modal-cancel]').onclick = closeModal;
    root.querySelector('#swsModalOverlay').onclick = (e) => { if (e.target.id === 'swsModalOverlay') closeModal(); };
    root.querySelector('[data-modal-submit]').onclick = () => { onSubmit(root); };
    document.addEventListener('keydown', modalEscHandler);
  }

  function modalEscHandler(e) {
    if (e.key === 'Escape') closeModal();
  }

  function closeModal() {
    document.removeEventListener('keydown', modalEscHandler);
    const root = document.getElementById('swsModalRoot');
    if (root) { root.innerHTML = ''; root.hidden = true; }
  }

  function setModalLoading(loading) {
    const btn = document.querySelector('[data-modal-submit]');
    if (btn) { btn.disabled = loading; btn.textContent = loading ? 'Kaydediliyor…' : 'Kaydet'; }
  }

  function openHomeworkModal(existing) {
    const h = existing || {};
    const isEdit = Boolean(existing);
    const templates = (currentData?.homework_templates || []).map((t) => `<option value="${esc(t)}" ${h.template === t ? 'selected' : ''}>${esc(t)}</option>`).join('');
    const today = new Date().toISOString().slice(0, 10);
    const statusOpts = Object.entries(HW_STATUS).map(([k, v]) => `<option value="${k}" ${(h.status || 'atandi') === k ? 'selected' : ''}>${esc(v)}</option>`).join('');
    openModal(isEdit ? 'Ödevi Düzenle' : 'Ödev Oluştur', `
      <div class="sws-form-grid">
        <div class="sws-field"><label for="hw_title">Ödev başlığı</label><input id="hw_title" name="title" required value="${esc(h.title || '')}"></div>
        <div class="sws-field"><label for="hw_template">Hazır şablon</label><select id="hw_template" name="template"><option value="">Seçin</option>${templates}</select></div>
        <div class="sws-field"><label for="hw_desc">Açıklama</label><textarea id="hw_desc" name="description">${esc(h.description || '')}</textarea></div>
        <div class="sws-field"><label for="hw_start">Başlangıç</label><input type="date" id="hw_start" name="start_date" value="${esc(h.start_date || today)}"></div>
        <div class="sws-field"><label for="hw_due">Son teslim</label><input type="date" id="hw_due" name="due_date" value="${esc(h.due_date || '')}"></div>
        <div class="sws-field"><label for="hw_status">Durum</label><select id="hw_status" name="status">${statusOpts}</select></div>
        ${isEdit ? '' : '<div class="sws-field"><label for="hw_file">Dosya</label><input type="file" id="hw_file" name="file"><small class="muted">Dosya yükleme API entegrasyonu bekliyor; dosya adı kaydedilir.</small></div>'}
        <div class="sws-field"><label><input type="checkbox" id="hw_visible" name="visible" ${h.visible_to_client !== false ? 'checked' : ''}> Danışana görünür</label></div>
        <div class="sws-field"><label><input type="checkbox" id="hw_notify" name="notify" ${!isEdit ? 'checked' : ''}> Danışana bilgilendirme e-postası (kural açıksa)</label></div>
        <div class="sws-field"><label for="hw_note">Terapist notu</label><textarea id="hw_note" name="therapist_note">${esc(h.therapist_note || '')}</textarea></div>
      </div>`, (root) => {
      setModalLoading(true);
      const fileInput = root.querySelector('#hw_file');
      const data = {
        title: root.querySelector('#hw_title').value,
        template: root.querySelector('#hw_template').value,
        description: root.querySelector('#hw_desc').value,
        start_date: root.querySelector('#hw_start').value,
        due_date: root.querySelector('#hw_due').value,
        status: root.querySelector('#hw_status').value,
        visible_to_client: root.querySelector('#hw_visible').checked,
        notify_email: root.querySelector('#hw_notify')?.checked !== false,
        therapist_note: root.querySelector('#hw_note').value,
        file_name: fileInput?.files[0]?.name || h.file_name || '',
      };
      const action = isEdit ? 'update_homework' : 'homework';
      if (isEdit) data.id = h.id;
      postAction(action, data).then(() => {
        closeModal();
        toast(isEdit ? 'Ödev güncellendi.' : 'Ödev kaydedildi.');
        switchToTab('homework');
      }).catch((e) => { setModalLoading(false); toast(e.message, 'error'); });
    }, 'Kaydet');
    if (!isEdit) {
      const foot = document.querySelector('.sws-modal-foot');
      if (foot) {
        const draft = document.createElement('button');
        draft.type = 'button';
        draft.className = 'btn btn-sm btn-outline';
        draft.textContent = 'Taslak olarak kaydet';
        draft.onclick = () => {
          document.querySelector('#hw_status').value = 'taslak';
          document.querySelector('[data-modal-submit]').click();
        };
        foot.insertBefore(draft, foot.firstChild.nextSibling);
      }
    }
  }

  function openTestModal() {
    const tests = (currentData?.available_tests || []).map((t) => `<option value="${t.id}">${esc(t.title)}</option>`).join('');
    if (!tests) { toast('Aktif test bulunamadı.', 'error'); return; }
    const today = new Date().toISOString().slice(0, 10);
    openModal('Test Ata', `
      <div class="sws-form-grid">
        <div class="sws-field"><label>Test / Ölçek</label><select id="test_id" required><option value="">Seçin</option>${tests}</select></div>
        <div class="sws-field"><label>Uygulama türü</label><select id="test_phase"><option value="on_test">Ön test</option><option value="ara_test">Ara test</option><option value="son_test">Son test</option></select></div>
        <div class="sws-field"><label>Atama tarihi</label><input type="date" id="test_assigned" value="${today}"></div>
        <div class="sws-field"><label>Son tarih</label><input type="date" id="test_due"></div>
        <div class="sws-field"><label>Açıklama</label><textarea id="test_note"></textarea></div>
        <div class="sws-field"><label><input type="checkbox" id="test_send"> Danışana gönder</label></div>
      </div>`, () => {
      setModalLoading(true);
      postAction('assign_test', {
        test_id: parseInt(document.getElementById('test_id').value, 10),
        phase: document.getElementById('test_phase').value,
        assigned_date: document.getElementById('test_assigned').value,
        due_date: document.getElementById('test_due').value,
        note: document.getElementById('test_note').value,
        send_to_client: document.getElementById('test_send').checked,
      }).then(() => { closeModal(); toast('Test atandı.'); switchToTab('tests'); })
        .catch((e) => { setModalLoading(false); toast(e.message, 'error'); });
    });
  }

  function openAppointmentModal() {
    const m = currentData?.session_meta || {};
    const today = new Date().toISOString().slice(0, 10);
    openModal('Randevu Oluştur', `
      <div class="sws-form-grid">
        <div class="sws-field"><label>Danışan</label><input id="appt_patient" value="${esc(m.patient_name)}" readonly></div>
        <div class="sws-field"><label>Terapist</label><input value="${esc(m.therapist_name)}" readonly><input type="hidden" id="appt_therapist" value="${m.therapist_id || ''}"></div>
        <div class="sws-field"><label>Şube</label><input id="appt_city" value="${esc(m.city)}"></div>
        <div class="sws-field"><label>Tarih</label><input type="date" id="appt_date" value="${today}" required></div>
        <div class="sws-field"><label>Saat</label><input type="time" id="appt_time" value="10:00" required></div>
        <div class="sws-field"><label>Süre (dk)</label><input type="number" id="appt_duration" value="${m.duration_minutes || 50}"></div>
        <div class="sws-field"><label>Tür</label><select id="appt_type"><option value="yuz_yuze">Yüz Yüze</option><option value="online" ${m.session_type === 'online' ? 'selected' : ''}>Online</option></select></div>
        <div class="sws-field"><label>Açıklama</label><textarea id="appt_notes"></textarea></div>
      </div>`, () => {
      setModalLoading(true);
      postAction('appointment', {
        therapist_id: parseInt(document.getElementById('appt_therapist').value, 10),
        date: document.getElementById('appt_date').value,
        time: document.getElementById('appt_time').value,
        duration: document.getElementById('appt_duration').value,
        session_type: document.getElementById('appt_type').value,
        notes: document.getElementById('appt_notes').value,
      }).then(() => { closeModal(); toast('Randevu oluşturuldu.'); loadWorkspace(currentId, 'overview'); })
        .catch((e) => { setModalLoading(false); toast(e.message, 'error'); });
    });
  }

  function openSignModal() {
    if (!currentData?.permissions?.sign) return;
    openModal('Notu İmzala', `<p>İmzalandıktan sonra not düzenleme kısıtlanır. Değişiklik için gerekçe istenecektir.</p><p class="sws-warn">Devam etmek istiyor musunuz?</p>`, () => {
      setModalLoading(true);
      postAction('sign_note', {}).then(() => { closeModal(); toast('Not imzalandı.'); switchToTab('note'); })
        .catch((e) => { setModalLoading(false); toast(e.message, 'error'); });
    }, 'İmzala');
  }

  function openCompleteModal() {
    const c = currentData?.completion_checklist || {};
    const warnings = [];
    if (!c.timer_saved) warnings.push('Seans süresi henüz kaydedilmedi');
    if (!c.has_note) warnings.push('Seans notu eksik');
    if (!c.has_next_appointment) warnings.push('Sonraki randevu planlanmadı');
    if (!c.has_homework_or_task) warnings.push('Ödev veya takip görevi yok');
    warnings.push('Ödeme durumu: ' + (c.payment_status || '—'));
    openModal('Seansı Tamamla', `<ul class="sws-checklist">${warnings.map((w) => `<li>${esc(w)}</li>`).join('')}</ul><p>Eksik alanlar olsa bile tamamlamak istiyor musunuz?</p>`, () => {
      setModalLoading(true);
      postAction('complete', { force: true }).then(() => { closeModal(); toast('Seans tamamlandı.'); loadWorkspace(currentId, 'overview'); })
        .catch((e) => { setModalLoading(false); toast(e.message, 'error'); });
    }, 'Tamamla');
  }

  function printSession() {
    if (!currentData?.permissions?.print) { toast('Yazdırma yetkiniz yok.', 'error'); return; }
    const area = document.getElementById('swsPrintArea');
    if (!area) return;
    const o = currentData.overview || {};
    area.innerHTML = `<div class="sws-print-doc"><h1>Seans Özeti — ${esc(o.name)}</h1><p>${esc(currentData.header.subtitle)}</p><h2>Not</h2><p>${esc(o.note_preview_label)}</p><h2>Plan</h2><p>${esc(o.plan_summary_label)}</p></div>`;
    area.hidden = false;
    window.print();
    area.hidden = true;
  }

  function generateAi() {
    fetch(`/admin/seans/${currentId}/workspace/ai-summary`, { method: 'POST', headers: { 'X-Requested-With': 'fetch' } })
      .then((r) => r.json()).then((draft) => {
        if (draft.error) throw new Error(draft.error);
        currentData.ai_summary = draft;
        body.querySelector('#swsAiArea').innerHTML = renderAiSummary(currentData);
        toast('AI özeti oluşturuldu.');
      }).catch((e) => toast(e.message || 'AI özeti oluşturulamadı.', 'error'));
  }

  document.querySelectorAll('.sws-row-clickable').forEach((row) => {
    row.addEventListener('click', (e) => {
      if (e.target.closest('a, button, input, label, .sws-menu-wrap')) return;
      openDrawer(row.dataset.sessionId);
    });
    row.addEventListener('keydown', (e) => { if (e.key === 'Enter') openDrawer(row.dataset.sessionId); });
  });
  document.querySelectorAll('.js-sws-open').forEach((btn) => btn.addEventListener('click', (e) => { e.stopPropagation(); openDrawer(btn.dataset.sessionId); }));

  document.querySelectorAll('.sws-menu-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const menu = btn.nextElementSibling;
      if (!menu?.classList.contains('sws-menu')) return;
      const open = !menu.hidden;
      document.querySelectorAll('.sws-menu').forEach((m) => { m.hidden = true; });
      menu.hidden = open;
    });
  });

  document.querySelectorAll('.sws-menu [data-menu-action]').forEach((item) => {
    item.addEventListener('click', (e) => {
      e.stopPropagation();
      const action = item.dataset.menuAction;
      const id = item.dataset.id;
      document.querySelectorAll('.sws-menu').forEach((m) => { m.hidden = true; });
      if (action === 'client' || action === 'session') openDrawer(id);
      else if (action === 'note') openDrawer(id, 'note');
      else if (action === 'documents') openDrawer(id, 'documents');
      else if (action === 'tests') openDrawer(id, 'tests');
      else if (action === 'appointment') window.location.href = `/admin/randevular?q=${encodeURIComponent(item.closest('.sws-board-row')?.dataset.clientEmail || '')}`;
    });
  });

  document.addEventListener('click', () => {
    document.querySelectorAll('.sws-menu').forEach((m) => { m.hidden = true; });
  });

  const filterToggle = document.getElementById('swsFilterToggle');
  const filterAdvanced = document.getElementById('swsFilterAdvanced');
  filterToggle?.addEventListener('click', () => {
    const open = filterAdvanced?.hidden !== false;
    if (filterAdvanced) filterAdvanced.hidden = !open;
    filterAdvanced?.classList.toggle('is-open', open);
    filterToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  document.querySelectorAll('.sws-date-preset').forEach((btn) => {
    btn.addEventListener('click', () => {
      const preset = btn.dataset.preset;
      const presetInput = document.getElementById('date_preset');
      const customDates = document.getElementById('swsCustomDates');
      if (presetInput) presetInput.value = preset;
      document.querySelectorAll('.sws-date-preset').forEach((b) => b.classList.toggle('is-active', b === btn));
      if (customDates) customDates.hidden = preset !== 'custom';
      if (preset !== 'custom') document.getElementById('swsFilterForm')?.requestSubmit();
    });
  });

  if (window.SWS_OPEN_SESSION) openDrawer(window.SWS_OPEN_SESSION);

  const closeBtn = document.getElementById('swsDrawerClose');
  closeBtn?.addEventListener('click', closeDrawer);
  closeBtn?.classList.add('sws-drawer-close-lg');
  overlay?.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !drawer.hidden && !document.getElementById('swsModalRoot')?.innerHTML) closeDrawer(); });
})();