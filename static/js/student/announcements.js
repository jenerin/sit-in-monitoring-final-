// ── Announcements JS ──────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Animate announcement items on load
  document.querySelectorAll('.announcement-item').forEach((item, i) => {
    item.style.opacity = '0';
    item.style.transform = 'translateY(10px)';
    item.style.transition = `opacity .3s ease ${i * 0.08}s, transform .3s ease ${i * 0.08}s`;
    setTimeout(() => {
      item.style.opacity = '1';
      item.style.transform = 'translateY(0)';
    }, 50);
  });
});
