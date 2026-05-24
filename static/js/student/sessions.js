// ── Sessions JS ───────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Highlight active sessions
  document.querySelectorAll('.badge-active').forEach(badge => {
    badge.closest('tr')?.classList.add('highlight-row');
  });
});
