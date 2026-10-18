/**
 * admin.js
 * Lógica modular para el Panel de Administración del Festival Vallenato 2027
 */

document.addEventListener('DOMContentLoaded', () => {
  initAdminDashboard();
});

function initAdminDashboard() {
  // Manejo de botón "+ Nueva votación"
  const btnNewPoll = document.getElementById('btnNewPoll');
  const modalNewPoll = document.getElementById('modalNewPoll');
  
  if (btnNewPoll && modalNewPoll && window.bootstrap) {
    btnNewPoll.addEventListener('click', () => {
      const bsModal = new bootstrap.Modal(modalNewPoll);
      bsModal.show();
    });
  }

  // Manejo de formulario de nueva votación
  const formNewPoll = document.getElementById('formNewPoll');
  if (formNewPoll) {
    formNewPoll.addEventListener('submit', (e) => {
      e.preventDefault();
      const title = document.getElementById('newPollTitle')?.value;
      const category = document.getElementById('newPollCategory')?.value;
      
      // Feedback visual
      const toastEl = document.getElementById('adminToast');
      if (toastEl && window.bootstrap) {
        const toastMsg = document.getElementById('toastMsg');
        if (toastMsg) {
          toastMsg.textContent = `Votación "${title}" (${category}) creada en modo demostración.`;
        }
        const bsToast = new bootstrap.Toast(toastEl);
        bsToast.show();
      }

      // Cerrar modal
      if (modalNewPoll && window.bootstrap) {
        const bsModal = bootstrap.Modal.getInstance(modalNewPoll);
        if (bsModal) bsModal.hide();
      }
      formNewPoll.reset();
    });
  }

  // Manejo de "Ver registro completo"
  const btnFullLog = document.getElementById('btnFullLog');
  const modalFullLog = document.getElementById('modalFullLog');
  if (btnFullLog && modalFullLog && window.bootstrap) {
    btnFullLog.addEventListener('click', (e) => {
      e.preventDefault();
      const bsModal = new bootstrap.Modal(modalFullLog);
      bsModal.show();
    });
  }
}
