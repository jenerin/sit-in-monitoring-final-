// ── Admin Reservation JS ──────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {

  // ── Lab Tabs ──────────────────────────────────────────────
  const tabs = document.querySelectorAll('.lab-tab');
  const panels = document.querySelectorAll('.pc-grid-panel');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const labId = tab.dataset.lab.replace(/ /g, '-');
      const panel = document.getElementById('panel-' + labId);
      if (panel) panel.classList.add('active');
    });
  });

  // ── PC Status Dropdowns ───────────────────────────────────
  document.querySelectorAll('.pc-status-select').forEach(select => {
    select.addEventListener('change', async () => {
      const lab = select.dataset.lab;
      const pc  = select.dataset.pc;
      const status = select.value;

      const cell = select.closest('.pc-cell');
      cell.className = 'pc-cell pc-' + status;
      cell.classList.remove('selected');
      refreshCounts();

      try {
        const formData = new FormData();
        formData.append('lab', lab);
        formData.append('pc', pc);
        formData.append('status', status);

        const res = await fetch('/admin/reservation/pc-status', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();

        if (!data.success) {
          console.error('Failed to update PC status:', data.error);
          showToast('Failed to update PC status.', 'error');
        } else {
          showToast(`PC ${pc} set to ${status.replace('_', ' ')}.`, 'success');
        }
      } catch (err) {
        console.error('Error updating PC status:', err);
        showToast('Network error. Please try again.', 'error');
      }
    });
  });

  const pcCells = Array.from(document.querySelectorAll('.pc-cell'));
  const bulkButtons = document.querySelectorAll('.btn-bulk');
  const selectedButtons = document.querySelectorAll('.btn-selected');
  const clearSelectionBtn = document.getElementById('clear-selection');

  function getActivePanel() {
    return document.querySelector('.pc-grid-panel.active');
  }

  function refreshCounts() {
    const panel = getActivePanel();
    if (!panel) return;

    const cells = Array.from(panel.querySelectorAll('.pc-cell'));
    const counts = { available: 0, reserved: 0, unavailable: 0, under_maintenance: 0, selected: 0 };

    cells.forEach(cell => {
      const statusSelect = cell.querySelector('.pc-status-select');
      const status = statusSelect ? statusSelect.value : '';
      if (counts[status] !== undefined) counts[status] += 1;
      if (cell.classList.contains('selected')) counts.selected += 1;
    });

    document.querySelector('.count-available').textContent = counts.available;
    document.querySelector('.count-reserved').textContent = counts.reserved;
    document.querySelector('.count-unavailable').textContent = counts.unavailable;
    document.querySelector('.count-maintenance').textContent = counts.under_maintenance;
    document.querySelector('.count-selected').textContent = counts.selected;
  }

  function updateCellStatus(cell, status) {
    const select = cell.querySelector('.pc-status-select');
    if (select) {
      select.value = status;
    }
    cell.className = 'pc-cell pc-' + status;
  }

  async function sendBulkUpdate(lab, status, pcNumbers = []) {
    try {
      const formData = new FormData();
      formData.append('lab', lab);
      formData.append('status', status);
      if (pcNumbers.length) {
        formData.append('pcs', pcNumbers.join(','));
      }

      const res = await fetch('/admin/reservation/pc-status/bulk', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();

      if (data.success) {
        showToast(`Updated ${pcNumbers.length ? 'selected PCs' : 'all PCs'} to ${status.replace('_', ' ')}.`, 'success');
        return true;
      }
      console.error('Bulk update failed:', data.error);
      showToast('Bulk update failed.', 'error');
    } catch (err) {
      console.error('Bulk update error:', err);
      showToast('Network error. Please try again.', 'error');
    }
    return false;
  }

  pcCells.forEach(cell => {
    cell.addEventListener('click', event => {
      const target = event.target;
      if (target.closest('.pc-actions') || target.closest('select')) return;
      cell.classList.toggle('selected');
      refreshCounts();
    });
  });

  bulkButtons.forEach(button => {
    button.addEventListener('click', async () => {
      const panel = getActivePanel();
      if (!panel) return;
      const lab = button.closest('.pc-map-card').querySelector('.lab-tab.active').dataset.lab;
      const status = button.dataset.bulk;
      const success = await sendBulkUpdate(lab, status);
      if (success) {
        const cells = Array.from(panel.querySelectorAll('.pc-cell'));
        cells.forEach(cell => updateCellStatus(cell, status));
        refreshCounts();
      }
    });
  });

  selectedButtons.forEach(button => {
    button.addEventListener('click', async () => {
      const panel = getActivePanel();
      if (!panel) return;
      const lab = button.closest('.pc-map-card').querySelector('.lab-tab.active').dataset.lab;
      const status = button.dataset.action;
      const selectedCells = Array.from(panel.querySelectorAll('.pc-cell.selected'));
      if (!selectedCells.length) {
        showToast('Select one or more PCs first.', 'error');
        return;
      }
      const pcNumbers = selectedCells.map(cell => cell.dataset.pc);
      const success = await sendBulkUpdate(lab, status, pcNumbers);
      if (success) {
        selectedCells.forEach(cell => {
          updateCellStatus(cell, status);
          cell.classList.remove('selected');
        });
        refreshCounts();
      }
    });
  });

  clearSelectionBtn?.addEventListener('click', () => {
    const selectedCells = document.querySelectorAll('.pc-cell.selected');
    selectedCells.forEach(cell => cell.classList.remove('selected'));
    refreshCounts();
  });

  document.querySelectorAll('.lab-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      setTimeout(refreshCounts, 0);
    });
  });

  refreshCounts();

  // ── Highlight pending reservations ───────────────────────
  document.querySelectorAll('.badge-pending').forEach(badge => {
    badge.closest('tr')?.style.setProperty('background', 'rgba(245,158,11,.04)');
  });

  // ── Toast helper ─────────────────────────────────────────
  function showToast(msg, type = 'success') {
    const existing = document.querySelector('.pc-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'pc-toast';
    toast.textContent = msg;
    toast.style.cssText = `
      position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 9999;
      background: ${type === 'success' ? 'rgba(0,242,195,.15)' : 'rgba(239,68,68,.15)'};
      color: ${type === 'success' ? '#00f2c3' : '#ef4444'};
      border: 1px solid ${type === 'success' ? 'rgba(0,242,195,.35)' : 'rgba(239,68,68,.35)'};
      padding: .65rem 1.25rem; border-radius: 10px;
      font-size: .85rem; font-weight: 600;
      box-shadow: 0 4px 20px rgba(0,0,0,.3);
      animation: fadeInUp .2s ease;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2500);
  }

});
