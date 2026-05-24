/* ═══════════════════════════════════════════════════════════
   student/reservation.js  —  Interactive PC Map
   ═══════════════════════════════════════════════════════════ */

// Lab configs: how many PCs each lab has
const LAB_CONFIG = {
  'Lab 1': 30,
  'Lab 2': 25,
  'Lab 3': 20,
};

// Injected from template
const allReservations = window.RESERVATIONS || [];
// Admin-set PC status: { "Lab 1": { "1": "available", "2": "unavailable", ... }, ... }
const pcStatus = window.PC_STATUS || {};

// Currently selected PC number
let selectedPC = null;

// ── DOM refs ──────────────────────────────────────────────────
const labSelect     = document.getElementById('labSelect');
const dateInput     = document.getElementById('dateInput');
const timeSlot      = document.getElementById('timeSlot');
const pcGrid        = document.getElementById('pcGrid');
const selectedInfo  = document.getElementById('selectedInfo');
const pcNumberInput = document.getElementById('pcNumberInput');
const submitBtn     = document.getElementById('submitBtn');
const labNameTag    = document.getElementById('labNameTag');

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const today = new Date().toISOString().split('T')[0];
  dateInput.setAttribute('min', today);
  dateInput.value = today;

  renderGrid();

  labSelect.addEventListener('change', renderGrid);
  dateInput.addEventListener('change', renderGrid);
  timeSlot.addEventListener('change', renderGrid);
});

// ── Determine the effective state of a PC ─────────────────────
// Priority: admin status (unavailable/under_maintenance/reserved) > reservation conflict > available
function getPCState(lab, pcNum, date, slot) {
  // 1. Check admin-set status first
  const adminStatus = (pcStatus[lab] || {})[String(pcNum)] || 'available';

  if (adminStatus === 'unavailable')       return 'unavailable';
  if (adminStatus === 'under_maintenance') return 'maintenance';
  // 'reserved' set by admin means permanently reserved (not student-bookable)
  if (adminStatus === 'reserved')          return 'admin_reserved';

  // 2. Check student reservations for this lab/date/slot
  for (const r of allReservations) {
    if (r.lab !== lab || r.pc_number !== pcNum) continue;
    if ((r.status === 'APPROVED' || r.status === 'PENDING') && r.date === date && r.time_slot === slot) {
      return 'reserved';
    }
  }

  return 'available';
}

// ── Build the PC grid ─────────────────────────────────────────
function renderGrid() {
  const lab      = labSelect.value;
  const date     = dateInput.value;
  const slot     = timeSlot.value;
  const totalPCs = LAB_CONFIG[lab] || 30;

  labNameTag.textContent = lab;

  // Reset selection
  selectedPC = null;
  pcNumberInput.value = '';
  updateSubmitState();
  updateSelectedInfo();

  pcGrid.innerHTML = '';

  for (let i = 1; i <= totalPCs; i++) {
    const state = getPCState(lab, i, date, slot);
    const isSelectable = state === 'available';

    const tile = document.createElement('div');
    tile.classList.add('pc-cell', 'pc-' + state);
    tile.dataset.pc    = i;
    tile.dataset.state = state;

    const numberLabel = document.createElement('span');
    numberLabel.classList.add('pc-num');
    numberLabel.textContent = i;

    const icon = document.createElement('span');
    icon.classList.add('pc-icon');
    icon.textContent = '🖥️';

    const statusLabel = document.createElement('span');
    statusLabel.classList.add('pc-status');
    statusLabel.textContent = isSelectable ? 'Available' : (state === 'maintenance' ? 'Maintenance' : (state === 'admin_reserved' ? 'Reserved' : state.charAt(0).toUpperCase() + state.slice(1)));

    tile.appendChild(numberLabel);
    tile.appendChild(icon);
    tile.appendChild(statusLabel);

    if (isSelectable) {
      tile.addEventListener('click', () => selectPC(i, tile));
    } else {
      tile.style.cursor = 'not-allowed';
      const tooltips = {
        reserved:       'Already reserved for this slot',
        admin_reserved: 'Reserved — not available for booking',
        unavailable:    'PC is currently unavailable',
        maintenance:    'PC is under maintenance',
      };
      tile.title = tooltips[state] || 'Not available';
    }

    pcGrid.appendChild(tile);
  }
}

// ── Select a PC ───────────────────────────────────────────────
function selectPC(pcNum, tile) {
  const prev = pcGrid.querySelector('.pc-selected');
  if (prev) {
    prev.classList.remove('pc-selected');
    prev.classList.add('pc-available');
  }

  if (selectedPC === pcNum) {
    selectedPC = null;
    pcNumberInput.value = '';
  } else {
    selectedPC = pcNum;
    pcNumberInput.value = pcNum;
    tile.classList.remove('pc-available');
    tile.classList.add('pc-selected');
  }

  updateSubmitState();
  updateSelectedInfo();
}

// ── Submit state ──────────────────────────────────────────────
function updateSubmitState() {
  const ready = selectedPC !== null;
  submitBtn.disabled = !ready;
}

// ── Info bar ──────────────────────────────────────────────────
function updateSelectedInfo() {
  const selectedInfo = document.getElementById('selectedInfo');
  if (selectedPC === null) {
    selectedInfo.textContent = 'No PC selected — click one above to choose.';
    selectedInfo.classList.remove('has-selection');
  } else {
    selectedInfo.textContent =
      `✔ PC ${selectedPC} — ${labSelect.value} · ${dateInput.value} · ${timeSlot.value}`;
    selectedInfo.classList.add('has-selection');
  }
}

// ── Validate on submit ────────────────────────────────────────
document.getElementById('reservationForm').addEventListener('submit', (e) => {
  if (!selectedPC) {
    e.preventDefault();
    alert('Please select a PC from the map first.');
  }
});
