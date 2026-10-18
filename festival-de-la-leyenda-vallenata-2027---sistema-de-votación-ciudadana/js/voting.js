/**
 * voting.js
 * Manejo de selección de participantes y modal de confirmación oficial
 */

document.addEventListener('DOMContentLoaded', () => {
  initVotingSelection();
});

const contestantsData = {
  mateo: { 
    name: 'Mateo Díaz', 
    song: 'Mi tierra canta',
    img: '/src/assets/images/contestant_mateo_diaz_1791516984186.jpg'
  },
  lucia: { 
    name: 'Lucía Pineda', 
    song: 'Raíces del alma',
    img: '/src/assets/images/contestant_lucia_pineda_1791516993941.jpg'
  },
  samuel: { 
    name: 'Samuel Rojas', 
    song: 'Aires de mi pueblo',
    img: '/src/assets/images/contestant_samuel_rojas_1791517002103.jpg'
  },
  valentina: { 
    name: 'Valentina López', 
    song: 'Corazón del Valle',
    img: '/src/assets/images/contestant_valentina_lopez_1791517011267.jpg'
  }
};

let currentSelected = 'mateo';

function initVotingSelection() {
  const cards = document.querySelectorAll('.option-contestant-card');
  const selectionLabel = document.getElementById('selectedContestantName');
  const selectionLabelDesktop = document.getElementById('selectedContestantNameDesktop');
  const voteBtns = document.querySelectorAll('.btn-trigger-vote');

  const modalName = document.getElementById('modalCandidateName');
  const modalImg = document.getElementById('modalCandidateImg');
  const btnConfirmVote = document.getElementById('btnConfirmVoteFinal');

  cards.forEach(card => {
    card.addEventListener('click', () => {
      const contestantId = card.getAttribute('data-id');
      if (!contestantId || !contestantsData[contestantId]) return;

      currentSelected = contestantId;

      // Actualizar selección visual de tarjetas
      cards.forEach(c => {
        c.classList.remove('selected');
        const badge = c.querySelector('.selection-indicator-circle');
        if (badge) {
          badge.innerHTML = '';
        }
      });

      card.classList.add('selected');
      const activeBadge = card.querySelector('.selection-indicator-circle');
      if (activeBadge) {
        activeBadge.innerHTML = '<i class="bi bi-check2"></i>';
      }

      // Actualizar texto: Tu elección: [Nombre]
      if (selectionLabel) {
        selectionLabel.textContent = contestantsData[contestantId].name;
      }
      if (selectionLabelDesktop) {
        selectionLabelDesktop.textContent = contestantsData[contestantId].name;
      }

      // Actualizar datos del modal de confirmación
      if (modalName) {
        modalName.textContent = contestantsData[contestantId].name;
      }
      if (modalImg) {
        modalImg.src = contestantsData[contestantId].img;
      }
    });
  });

  // Al hacer clic en cualquiera de los botones "Votar ✓" (Móvil o Desktop)
  voteBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();

      // Guardar candidato elegido en almacenamiento de sesión
      sessionStorage.setItem('votedCandidate', JSON.stringify({
        id: currentSelected,
        name: contestantsData[currentSelected].name,
        song: contestantsData[currentSelected].song,
        img: contestantsData[currentSelected].img
      }));

      // Abrir modal de Bootstrap
      const confirmModalEl = document.getElementById('voteConfirmModal');
      if (confirmModalEl && window.bootstrap) {
        const bsModal = new bootstrap.Modal(confirmModalEl);
        bsModal.show();
      }
    });
  });

  // Al confirmar el voto en el modal
  if (btnConfirmVote) {
    btnConfirmVote.addEventListener('click', () => {
      // Navegar a la pantalla de éxito
      window.location.href = 'exito.html';
    });
  }
}
