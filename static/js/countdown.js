/**
 * countdown.js
 * Manejo del contador regresivo para el Festival de la Leyenda Vallenata 2027
 */

document.addEventListener('DOMContentLoaded', () => {
  initCountdown();
});

function initCountdown() {
  const daysEl = document.getElementById('count-days');
  const hoursEl = document.getElementById('count-hours');
  const minutesEl = document.getElementById('count-minutes');
  const secondsEl = document.getElementById('count-seconds');

  // Si no existen los elementos en la vista actual, salir
  if (!daysEl || !hoursEl || !minutesEl || !secondsEl) return;

  // La fecha de inicio viene de la edición vigente en la base de datos (data-inicio en index.html).
  // Sin edición no hay a qué contar: se dejan los guiones del diseño.
  const inicio = document.querySelector('[data-inicio]')?.dataset.inicio;
  if (!inicio) return;
  const targetDate = new Date(`${inicio}T00:00:00`).getTime();

  function update() {
    const now = new Date().getTime();
    const distance = targetDate - now;

    if (distance > 0) {
      const days = Math.floor(distance / (1000 * 60 * 60 * 24));
      const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((distance % (1000 * 60)) / 1000);

      daysEl.textContent = String(days).padStart(2, '0');
      hoursEl.textContent = String(hours).padStart(2, '0');
      minutesEl.textContent = String(minutes).padStart(2, '0');
      secondsEl.textContent = String(seconds).padStart(2, '0');
    } else {
      daysEl.textContent = '--';
      hoursEl.textContent = '--';
      minutesEl.textContent = '--';
      secondsEl.textContent = '--';
    }
  }

  // Se pinta de una vez para no mostrar guiones durante el primer segundo.
  update();
  setInterval(update, 1000);
}
