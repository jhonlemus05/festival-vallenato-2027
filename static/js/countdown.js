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

  // Fecha tentativa de inicio de la 60ª edición (Abril 2027)
  const targetDate = new Date('2027-04-26T08:00:00').getTime();

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

  // Si se desea mostrar guiones iniciales como en el diseño de Figma, se puede alternar:
  // update();
  setInterval(update, 1000);
}
