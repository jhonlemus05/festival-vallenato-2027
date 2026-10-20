/**
 * auth.js
 * Lógica de cliente de la pantalla de registro / inicio de sesión (/usuarios/login/).
 *
 * Ojo: esto es solo UX. Ninguna validación de acá es una barrera de seguridad; el
 * servidor (usuarios/views.py) revalida todo. El JS únicamente alterna pestañas,
 * da feedback inmediato y evita errores tontos de tipeo.
 */

document.addEventListener('DOMContentLoaded', () => {
  initAuthPage();
});

function initAuthPage() {
  // Referencias al DOM. Varias pueden ser null (p. ej. con sesión activa no hay formulario),
  // por eso todo se usa con guardas `if (el)` más abajo.
  const btnRegister = document.getElementById('tabRegister');
  const btnLogin = document.getElementById('tabLogin');
  const submitBtnText = document.getElementById('authSubmitText');
  const footerToggleText = document.getElementById('authFooterToggle');
  const docNumberGroup = document.getElementById('docNumberGroup');
  const docInput = document.getElementById('docInput');
  const termsGroup = document.getElementById('termsGroup');
  const termsHiddenInput = document.getElementById('termsHiddenInput');
  const passwordHint = document.getElementById('passwordHint');
  const passwordStrengthWrap = document.getElementById('passwordStrengthWrap');
  const forgotPasswordWrap = document.getElementById('forgotPasswordWrap');
  const passInput = document.getElementById('passwordInput');
  // Input hidden que viaja en el POST; es lo que le dice a la vista qué flujo ejecutar.
  const authModeInput = document.getElementById('authModeInput');

  if (btnRegister && btnLogin) {
    btnRegister.addEventListener('click', () => {
      setMode('register');
    });

    btnLogin.addEventListener('click', () => {
      setMode('login');
    });
  }

  /**
   * Cambia la UI entre "register" y "login".
   * Punto importante: se alterna el atributo `required` de los campos que se ocultan; un
   * campo oculto pero `required` bloquearía el submit del navegador sin mostrar error.
   */
  function setMode(mode) {
    if (!btnRegister || !btnLogin) return;

    // Sincroniza el modo con el campo hidden para que el servidor procese el flujo correcto.
    if (authModeInput) {
      authModeInput.value = mode;
    }

    if (mode === 'register') {
      btnRegister.classList.add('active');
      btnLogin.classList.remove('active');
      if (submitBtnText) submitBtnText.textContent = 'Crear cuenta';
      if (docNumberGroup) docNumberGroup.style.display = 'block';
      if (docInput) docInput.required = true;
      if (termsGroup) termsGroup.style.display = 'flex';
      if (termsHiddenInput) termsHiddenInput.required = true;
      if (passwordHint) passwordHint.style.display = 'block';
      if (passwordStrengthWrap) passwordStrengthWrap.style.display = 'block';
      if (forgotPasswordWrap) forgotPasswordWrap.style.display = 'none';
      if (passInput) {
        passInput.placeholder = 'Ingresa tu contraseña';
        // `new-password` le indica al gestor de contraseñas que ofrezca generar una nueva.
        passInput.setAttribute('autocomplete', 'new-password');
      }
      if (footerToggleText) {
        footerToggleText.innerHTML = '¿Ya tienes una cuenta? <span class="fw-semibold text-dark text-decoration-underline" style="cursor:pointer;" onclick="setAuthModeExternal(\'login\')">Iniciar sesión</span>';
      }
    } else {
      btnLogin.classList.add('active');
      btnRegister.classList.remove('active');
      if (submitBtnText) submitBtnText.textContent = 'Iniciar sesión';
      if (docNumberGroup) docNumberGroup.style.display = 'none';
      if (docInput) docInput.required = false;
      if (termsGroup) termsGroup.style.display = 'none';
      if (termsHiddenInput) termsHiddenInput.required = false;
      if (passwordHint) passwordHint.style.display = 'none';
      if (passwordStrengthWrap) passwordStrengthWrap.style.display = 'none';
      if (forgotPasswordWrap) forgotPasswordWrap.style.display = 'block';
      if (passInput) {
        passInput.placeholder = 'Ingresa tu contraseña';
        // `current-password` hace que el gestor autocomplete la clave guardada.
        passInput.setAttribute('autocomplete', 'current-password');
      }
      if (footerToggleText) {
        footerToggleText.innerHTML = '¿No tienes una cuenta? <span class="fw-semibold text-dark text-decoration-underline" style="cursor:pointer;" onclick="setAuthModeExternal(\'register\')">Registrarse</span>';
      }
    }
  }

  // Se expone en window porque el enlace del pie del formulario la invoca con onclick inline.
  window.setAuthModeExternal = setMode;

  // Al cargar, aplica el modo que decidió el servidor (p. ej. tras un error de registro
  // duplicado el servidor devuelve modo "login" y la UI debe reflejarlo).
  if (authModeInput && authModeInput.value) {
    setMode(authModeInput.value);
  }

  // Sanitiza el documento en vivo: descarta todo lo que no sea dígito (coincide con el
  // regex ^[0-9]{5,15}$ del servidor, pero solo como comodidad para el usuario).
  if (docInput) {
    docInput.addEventListener('input', () => {
      docInput.value = docInput.value.replace(/[^0-9]/g, '');
    });
  }

  // Recalcula el medidor de fortaleza en cada tecla.
  if (passInput) {
    passInput.addEventListener('input', () => {
      updatePasswordStrength(passInput.value);
    });
  }

  // Botón "ojo": alterna entre ocultar y mostrar la contraseña.
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
}

