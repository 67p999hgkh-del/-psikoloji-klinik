(function () {
  'use strict';

  const bulkForm = document.getElementById('swsBulkForm');
  const bulkBar = bulkForm;
  const countEl = document.getElementById('swsBulkCount');
  const bulkAction = document.getElementById('swsBulkAction');
  const therapistWrap = document.getElementById('swsBulkTherapistWrap');
  const therapistSelect = document.getElementById('swsBulkTherapist');

  function rowChecks() {
    return Array.from(document.querySelectorAll('.sws-row-select'));
  }

  function selectedIds() {
    return rowChecks().filter((c) => c.checked).map((c) => c.value);
  }

  function syncBulkUi() {
    const checks = rowChecks();
    const selected = checks.filter((c) => c.checked);
    if (countEl) countEl.textContent = String(selected.length);
    if (bulkBar) bulkBar.hidden = selected.length === 0;
    const allOn = checks.length > 0 && selected.length === checks.length;
    const some = selected.length > 0 && !allOn;
    ['swsSelectAll', 'swsSelectAllHead'].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.checked = allOn;
      el.indeterminate = some;
    });
    checks.forEach((cb) => {
      cb.closest('.sws-board-row')?.classList.toggle('is-selected', cb.checked);
    });
  }

  function setAll(checked) {
    rowChecks().forEach((cb) => { cb.checked = checked; });
    syncBulkUi();
  }

  function toast(msg) {
    let el = document.getElementById('swsListToast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'swsListToast';
      el.className = 'sws-toast sws-toast-info show';
      el.setAttribute('role', 'status');
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.className = 'sws-toast sws-toast-info show';
    setTimeout(() => el.classList.remove('show'), 4000);
  }

  function submitBulk(action) {
    const ids = selectedIds();
    if (!ids.length || !bulkForm || !bulkAction) return;

    if (action === 'delete' && !window.confirm(`${ids.length} seans kaydı kalıcı olarak silinsin mi?`)) {
      return;
    }
    if (action === 'therapist') {
      if (therapistWrap) therapistWrap.hidden = false;
      const tid = therapistSelect?.value;
      if (!tid) {
        toast('Terapist değiştirmek için listeden terapist seçin, ardından tekrar tıklayın.');
        therapistSelect?.focus();
        return;
      }
    } else if (therapistWrap) {
      therapistWrap.hidden = true;
    }

    if (action === 'mail' && !window.confirm(`${ids.length} danışana bilgilendirme e-postası kuyruğa alınsın mı?`)) {
      return;
    }

    bulkAction.value = action;
    bulkForm.submit();
  }

  rowChecks().forEach((cb) => {
    cb.addEventListener('click', (e) => e.stopPropagation());
    cb.addEventListener('change', syncBulkUi);
  });

  ['swsSelectAll', 'swsSelectAllHead'].forEach((id) => {
    document.getElementById(id)?.addEventListener('change', (e) => setAll(e.target.checked));
  });

  document.querySelectorAll('[data-bulk]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const ids = selectedIds();
      if (!ids.length) return;
      const action = btn.dataset.bulk;
      if (action === 'export') {
        window.open(`/admin/seanslar/disa-aktar?ids=${ids.join(',')}`, '_blank');
        return;
      }
      submitBulk(action);
    });
  });

  syncBulkUi();
})();
