function toggleTactics(header) {
  const body = header.nextElementSibling;
  const icon = header.querySelector('.toggle-icon');
  const isOpen = body.classList.contains('open');
  body.classList.toggle('open', !isOpen);
  icon.style.transform = isOpen ? '' : 'rotate(180deg)';
}

// Auto-open tactics for top 3 trends on load
document.addEventListener('DOMContentLoaded', () => {
  const headers = document.querySelectorAll('.tactics-header');
  headers.forEach((h, i) => {
    if (i < 3) {
      h.nextElementSibling.classList.add('open');
      h.querySelector('.toggle-icon').style.transform = 'rotate(180deg)';
    }
  });
});
