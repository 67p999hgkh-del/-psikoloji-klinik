(function () {
  'use strict';

  const form = document.getElementById('apptCreateForm');
  if (!form) return;

  let clients = [];
  try {
    const raw = document.getElementById('apfClientsData');
    clients = raw ? JSON.parse(raw.textContent || '[]') : [];
  } catch (e) {
    clients = [];
  }

  const byEmail = {};
  clients.forEach((c) => {
    if (c && c.email) byEmail[String(c.email).toLowerCase()] = c;
  });

  const search = document.getElementById('clientSearch');
  const profileId = document.getElementById('clientProfileId');
  const nameInput = document.getElementById('patient_name');
  const emailInput = document.getElementById('patient_email');
  const phoneInput = document.getElementById('patient_phone');
  const chip = document.getElementById('apfClientChip');
  const chipName = document.getElementById('apfChipName');
  const chipEmail = document.getElementById('apfChipEmail');
  const chipPending = document.getElementById('apfChipPending');
  const clearBtn = document.getElementById('apfClearClient');

  function setLocked(locked) {
    if (nameInput) nameInput.readOnly = locked;
    if (emailInput) emailInput.readOnly = locked;
  }

  function applyClient(c) {
    if (!c) return;
    profileId.value = c.id || '';
    nameInput.value = c.full_name || '';
    emailInput.value = c.email || '';
    phoneInput.value = c.phone || phoneInput.value || '';
    if (chipName) chipName.textContent = c.full_name || c.email || '';
    if (chipEmail) {
      chipEmail.textContent = c.phone ? `${c.email} · ${c.phone}` : (c.email || '');
    }
    if (chipPending) chipPending.hidden = !c.pending;
    if (chip) chip.hidden = false;
    setLocked(true);
  }

  function clearClient() {
    profileId.value = '';
    if (chip) chip.hidden = true;
    if (chipPending) chipPending.hidden = true;
    setLocked(false);
    if (search) search.value = '';
  }

  function matchFromSearch() {
    const q = (search.value || '').trim().toLowerCase();
    if (!q) return;
    let found = byEmail[q];
    if (!found) {
      found = clients.find((c) => {
        const name = String(c.full_name || '').toLowerCase();
        const email = String(c.email || '').toLowerCase();
        return name === q || email === q || name.includes(q) || email.includes(q);
      });
    }
    if (found) applyClient(found);
  }

  search?.addEventListener('change', matchFromSearch);
  search?.addEventListener('blur', matchFromSearch);
  clearBtn?.addEventListener('click', () => {
    clearClient();
    nameInput.value = '';
    emailInput.value = '';
    phoneInput.value = '';
    nameInput.focus();
  });

  form.addEventListener('submit', (e) => {
    const missing = [];
    if (!(nameInput.value || '').trim()) missing.push('Ad soyad');
    if (!(emailInput.value || '').trim()) missing.push('E-posta');
    if (!(phoneInput.value || '').trim()) missing.push('Telefon');
    const therapist = form.querySelector('[name="therapist_id"]');
    if (therapist && !(therapist.value || '').trim()) missing.push('Terapist');
    if (!(form.appointment_date?.value || '').trim()) missing.push('Tarih');
    if (!(form.appointment_time?.value || '').trim()) missing.push('Saat');
    if (missing.length) {
      e.preventDefault();
      alert('Zorunlu alanlar: ' + missing.join(', '));
    }
  });
})();
