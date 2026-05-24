// ── Records JS ────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Highlight active rows
  document.querySelectorAll('.badge-active').forEach(badge => {
    badge.closest('tr')?.classList.add('highlight-row');
  });
});
