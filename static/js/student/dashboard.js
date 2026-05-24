// ── Student Dashboard JS ──────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Animate stat card values on load
  document.querySelectorAll('.stat-value').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(8px)';
    el.style.transition = 'opacity .4s ease, transform .4s ease';
    setTimeout(() => {
      el.style.opacity = '1';
      el.style.transform = 'translateY(0)';
    }, 100);
  });

});
