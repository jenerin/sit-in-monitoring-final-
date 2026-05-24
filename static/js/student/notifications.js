// ── Notifications JS ──────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Animate notification items
  document.querySelectorAll('.notif-item').forEach((item, i) => {
    item.style.opacity = '0';
    item.style.transform = 'translateY(8px)';
    item.style.transition = `opacity .3s ease ${i * 0.07}s, transform .3s ease ${i * 0.07}s`;
    setTimeout(() => {
      item.style.opacity = '1';
      item.style.transform = 'translateY(0)';
    }, 50);
  });
});
