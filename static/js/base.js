// ── Base JS — CCS Sit-in Monitor ─────────────────────────────

// Auto-dismiss flash messages after 4 seconds
document.addEventListener('DOMContentLoaded', () => {
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(flash => {
    setTimeout(() => {
      flash.style.transition = 'opacity .4s ease';
      flash.style.opacity = '0';
      setTimeout(() => flash.remove(), 400);
    }, 4000);
  });

  // Dark mode initialization + toggle support
  const darkModeToggle = document.getElementById('darkModeToggle');
  const savedDarkMode = localStorage.getItem('darkMode') || localStorage.getItem('theme');
  const isDarkMode = savedDarkMode === 'enabled' || savedDarkMode === 'true' || savedDarkMode === 'dark';

  if (isDarkMode) {
    document.body.classList.add('dark-mode');
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.body.classList.remove('dark-mode');
    document.documentElement.setAttribute('data-theme', 'light');
  }

  if (darkModeToggle) {
    darkModeToggle.textContent = isDarkMode ? '☀️' : '🌙';
    darkModeToggle.addEventListener('click', () => {
      const active = document.body.classList.toggle('dark-mode');
      darkModeToggle.textContent = active ? '☀️' : '🌙';
      localStorage.setItem('darkMode', active ? 'enabled' : 'disabled');
      localStorage.setItem('theme', active ? 'dark' : 'light');
      document.documentElement.setAttribute('data-theme', active ? 'dark' : 'light');
    });
  }
});
