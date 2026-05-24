// ── Reports JS ────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Print report button support
  const printBtn = document.getElementById('printReport');
  if (printBtn) {
    printBtn.addEventListener('click', () => window.print());
  }
});