/**
 * Medidor de fortaleza de contraseña (0 a 4). Es heurístico y solo orientativo: no
 * reemplaza a los validadores de Django. Un punto por cada criterio cumplido:
 *   1) >= 8 caracteres   2) letras y números   3) mayúsculas y minúsculas
 *   4) símbolo especial o >= 12 caracteres
 */
function updatePasswordStrength(val) {
  const segs = [
    document.getElementById('strengthSeg1'),
    document.getElementById('strengthSeg2'),
    document.getElementById('strengthSeg3'),
    document.getElementById('strengthSeg4'),
  ];
  const label = document.getElementById('strengthLabelText');
  // Si el DOM del medidor no existe (modo sesión activa), no hay nada que pintar.
  if (!segs[0] || !label) return;

  let score = 0;
  if (val.length >= 8) score++;
  if (/[A-Za-z]/.test(val) && /[0-9]/.test(val)) score++;
  if (/[A-Z]/.test(val) && /[a-z]/.test(val)) score++;
  if (/[^A-Za-z0-9]/.test(val) || val.length >= 12) score++;

  // Los arrays se indexan por `score`: posición 0 = sin puntaje, 4 = óptimo.
  const colors = ['#E5E7EB', '#EF4444', '#F59E0B', '#D8A629', '#16A34A'];
  const texts = [
    'Nivel de seguridad: Pendiente',
    'Nivel de seguridad: Débil',
    'Nivel de seguridad: Aceptable',
    'Nivel de seguridad: Fuerte',
    'Nivel de seguridad: Óptimo',
  ];

  // Se pintan solo tantos segmentos como puntos tenga la clave; el resto queda gris.
  segs.forEach((seg, idx) => {
    if (!seg) return;
    seg.style.backgroundColor = idx < score ? colors[score] : '#E5E7EB';
  });
  label.textContent = texts[score];
}

/**
 * Checkbox de términos personalizado (cuadrado dorado del Figma).
 * El checkbox real está oculto y es el que viaja en el POST; este div solo lo "maquilla".
 * Se invoca con onclick inline desde el template, por eso es global.
 */
function toggleTerms() {
  const hidden = document.getElementById('termsHiddenInput');
  const box = document.getElementById('termsBox');
  const icon = document.getElementById('termsCheckIcon');
  if (!hidden || !box || !icon) return;
  hidden.checked = !hidden.checked;
  if (hidden.checked) {
    box.style.backgroundColor = 'var(--color-gold)';
    icon.style.display = 'block';
  } else {
    box.style.backgroundColor = '#FFFFFF';
    icon.style.display = 'none';
  }
}
