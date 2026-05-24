// ── Admin Dashboard JS ────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Animate stat cards
  document.querySelectorAll('.stat-card').forEach((card, i) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(12px)';
    card.style.transition = `opacity .35s ease ${i * 0.07}s, transform .35s ease ${i * 0.07}s`;
    setTimeout(() => {
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, 50);
  });
});
