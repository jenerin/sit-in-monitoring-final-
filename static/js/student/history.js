// ── History JS ────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Highlight active sessions in history table
  document.querySelectorAll('.badge-active').forEach(badge => {
    badge.closest('tr')?.classList.add('highlight-row');
  });
});
