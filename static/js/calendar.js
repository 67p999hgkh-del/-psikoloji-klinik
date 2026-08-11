document.addEventListener('DOMContentLoaded', () => {
  const calendarEl = document.querySelector('.calendar-booking');
  if (!calendarEl) return;

  const therapistId = calendarEl.dataset.therapistId;
  const daysEl = calendarEl.querySelector('.cal-days');
  const monthLabel = calendarEl.querySelector('.cal-month-label');
  const prevBtn = calendarEl.querySelector('.cal-prev');
  const nextBtn = calendarEl.querySelector('.cal-next');
  const slotsPanel = calendarEl.querySelector('.time-slots-panel');
  const slotsEl = calendarEl.querySelector('.time-slots');
  const dateLabel = calendarEl.querySelector('.selected-date-label');
  const dateInput = document.getElementById('appointment_date');
  const timeInput = document.getElementById('appointment_time');
  const slotInfo = document.getElementById('selectedSlotInfo');
  const submitBtn = document.getElementById('submitBtn');
  const msgEmpty = calendarEl.dataset.msgEmpty || 'Henüz tarih ve saat seçilmedi.';
  const msgSelectedPrefix = calendarEl.dataset.msgSelected || 'Seçilen:';

  const monthNames = [
    'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
    'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
  ];

  let currentYear = new Date().getFullYear();
  let currentMonth = new Date().getMonth() + 1;
  let availability = null;
  let selectedDate = null;
  let selectedTime = null;

  function formatDisplayDate(isoDate) {
    const [y, m, d] = isoDate.split('-');
    return `${d}.${m}.${y}`;
  }

  function updateSlotInfo() {
    if (!slotInfo) return;
    if (selectedDate && selectedTime) {
      slotInfo.textContent = `${msgSelectedPrefix} ${formatDisplayDate(selectedDate)} — ${selectedTime}`;
      slotInfo.classList.add('has-selection');
      if (submitBtn) submitBtn.disabled = false;
    } else {
      slotInfo.textContent = msgEmpty;
      slotInfo.classList.remove('has-selection');
      if (submitBtn) submitBtn.disabled = true;
    }
  }

  function selectSlot(date, time) {
    selectedDate = date;
    selectedTime = time;
    if (dateInput) dateInput.value = date;
    if (timeInput) timeInput.value = time;
    updateSlotInfo();
  }

  function renderTimeSlots(dayData, dateKey) {
    slotsEl.innerHTML = '';
    dateLabel.textContent = formatDisplayDate(dateKey);
    slotsPanel.classList.remove('hidden');

    Object.entries(dayData.slots).forEach(([hour, status]) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `time-slot time-slot-${status}`;
      btn.textContent = hour;

      if (status === 'available') {
        btn.addEventListener('click', () => {
          slotsEl.querySelectorAll('.time-slot-selected').forEach((el) => {
            el.classList.remove('time-slot-selected');
          });
          btn.classList.add('time-slot-selected');
          selectSlot(dateKey, hour);
        });

        if (selectedDate === dateKey && selectedTime === hour) {
          btn.classList.add('time-slot-selected');
        }
      } else if (status === 'busy') {
        btn.disabled = true;
        btn.title = 'Dolu';
      } else {
        btn.disabled = true;
      }

      slotsEl.appendChild(btn);
    });
  }

  function renderCalendar() {
    if (!availability) return;

    monthLabel.textContent = `${monthNames[currentMonth - 1]} ${currentYear}`;
    daysEl.innerHTML = '';

    const firstDay = new Date(currentYear, currentMonth - 1, 1);
    let startPad = firstDay.getDay() - 1;
    if (startPad < 0) startPad = 6;

    for (let i = 0; i < startPad; i += 1) {
      const empty = document.createElement('div');
      empty.className = 'cal-day empty';
      daysEl.appendChild(empty);
    }

    Object.entries(availability.days).forEach(([dateKey, dayData]) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `cal-day cal-day-${dayData.status}`;
      btn.textContent = dateKey.split('-')[2].replace(/^0/, '');

      if (dayData.status === 'closed' || dayData.status === 'full') {
        btn.disabled = true;
      } else {
        btn.addEventListener('click', () => {
          daysEl.querySelectorAll('.cal-day-selected').forEach((el) => {
            el.classList.remove('cal-day-selected');
          });
          btn.classList.add('cal-day-selected');
          renderTimeSlots(dayData, dateKey);
        });
      }

      if (selectedDate === dateKey) {
        btn.classList.add('cal-day-selected');
      }

      daysEl.appendChild(btn);
    });
  }

  async function loadAvailability() {
    const response = await fetch(`/api/randevu/musaitlik/${therapistId}?year=${currentYear}&month=${currentMonth}`);
    availability = await response.json();
    renderCalendar();

    if (selectedDate && availability.days[selectedDate]) {
      renderTimeSlots(availability.days[selectedDate], selectedDate);
    }
  }

  prevBtn.addEventListener('click', () => {
    currentMonth -= 1;
    if (currentMonth < 1) {
      currentMonth = 12;
      currentYear -= 1;
    }
    loadAvailability();
  });

  nextBtn.addEventListener('click', () => {
    currentMonth += 1;
    if (currentMonth > 12) {
      currentMonth = 1;
      currentYear += 1;
    }
    loadAvailability();
  });

  loadAvailability();
  updateSlotInfo();
});
