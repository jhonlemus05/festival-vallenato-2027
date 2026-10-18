/**
 * success.js
 * Carga de datos del participante votado en la pantalla de éxito oficial
 */

document.addEventListener('DOMContentLoaded', () => {
  loadVotedCandidateDetails();
});

function loadVotedCandidateDetails() {
  const nameEl = document.getElementById('successCandidateName');
  const songEl = document.getElementById('successCandidateSong');
  const imgEl = document.getElementById('successCandidateImg');

  try {
    const saved = sessionStorage.getItem('votedCandidate');
    if (saved) {
      const data = JSON.parse(saved);
      if (nameEl && data.name) nameEl.textContent = data.name;
      if (songEl && data.song) songEl.textContent = data.song;
      if (imgEl && data.img) imgEl.src = data.img;
    }
  } catch (e) {
    console.error('Error cargando candidato votado:', e);
  }
}
