// Filter repository cards by name or language.
document.getElementById('q').addEventListener('input', (e) => {
  const q = e.target.value.trim().toLowerCase();
  document.querySelectorAll('.card').forEach((c) => {
    c.hidden = q && !(c.dataset.name.includes(q) || c.dataset.lang.includes(q));
  });
});
