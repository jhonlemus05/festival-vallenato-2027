/**
 * auth.js
 * Manejo de formulario de registro / inicio de sesión del Festival Vallenato 2027
 */

document.addEventListener('DOMContentLoaded', () => {
  initAuthPage();
});

function initAuthPage() {
  const btnRegister = document.getElementById('tabRegister');
  const btnLogin = document.getElementById('tabLogin');
  const submitBtn = document.getElementById('btnAuthSubmit');
  const submitBtnText = document.getElementById('authSubmitText');
  const footerToggleText = document.getElementById('authFooterToggle');
  const docNumberGroup = document.getElementById('docNumberGroup');
  const termsGroup = document.getElementById('termsGroup');
  const passwordHint = document.getElementById('passwordHint');
  const forgotPasswordWrap = document.getElementById('forgotPasswordWrap');
  const passInput = document.getElementById('passwordInput');

  if (btnRegister && btnLogin) {
    btnRegister.addEventListener('click', () => {
      setMode('register');
    });

    btnLogin.addEventListener('click', () => {
      setMode('login');
    });
  }

  function setMode(mode) {
    if (mode === 'register') {
      btnRegister.classList.add('active');
      btnLogin.classList.remove('active');
      if (submitBtnText) submitBtnText.textContent = 'Crear cuenta';
      if (docNumberGroup) docNumberGroup.style.display = 'block';
      if (termsGroup) termsGroup.style.display = 'flex';
      if (passwordHint) passwordHint.style.display = 'block';
      if (forgotPasswordWrap) forgotPasswordWrap.style.display = 'none';
      if (passInput) passInput.placeholder = 'Ingresa tu contraseña';
      if (footerToggleText) {
        footerToggleText.innerHTML = '¿Ya tienes una cuenta? <span class="fw-semibold text-dark text-decoration-underline" style="cursor:pointer;" onclick="setAuthModeExternal(\'login\')">Iniciar sesión</span>';
      }
    } else {
      btnLogin.classList.add('active');
      btnRegister.classList.remove('active');
      if (submitBtnText) submitBtnText.textContent = 'Iniciar sesión';
      if (docNumberGroup) docNumberGroup.style.display = 'none';
      if (termsGroup) termsGroup.style.display = 'none';
      if (passwordHint) passwordHint.style.display = 'none';
      if (forgotPasswordWrap) forgotPasswordWrap.style.display = 'block';
      if (passInput) passInput.placeholder = 'Ingresa tu contraseña';
      if (footerToggleText) {
        footerToggleText.innerHTML = '¿No tienes una cuenta? <span class="fw-semibold text-dark text-decoration-underline" style="cursor:pointer;" onclick="setAuthModeExternal(\'register\')">Registrarse</span>';
      }
    }
  }

  window.setAuthModeExternal = setMode;

  // Toggle de visualización de contraseña (ojo tachado)
  const togglePassBtn = document.getElementById('togglePasswordVisibility');
  const eyeIcon = document.getElementById('passwordEyeIcon');

  if (togglePassBtn && passInput && eyeIcon) {
    togglePassBtn.addEventListener('click', () => {
      if (passInput.type === 'password') {
        passInput.type = 'text';
        eyeIcon.className = 'bi bi-eye';
      } else {
        passInput.type = 'password';
        eyeIcon.className = 'bi bi-eye-slash';
      }
    });
  }

  // Envío del formulario
  const authForm = document.getElementById('authForm');
  if (authForm) {
    authForm.addEventListener('submit', (e) => {
      e.preventDefault();
      // Navegación hacia categorías
      window.location.href = 'categorias.html';
    });
  }
}
