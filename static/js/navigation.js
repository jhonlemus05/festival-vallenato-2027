/**
 * navigation.js
 * Manejo de navegación entre interfaces y menú lateral institucional
 */

document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
});

function setupNavigation() {
  // Manejo de enlaces para prototipo estático
  const links = document.querySelectorAll('a[data-route]');
  links.forEach(link => {
    link.addEventListener('click', (e) => {
      const target = link.getAttribute('data-route');
      if (target) {
        // Redirección simple entre las páginas HTML
        window.location.href = target;
      }
    });
  });
}

function openMenuDrawer() {
  const drawer = document.getElementById('institutionalDrawer');
  if (drawer && window.bootstrap) {
    const bsOffcanvas = new bootstrap.Offcanvas(drawer);
    bsOffcanvas.show();
  }
}
