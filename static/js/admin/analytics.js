// ── Analytics JS ──────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Animate bar fills
  document.querySelectorAll('.bar-fill').forEach(bar => {
    const target = bar.style.width;
    bar.style.width = '0';
    setTimeout(() => {
      bar.style.transition = 'width .7s ease';
      bar.style.width = target;
    }, 100);
  });
});
