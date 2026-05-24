// ── Admin Announcements JS ────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  const textarea = document.querySelector('textarea[name="body"]');
  const counter = document.getElementById('charCount');
  if (textarea && counter) {
    textarea.addEventListener('input', () => {
      counter.textContent = textarea.value.length;
    });
  }
});
