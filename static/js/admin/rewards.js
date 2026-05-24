// ── Admin Rewards JS ──────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Highlight top 3 rows
  const rows = document.querySelectorAll('.data-table tbody tr');
  rows.forEach((row, i) => {
    if (i === 0) row.style.background = 'rgba(245,158,11,.08)';
    else if (i === 1) row.style.background = 'rgba(148,163,184,.05)';
    else if (i === 2) row.style.background = 'rgba(180,83,9,.05)';
  });
});
