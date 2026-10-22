import re
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST
from .models import Usuario, Bitacora


# Documento: solo dígitos, 5 a 15. Se valida en servidor aunque el HTML ya tenga `pattern`,
# porque el cliente se puede saltar con cualquier herramienta (curl, devtools...).
DOCUMENTO_REGEX = re.compile(r'^[0-9]{5,15}$')

# Cuántos eventos de la bitácora se muestran en "Mi actividad" del perfil.
EVENTOS_ACTIVIDAD = 15


def clave_cumple_formato(password):
    """Regla básica de la UI (8+ caracteres, letras y números). Los validadores de Django se aplican aparte."""
    return len(password) >= 8 and any(c.isalpha() for c in password) and any(c.isdigit() for c in password)


def obtener_ip_cliente(request):
    """
    Saca la IP del cliente para la bitácora.

    Ojo: X-Forwarded-For lo puede falsificar cualquiera si no hay un proxy de confianza
    delante. Para auditoría informativa en dev está bien; en producción detrás de
    nginx/balanceador habría que confiar solo en el último salto conocido.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or '127.0.0.1'


def registrar_evento_bitacora(request, usuario, accion, detalles):
    """Atajo para escribir en Bitacora adjuntando siempre la IP. `usuario` puede ser None (intentos sobre cuentas inexistentes)."""
    return Bitacora.objects.create(
        usuario=usuario,
        accion=accion,
        detalles=detalles,
        ip_origen=obtener_ip_cliente(request),
    )


def obtener_next_seguro(request):
    """
    Devuelve el `next` (POST o GET) solo si apunta a este mismo sitio; si no, None.

    Sin esta validación, un `?next=https://sitio-falso.com` mandaría al votante, recién
    autenticado, a una página externa (open redirect, típico en phishing).
    """
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return None


def obtener_perfil(user):
    """
    Devuelve el perfil `Usuario` de un `auth.User`, creándolo si no existe.

    Las cuentas creadas fuera del registro (Admin/createsuperuser) no tienen perfil:
    se les genera uno al vuelo para que el login y la pantalla de perfil no fallen.
    """
    perfil, _ = Usuario.objects.get_or_create(
        user=user,
        defaults={
            'identificacion': f'DOC-{user.id}',
            'correo': user.email or f'{user.username}@festivalvallenato.com',
            'password_hash': user.password,
            'rol': 'administrador' if user.is_staff else 'votante',
            'acepta_terminos': True,
        },
    )
    return perfil


# sensitive_post_parameters: oculta el campo `password` en los reportes de error de Django
# (página de debug y mails de excepciones), así no se filtra una clave en un traceback.
# never_cache: evita que el navegador guarde en caché esta pantalla (botón "atrás" tras logout).
@sensitive_post_parameters('password')
@never_cache
def login_view(request, modo_inicial=None):
    """
    Vista única para registro e inicio de sesión (el prototipo tiene ambos en una sola
    pantalla con pestañas). El campo oculto `modo` indica cuál de los dos flujos procesar.
    """
    # Con sesión ya iniciada no tiene sentido mostrar registro/login: se va al perfil (o al
    # `next` si venía de una página protegida). Solo en GET, para no cortar un POST en curso.
    if request.method == 'GET' and request.user.is_authenticated:
        return redirect(obtener_next_seguro(request) or 'perfil')

    # Prioridad del modo: argumento de la vista > campo POST > query string > por defecto.
    # Si llega un `next` (lo pone @login_required) se abre "login": esa persona quiere entrar, no registrarse.
    # Cualquier valor raro se normaliza para no renderizar estados inválidos.
    modo_por_defecto = 'login' if request.GET.get('next') else 'register'
    modo_activo = modo_inicial or request.POST.get('modo') or request.GET.get('modo', modo_por_defecto)
    if modo_activo not in ('register', 'login'):
        modo_activo = 'register'

    # Se devuelven al template para repoblar el formulario tras un error
    # (la contraseña nunca se reenvía por seguridad).
    correo_val = ''
    identificacion_val = ''

    if request.method == 'POST':
        # ------------------------------------------------------------------
        # FLUJO DE REGISTRO
        # ------------------------------------------------------------------
        if modo_activo == 'register':
            correo_val = request.POST.get('correo', '').strip().lower()
            identificacion_val = request.POST.get('identificacion', '').strip()
            password = request.POST.get('password', '')
            terminos = request.POST.get('terminos') == 'on'

            # Cadena de validaciones: se corta en la primera que falle y se muestra un único
            # mensaje claro, en orden de barato a caro (campos vacíos -> formato -> BD).
            if not correo_val or not identificacion_val or not password:
                messages.error(request, 'Todos los campos son obligatorios para crear tu cuenta.')
            elif not terminos:
                messages.error(request, 'Debes aceptar los términos de participación y la política de tratamiento de datos personales.')
            else:
                try:
                    validate_email(correo_val)
                    correo_valido = True
                except ValidationError:
                    correo_valido = False

                if not correo_valido:
                    messages.error(request, 'Ingresa una dirección de correo electrónico válida.')
                elif not DOCUMENTO_REGEX.fullmatch(identificacion_val):
                    messages.error(request, 'El número de documento debe contener únicamente entre 5 y 15 dígitos numéricos.')
                elif not clave_cumple_formato(password):
                    messages.error(request, 'La contraseña debe tener al menos 8 caracteres e incluir letras y números.')
                # Unicidad de correo: se revisa en User.email, User.username y Usuario.correo
                # porque hay cuentas (p. ej. creadas desde el Admin) que podrían existir solo en uno.
                elif (
                    User.objects.filter(email__iexact=correo_val).exists()
                    or User.objects.filter(username__iexact=correo_val).exists()
                    or Usuario.objects.filter(correo__iexact=correo_val).exists()
                ):
                    messages.error(request, 'Ya existe una cuenta registrada con este correo electrónico. Puedes iniciar sesión.')
                    # Cambiamos a la pestaña de login para guiar al usuario.
                    modo_activo = 'login'
                elif Usuario.objects.filter(identificacion=identificacion_val).exists():
                    messages.error(request, 'Ya existe un votante registrado con este número de documento.')
                else:
                    # Usuario temporal SIN guardar: solo sirve para que UserAttributeSimilarityValidator
                    # compare la clave contra correo/documento y rechace cosas como "valledupar1".
                    temp_user = User(username=correo_val, email=correo_val, first_name=identificacion_val)
                    try:
                        validate_password(password, user=temp_user)
                        password_segura = True
                    except ValidationError as exc:
                        password_segura = False
                        for err in exc.messages:
                            messages.error(request, err)

                    if password_segura:
                        # El correo se usa como username: así el login por correo es directo
                        # y evitamos pedirle al votante un nombre de usuario extra.
                        user = User(username=correo_val, email=correo_val)
                        # Se fuerza PBKDF2-SHA256 de forma explícita (en vez de confiar solo en el
                        # primer hasher de settings) para que quede evidenciado en el código.
                        user.password = make_password(password, hasher='pbkdf2_sha256')
                        user.save()

                        perfil = Usuario.objects.create(
                            user=user,
                            identificacion=identificacion_val,
                            correo=correo_val,
                            password_hash=user.password,
                            rol='votante',
                            acepta_terminos=True,
                        )
                        registrar_evento_bitacora(
                            request,
                            perfil,
                            'Registro de cuenta',
                            f'Registro verificado con cifrado PBKDF2-SHA256 para documento {identificacion_val}',
                        )
                        # Login automático tras registrarse: menos fricción para el votante.
                        login(request, user)
                        messages.success(request, '¡Cuenta creada exitosamente con cifrado PBKDF2-SHA256! Tu sesión ha sido iniciada.')
                        return redirect(obtener_next_seguro(request) or 'perfil')

        # ------------------------------------------------------------------
        # FLUJO DE INICIO DE SESIÓN
        # ------------------------------------------------------------------
        else:
            correo_val = request.POST.get('correo', '').strip().lower()
            password = request.POST.get('password', '')

            if not correo_val or not password:
                messages.error(request, 'Ingresa tu correo electrónico y contraseña para continuar.')
            else:
                # Resolvemos el identificador: primero como correo/username y, si no aparece,
                # como número de documento (el campo del formulario acepta ambos).
                user_obj = (
                    User.objects.filter(email__iexact=correo_val).first()
                    or User.objects.filter(username__iexact=correo_val).first()
                )
                if not user_obj:
                    perfil_doc = Usuario.objects.filter(identificacion=correo_val).select_related('user').first()
                    if perfil_doc:
                        user_obj = perfil_doc.user

                perfil_objetivo = None
                if user_obj:
                    perfil_objetivo = Usuario.objects.filter(user=user_obj).first()

                # 1) ¿Cuenta bloqueada? Se rechaza ANTES de verificar la clave: así un atacante
                # no puede seguir probando contraseñas durante el bloqueo, ni siquiera la correcta.
                if perfil_objetivo and perfil_objetivo.esta_bloqueado():
                    minutos = perfil_objetivo.minutos_restantes_bloqueo()
                    registrar_evento_bitacora(
                        request,
                        perfil_objetivo,
                        'Intento en cuenta bloqueada',
                        f'Acceso rechazado por bloqueo temporal activo ({minutos} min restantes)',
                    )
                    messages.error(
                        request,
                        f'Por seguridad, tu cuenta se encuentra bloqueada temporalmente debido a múltiples intentos fallidos. Intenta de nuevo en {minutos} minuto(s).',
                    )
                else:
                    # Mitigación de timing attack / enumeración de usuarios: si el correo no existe
                    # igual gastamos el costo de un PBKDF2, así la respuesta tarda parecido exista
                    # o no la cuenta y no se puede deducir quién está registrado midiendo tiempos.
                    if not user_obj:
                        make_password(password, hasher='pbkdf2_sha256')

                    # authenticate() verifica el hash en tiempo constante.
                    user = authenticate(request, username=user_obj.username, password=password) if user_obj else None

                    if user is not None:
                        # Migración transparente: si una cuenta vieja (p. ej. creada con
                        # createsuperuser) tiene otro algoritmo, aprovechamos que tenemos la clave
                        # en claro justo ahora para re-hashearla con PBKDF2-SHA256.
                        if not user.password.startswith('pbkdf2_sha256$'):
                            user.password = make_password(password, hasher='pbkdf2_sha256')
                            user.save(update_fields=['password'])

                        perfil = obtener_perfil(user)
                        perfil.password_hash = user.password
                        perfil.save(update_fields=['password_hash'])
                        perfil.reiniciar_intentos()

                        # login() rota la clave de sesión (previene session fixation).
                        login(request, user)
                        registrar_evento_bitacora(
                            request,
                            perfil,
                            'Inicio de sesión',
                            'Autenticación exitosa verificada con PBKDF2-SHA256',
                        )
                        messages.success(request, 'Has iniciado sesión de forma segura.')
                        return redirect(obtener_next_seguro(request) or 'perfil')
                    else:
                        # Credenciales inválidas. Solo contamos intentos si la cuenta existe;
                        # para correos inexistentes no hay a quién bloquear.
                        bloqueado_ahora = False
                        if perfil_objetivo:
                            bloqueado_ahora = perfil_objetivo.registrar_intento_fallido()

                        if bloqueado_ahora:
                            registrar_evento_bitacora(
                                request,
                                perfil_objetivo,
                                'Bloqueo temporal de cuenta',
                                f'Cuenta bloqueada por {Usuario.MINUTOS_BLOQUEO} minutos tras {Usuario.MAX_INTENTOS_FALLIDOS} intentos fallidos',
                            )
                            messages.error(
                                request,
                                f'Has superado el límite de {Usuario.MAX_INTENTOS_FALLIDOS} intentos fallidos. Tu cuenta ha sido bloqueada preventivamente por {Usuario.MINUTOS_BLOQUEO} minutos.',
                            )
                        else:
                            registrar_evento_bitacora(
                                request,
                                perfil_objetivo,
                                'Intento fallido de inicio de sesión',
                                f'Credenciales inválidas para el identificador {correo_val}',
                            )
                            # Mensaje genérico a propósito: no revela si falló el correo o la clave.
                            messages.error(request, 'Credenciales inválidas. Verifica tu correo y contraseña.')

    return render(
        request,
        'usuarios/login.html',
        {
            'seccion_activa': 'cuenta',
            'modo_activo': modo_activo,
            'correo_val': correo_val,
            'identificacion_val': identificacion_val,
            # Viaja como hidden en el form para no perder el destino al hacer POST.
            'next': obtener_next_seguro(request) or '',
        },
    )


@sensitive_post_parameters('password')
@never_cache
def registro_view(request):
    """Alias de /usuarios/registro/: abre la misma pantalla forzando la pestaña de registro."""
    return login_view(request, modo_inicial='register')


# Las tres pantallas del perfil comparten perfil_base.html (avatar + menú lateral).
# `seccion_perfil` marca la opción activa del menú, igual que `seccion_admin` en el panel.
# login_required: sin sesión redirige a settings.LOGIN_URL con ?next=<la URL pedida>.
@login_required
@never_cache
def perfil_view(request):
    """Perfil > Mis datos: datos del votante y del hash de su contraseña."""
    perfil = obtener_perfil(request.user)

    # El hash de Django tiene la forma algoritmo$iteraciones$salt$hash. Las iteraciones se
    # muestran como evidencia del costo de PBKDF2 (formato colombiano: 1.500.000).
    partes_hash = perfil.password_hash.split('$')
    iteraciones = None
    if len(partes_hash) == 4 and partes_hash[1].isdigit():
        iteraciones = f'{int(partes_hash[1]):,}'.replace(',', '.')

    return render(
        request,
        'usuarios/perfil_datos.html',
        {
            'seccion_activa': 'cuenta',
            'seccion_perfil': 'datos',
            'perfil': perfil,
            'iteraciones': iteraciones,
        },
    )


@sensitive_post_parameters('password_actual', 'password_nueva', 'password_confirmacion')
@login_required
@never_cache
def perfil_contrasena_view(request):
    """
    Perfil > Cambiar contraseña. Si sale bien redirige (patrón PRG) para que recargar
    la página no reenvíe el formulario.
    """
    perfil = obtener_perfil(request.user)

    if request.method == 'POST':
        password_actual = request.POST.get('password_actual', '')
        password_nueva = request.POST.get('password_nueva', '')
        password_confirmacion = request.POST.get('password_confirmacion', '')

        # Misma idea que el registro: se corta en la primera validación que falle.
        if not password_actual or not password_nueva or not password_confirmacion:
            messages.error(request, 'Completa los tres campos para cambiar tu contraseña.')
        elif not request.user.check_password(password_actual):
            # Cuenta para el mismo bloqueo que el login: con una sesión robada no se puede
            # adivinar la clave actual sin límite. Al bloquear se cierra también la sesión.
            if perfil.registrar_intento_fallido():
                registrar_evento_bitacora(
                    request,
                    perfil,
                    'Bloqueo temporal de cuenta',
                    f'Cuenta bloqueada por {Usuario.MINUTOS_BLOQUEO} minutos tras {Usuario.MAX_INTENTOS_FALLIDOS} intentos fallidos (cambio de contraseña)',
                )
                logout(request)
                messages.error(
                    request,
                    f'Has superado el límite de {Usuario.MAX_INTENTOS_FALLIDOS} intentos fallidos. Tu cuenta ha sido bloqueada preventivamente por {Usuario.MINUTOS_BLOQUEO} minutos y se cerró tu sesión.',
                )
                return redirect('/usuarios/login/?modo=login')
            registrar_evento_bitacora(
                request,
                perfil,
                'Intento fallido de cambio de contraseña',
                'La contraseña actual ingresada no coincide',
            )
            messages.error(request, 'La contraseña actual no es correcta.')
        elif password_nueva != password_confirmacion:
            messages.error(request, 'La nueva contraseña y su confirmación no coinciden.')
        elif password_nueva == password_actual:
            messages.error(request, 'La nueva contraseña debe ser distinta de la actual.')
        elif not clave_cumple_formato(password_nueva):
            messages.error(request, 'La nueva contraseña debe tener al menos 8 caracteres e incluir letras y números.')
        else:
            try:
                validate_password(password_nueva, user=request.user)
                password_segura = True
            except ValidationError as exc:
                password_segura = False
                for err in exc.messages:
                    messages.error(request, err)

            if password_segura:
                user = request.user
                user.password = make_password(password_nueva, hasher='pbkdf2_sha256')
                user.save(update_fields=['password'])
                perfil.password_hash = user.password
                perfil.save(update_fields=['password_hash'])
                perfil.reiniciar_intentos()
                # Al cambiar la clave Django invalida todas las sesiones de la cuenta (guardan un
                # hash de la clave). Esto renueva solo la actual: las demás quedan cerradas.
                update_session_auth_hash(request, user)
                registrar_evento_bitacora(
                    request,
                    perfil,
                    'Cambio de contraseña',
                    'Contraseña actualizada con cifrado PBKDF2-SHA256; se cerraron las demás sesiones abiertas',
                )
                messages.success(request, 'Tu contraseña se actualizó con cifrado PBKDF2-SHA256. Las demás sesiones abiertas se cerraron.')
                return redirect('perfil_contrasena')

    return render(
        request,
        'usuarios/perfil_contrasena.html',
        {
            'seccion_activa': 'cuenta',
            'seccion_perfil': 'contrasena',
            'perfil': perfil,
        },
    )


@login_required
@never_cache
def perfil_actividad_view(request):
    """Perfil > Mi actividad: últimos eventos de la bitácora con su firma verificada."""
    perfil = obtener_perfil(request.user)

    # Bitacora.Meta.ordering es -fecha_hora: los más recientes primero. Se verifica la firma
    # de cada evento aquí para no recalcularla dos veces en el template.
    actividad = list(perfil.bitacoras.all()[:EVENTOS_ACTIVIDAD])
    for evento in actividad:
        evento.firma_ok = evento.firma_valida()

    return render(
        request,
        'usuarios/perfil_actividad.html',
        {
            'seccion_activa': 'cuenta',
            'seccion_perfil': 'actividad',
            'perfil': perfil,
            'actividad': actividad,
            'firmas_validas': sum(1 for evento in actividad if evento.firma_ok),
        },
    )


# require_POST: con GET, cualquier página ajena podría cerrar la sesión del votante con
# un simple <img src="/usuarios/logout/">. Por POST además exige el token CSRF.
@require_POST
@never_cache
def logout_view(request):
    """
    Cierra la sesión. Se audita ANTES de llamar a logout(), porque después request.user
    pasa a ser anónimo y perderíamos a quién atribuir el evento.
    """
    if request.user.is_authenticated:
        perfil = Usuario.objects.filter(user=request.user).first()
        registrar_evento_bitacora(
            request,
            perfil,
            'Cierre de sesión',
            'El usuario cerró su sesión y se invalidó el token de sesión activa',
        )
        # logout() borra la sesión del servidor, no solo la cookie del cliente.
        logout(request)
        messages.info(request, 'Has cerrado tu sesión de forma segura.')
    return redirect('/usuarios/login/?modo=login')
