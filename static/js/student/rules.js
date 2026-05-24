// ── Rules JS ──────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Animate rule items on load
  document.querySelectorAll('.rule-item').forEach((item, i) => {
    item.style.opacity = '0';
    item.style.transform = 'translateX(-10px)';
    item.style.transition = `opacity .3s ease ${i * 0.06}s, transform .3s ease ${i * 0.06}s`;
    setTimeout(() => {
      item.style.opacity = '1';
      item.style.transform = 'translateX(0)';
    }, 50);
  });
});
