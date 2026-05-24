// ── Rewards JS ────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Highlight the current student's row in the leaderboard
  const highlightRow = document.querySelector('.highlight-row');
  if (highlightRow) {
    highlightRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
});
