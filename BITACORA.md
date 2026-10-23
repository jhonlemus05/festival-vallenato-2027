# BITÁCORA DEL PROYECTO — Festival de la Leyenda Vallenata 2027

> Este archivo registra cada modificación hecha al proyecto para mantener el contexto
> entre sesiones/modelos. **Actualizar siempre que se haga un cambio.**

## 1. Descripción general

Migración de un prototipo HTML estático (`festival-de-la-leyenda-vallenata-2027---sistema-de-votación-ciudadana/`)
a un proyecto **Django**. Se migra **vista por vista**. Los assets (CSS/JS/imágenes) viven en `static/`
y las vistas usan plantillas con herencia (`base.html` + página hija).

La organización del proyecto sigue **`ESTRUCTURA.md`** (raíz): 3 apps modulares
`usuarios` (autenticación), `votaciones` (experiencia pública del votante) y `administracion` (panel privado).

## 2. Estructura del proyecto

```
D:\no_borrar\programacion\Python\Django\
├── manage.py
├── db.sqlite3
├── BITACORA.md                     # Este archivo
├── ESTRUCTURA.md                   # Estructura objetivo acordada
├── env_django\                     # Entorno virtual (python.exe aquí) — IGNORADO por git
├── pr_festivalVallenato\           # Configuración del proyecto Django
│   ├── settings.py                 # INSTALLED_APPS: usuarios, votaciones, administracion
│   ├── urls.py                     # admin/ , '' (votaciones), usuarios/, admin-panel/
│   └── wsgi.py / asgi.py
├── static\                         # Estáticos globales (STATICFILES_DIRS)
│   ├── css\responsive.css
│   ├── css\usuarios.css             # Estilos compartidos de login.html y del perfil
│   ├── js\countdown.js
│   ├── js\navigation.js
│   ├── js\admin.js
│   ├── js\auth.js
│   └── images\hero_accordionist_banner_1791518403166.jpg
├── usuarios\                       # APP 1: autenticación (MIGRADA + FUNCIONAL)
│   ├── migrations\0001_initial.py  # Modelos Usuario y Bitacora
│   ├── migrations\0002_alter_bitacora_fecha_hora.py  # fecha_hora con default (firma verificable)
│   ├── templates\usuarios\
│   │   ├── login.html              # Registro e Inicio de sesión
│   │   ├── perfil_base.html        # Base del perfil: avatar + menú lateral (seccion_perfil)
│   │   ├── perfil_datos.html       # Perfil > Mis datos
│   │   ├── perfil_contrasena.html  # Perfil > Cambiar contraseña
│   │   ├── perfil_actividad.html   # Perfil > Mi actividad
│   │   └── _mensajes.html          # Parcial de alertas (django.contrib.messages)
│   ├── models.py                   # Usuario (tabla 'usuario') y Bitacora (tabla 'bitacora')
│   ├── admin.py                    # Registro en Django Admin
│   ├── urls.py                     # '' , 'login/', 'registro/', 'perfil/' (+ contrasena/, actividad/), 'logout/'
│   ├── views.py                    # login_view, registro_view, perfil_*_view, logout_view
│   └── tests.py                    # Pruebas de registro, login, logout, bitácora y perfil
├── votaciones\                     # APP 2: experiencia pública (MIGRANDO)
│   ├── templates\votaciones\
│   │   ├── base.html               # Layout público (navbar, footer, offcanvas, scripts)
│   │   └── index.html              # Página de Inicio (ex inicio.html)
│   ├── urls.py                     # '' -> views.index (name='index')
│   └── views.py                    # def index(...)
├── administracion\                 # APP 3: panel privado (MIGRANDO)
│   ├── templates\administracion\
│   │   ├── admin_base.html             # Layout privado (sidebar, topbar, offcanvas, scripts)
│   │   ├── _admin_sidebar_nav.html     # Menú lateral reutilizable (sidebar + offcanvas)
│   │   ├── panel_principal.html        # Dashboard principal (ex admin.html)
│   │   └── categorias.html             # Gestión de categorías (ex admin-categorias.html)
│   ├── urls.py                     # '' -> panel_principal ; 'categorias/' -> categorias
│   └── views.py
└── festival-de-la-leyenda-vallenata-2027---...-ciudadana\   # Prototipo fuente (referencia)
```

## 3. Convenios usados

- **Python/pip:** usar `env_django\Scripts\python.exe` (ej: `& "env_django\Scripts\python.exe" manage.py check`).
- **Rutas Django:**
  - `votaciones` montada en **`/`** (raíz). Inicio: `http://127.0.0.1:8000/` (nombre de URL `index`).
  - `usuarios` en `/usuarios/` (`login`, `registro`, `perfil`, `perfil_contrasena`, `perfil_actividad`, `logout`) y `administracion` en `/admin-panel/` (`panel_principal`).
- **Estáticos:** referenciar con `{% static '...' %}`. `settings.py` tiene `STATICFILES_DIRS = [BASE_DIR / 'static']`.
- **Plantillas:** cada página hereda de la base de su app:
  - Público: `votaciones/base.html` (bloques `titulo`, `descripcion`, `contenido`, `extra_css`, `extra_js`).
  - Admin: `administracion/admin_base.html` (bloques `titulo`, `descripcion`, `breadcrumb`,
    `contenido`, `modales`, `extra_css`, `extra_js`). Incluye el partial `_admin_sidebar_nav.html`.
- **Navegación activa:**
  - Público: variable de contexto `seccion_activa` (valores: `inicio`, `categorias`, `cuenta`, `admin`).
  - Admin: variable de contexto `seccion_admin` (valores: `panel`, `categorias`, `votaciones`,
    `opciones`, `resultados`). La vista debe pasarla.
- **Admin (diseño propio):** usa `--color-gold: #D4AF37` (distinto al dorado público `#D8A629`) y NO
  carga `responsive.css`; la responsividad del panel está en `admin_base.html` (breakpoint 991px).
  Pendiente: proteger las vistas admin con login/staff (ver `ESTRUCTURA.md`).
- **Enlaces a vistas no migradas:** quedaron como `href="#"` (placeholders) y se reemplazarán
  por `{% url '...' %}` cuando exista cada vista.
- **Idioma:** contenido en español. NO agregar comentarios al código salvo lo ya presente.

## 4. Registro de cambios

### [1] Vistas: Home (plantilla base + inicio)
- **`pr_festivalVallenato/settings.py`**: se agregó `STATICFILES_DIRS = [BASE_DIR / 'static']`.
- **`static/`**: se creó con `css/responsive.css`, `js/countdown.js`, `js/navigation.js`
  e `images/hero_accordionist_banner_1791518403166.jpg` (copiados del prototipo).
- **`static/css/responsive.css`**: se cambió la ruta de la imagen de fondo de
  `/src/assets/images/...` a `/static/images/...`.
- **Base institucional**: head (Google Fonts, Bootstrap 5.3, Bootstrap Icons, `responsive.css`),
  variables CSS (`--color-gold: #D8A629`, etc.), encabezado, footer desktop, navbar inferior móvil,
  offcanvas lateral y scripts (`countdown.js`, `navigation.js`).
- **Vista Inicio**: creada a partir del `index.html` del prototipo (hero + cuenta regresiva/CTA/preview).
- **Verificación:** `manage.py check` sin errores; la vista responde **200** y renderiza estáticos.

### [2] Control de versiones (Git)
- **`.gitignore`**: creado en la raíz. Excluye `env_django/`, `__pycache__/`, `*.pyc`, `db.sqlite3`,
  `/staticfiles/`, `/media/`, `.env`, archivos de IDE y de sistema. **La carpeta del prototipo
  `festival-de-la-leyenda-vallenata-2027---sistema-de-votación-ciudadana/` SÍ se versiona** (pesa ~4.4 MB)
  como referencia de diseño. El repo todavía NO se ha inicializado (`git init` pendiente, lo hace el usuario).
- Entorno: Git 2.55 (Windows), usuario global `jhonlemus05 <jhonlemus05@gmail.com>`. No hay `gh` CLI.

### [3] Reestructuración a 3 apps (según ESTRUCTURA.md)
- **Apps creadas** con `startapp`: `usuarios`, `votaciones`, `administracion`.
- **`pr_festivalVallenato/settings.py`**: `INSTALLED_APPS` reemplazó `'home'` por
  `'usuarios', 'votaciones', 'administracion'`.
- **`pr_festivalVallenato/urls.py`**: ahora incluye `path('', include('votaciones.urls'))`,
  `path('usuarios/', include('usuarios.urls'))` y `path('admin-panel/', include('administracion.urls'))`.
- **Plantillas movidas** de `home` a `votaciones`:
  - `home/templates/home/base.html` -> `votaciones/templates/votaciones/base.html`
  - `home/templates/home/inicio.html` -> `votaciones/templates/votaciones/index.html`
  - Se actualizó `{% extends %}` a `votaciones/base.html` y los `{% url 'home' %}` a `{% url 'index' %}`.
- **`votaciones/views.py`**: `def index(request)` -> `render(request, 'votaciones/index.html', {'seccion_activa': 'inicio'})`.
- **`votaciones/urls.py`**: `path('', views.index, name='index')` (sin namespace).
- **`usuarios/urls.py`** y **`administracion/urls.py`**: creados con `urlpatterns = []` (pendientes).
- **App `home` eliminada** por completo (carpeta borrada).
- **Verificación:** `manage.py check` OK; la vista Inicio responde **200** en `/` y renderiza estáticos.

### [4] Panel de administración: base + Panel principal
- **Rama Git:** `feature/migracion-administracion` (remota en origin; se hizo `fetch` + `checkout`).
- **`static/js/admin.js`**: copiado del prototipo (`js/admin.js`), sin cambios.
- **`administracion/templates/administracion/admin_base.html`**: layout privado. Contiene el sistema
  de diseño del panel (variables `--color-gold: #D4AF37`, sidebar, topbar/breadcrumb, offcanvas móvil,
  KPIs, badges y barras de progreso genéricas, responsive 991px) y bloques `titulo`, `descripcion`,
  `breadcrumb`, `contenido`, `modales`, `extra_css`, `extra_js`.
- **`administracion/templates/administracion/_admin_sidebar_nav.html`**: partial con el menú lateral
  (se reutiliza en sidebar desktop y en el offcanvas móvil; recibe `offcanvas=True`).
- **`administracion/templates/administracion/panel_principal.html`**: migración de `admin.html`.
  El contenido (header de página, KPIs, tabla de actividad, votaciones de la edición, resumen de
  categorías) va en `{% block contenido %}`; los modales y el toast en `{% block modales %}`; el CSS
  específico de la página en `{% block extra_css %}`.
- **`administracion/views.py`**: `def panel_principal(request)` -> render con `{'seccion_admin': 'panel'}`.
- **`administracion/urls.py`**: `path('', views.panel_principal, name='panel_principal')` (ruta `/admin-panel/`).
- **Enlaces:** "Volver a vista pública" -> `{% url 'index' %}`. Los ítems Categorías/Votaciones/Opciones/
  Resultados del menú quedaron como `href="#"` hasta migrarlos.
- **Verificación:** `manage.py check` OK; `/` y `/admin-panel/` responden **200**.

### [5] Módulo de Usuarios: migración de login/registro y seguridad avanzada (PBKDF2-SHA256)
- **Rama Git:** `feature/migracion-usuarios` (actualizada con `main`).
- **`pr_festivalVallenato/settings.py`**: configurado `PASSWORD_HASHERS` con `PBKDF2PasswordHasher` (`PBKDF2-HMAC-SHA256`), validadores de contraseñas (`AUTH_PASSWORD_VALIDATORS`), idioma `es-co` y banderas de seguridad de sesión/cookies (`HttpOnly`, `SameSite=Lax`, `X_FRAME_OPTIONS='DENY'`, `NOSNIFF`).
- **`usuarios/models.py`**: creados los modelos `Usuario` (`db_table='usuario'`, con `identificacion`, `correo`, `password_hash` en formato `pbkdf2_sha256$...`, `rol`, `acepta_terminos`, `intentos_fallidos`, `bloqueado_hasta`, `fecha_registro`) y `Bitacora` (`db_table='bitacora'`, con `usuario`, `accion`, `detalles`, `ip_origen`, `hash_sha256` calculado con `hashlib.sha256` e inmutable, `fecha_hora`).
- **`usuarios/admin.py`**: registrados `Usuario` y `Bitacora` en Django Admin mostrando el estado de bloqueo, intentos fallidos, IP de origen y la firma de integridad `hash_sha256`.
- **`usuarios/migrations/0001_initial.py`**: migración inicial generada y verificada.
- **`static/js/auth.js`**: adaptado del prototipo (`js/auth.js`) con medidor visual de fortaleza de contraseña en tiempo real, sanitización numérica del documento y alternancia entre "Registrarse" e "Iniciar sesión".
- **`usuarios/templates/usuarios/login.html`**: migrado desde `login.html` heredando de `votaciones/base.html` (`seccion_activa='cuenta'`). Incluye barra de nivel de seguridad de contraseña, insignia de protección activa y tarjeta de "Sesión activa" que exhibe el algoritmo `PBKDF2-HMAC-SHA256`, el hash almacenado y la firma `SHA-256` de la bitácora.
- **`usuarios/views.py`** y **`usuarios/urls.py`**: implementadas `login_view`, `registro_view` y `logout_view` con `@sensitive_post_parameters`, `@never_cache`, bloqueo preventivo de 15 minutos tras 5 intentos fallidos (CU-03 4c), mitigación de ataques de tiempo (anti-enumeración) y validación OWASP de claves.
- **`votaciones/templates/votaciones/base.html`** e **`index.html`**: actualizados los enlaces de "Mi cuenta", "Regístrate", "Registro y Cuenta" y "Administración" a `{% url 'login' %}` y `{% url 'panel_principal' %}`.
- **`usuarios/tests.py`**: 6 pruebas automatizadas de seguridad (renderizado, cifrado PBKDF2-SHA256 + firma SHA-256 en bitácora, prevención de duplicados, login/logout, bloqueo tras 5 intentos fallidos y rechazo de inyecciones/claves débiles).

### [6] Admin: Gestión de Categorías
- **`administracion/templates/administracion/categorias.html`**: migración de `admin-categorias.html`. Hereda de
  `admin_base.html`. El contenido (header, 3 KPIs simples, catálogo con búsqueda/filtro, tabla de categorías,
  paginación, tarjetas informativas y nota al pie) va en `{% block contenido %}`; los modales (nueva/editar
  categoría) y el toast en `{% block modales %}`; el bloque `breadcrumb` muestra "Administración > Categorías".
  El CSS específico (botón oscuro, métricas simples, catálogo/tabla, tarjetas informativas y su responsive)
  está en `{% block extra_css %}`; el JS propio de la página (búsqueda en vivo, apertura de modales,
  envío de formularios y toast) en `{% block extra_js %}`.
- **`administracion/views.py`**: `def categorias(request)` -> render con `{'seccion_admin': 'categorias'}`.
- **`administracion/urls.py`**: `path('categorias/', views.categorias, name='categorias')` (ruta `/admin-panel/categorias/`).
- **`_admin_sidebar_nav.html`**: el ítem "Categorías" ahora apunta a `{% url 'categorias' %}`.
- **Convenio:** `admin_base.html` no define `--color-gold-text`; en `categorias.html` se usó `#B48216` directo.
- **Verificación:** `manage.py check` OK; `/admin-panel/categorias/` y `/admin-panel/` responden **200**.

### [7] Usuarios: correcciones tras pruebas funcionales
- **Rama Git:** `feature/migracion-usuarios` (actualizada con `main`).
- **`usuarios/models.py`**: `Bitacora.fecha_hora` pasó de `auto_now_add=True` a `default=timezone.now`
  (`editable=False`). Con `auto_now_add` Django pisaba la fecha en el INSERT después de firmar, así que
  ninguna firma `hash_sha256` coincidía al recalcularla. Se separó `calcular_firma()` y se agregó
  `firma_valida()` para verificar la integridad de una fila.
- **`usuarios/migrations/0002_alter_bitacora_fecha_hora.py`**: migración del cambio anterior
  (hay que correr `manage.py migrate`). Las filas creadas antes de este cambio quedan con firma inválida.
- **`usuarios/views.py`**: `logout_view` ahora tiene `@require_POST` (un GET responde **405**), y el
  parámetro `next` solo se respeta si apunta al mismo sitio (`obtener_next_seguro`, anti open redirect).
- **`votaciones/templates/votaciones/base.html`**: los botones "Cerrar sesión" (navbar y menú móvil)
  pasaron de enlaces GET a botones que envían el formulario oculto `logoutForm` (POST + CSRF).
- **`usuarios/tests.py`**: 3 pruebas nuevas (firma verificable y que detecta alteración, logout por GET
  rechazado, `next` externo ignorado). Total: **9 pruebas OK**.
- **Verificación:** probado en navegador: registro, login con correo y documento, bloqueo tras 5 intentos,
  logout desde la tarjeta, el navbar y el menú móvil; firmas nuevas de la bitácora válidas.

### [8] Usuarios: perfil de usuario (`/usuarios/perfil/`)
- **Rama Git:** `feature/migracion-usuarios`. Pantalla nueva (no existía en el prototipo).
- **`usuarios/views.py`**: `perfil_view` con `@login_required`, `@sensitive_post_parameters` y `@never_cache`.
  Muestra los datos del votante (incluye algoritmo e iteraciones del hash PBKDF2), permite **cambiar la
  contraseña** (pide la actual, mismas reglas y validadores del registro, `update_session_auth_hash` para
  mantener esta sesión y cerrar las demás) y lista **Mi actividad**: los últimos 15 eventos de la bitácora
  con su firma verificada (`firma_valida()`). Una clave actual errónea cuenta para el bloqueo de 5 intentos;
  al bloquear se cierra la sesión.
- **`usuarios/views.py`**: `login_view` redirige al perfil si ya hay sesión; tras login/registro el destino
  por defecto es el perfil; si llega `?next=` abre la pestaña "login" y lo guarda en un hidden. Se extrajeron
  `obtener_perfil()` y `clave_cumple_formato()` para reutilizarlas.
- **`pr_festivalVallenato/settings.py`**: `LOGIN_URL = 'login'` (destino de `@login_required`).
- **`usuarios/templates/usuarios/perfil.html`**: hereda de `votaciones/base.html` (`seccion_activa='cuenta'`).
  Reutiliza el ojo y el medidor de fortaleza de `auth.js` (mismos `id`).
- **`usuarios/templates/usuarios/login.html`**: la tarjeta "Sesión activa" pasó al perfil; sus estilos
  comunes se movieron a **`static/css/usuarios.css`** y las alertas al parcial **`_mensajes.html`**.
- **`usuarios/tests.py`**: clase `PerfilUsuarioTests` con 6 pruebas (acceso sin sesión + `next`, redirección
  del login, datos y actividad, cambio exitoso que cierra las otras sesiones, rechazos, bloqueo tras 5 fallos).
  Total: **15 pruebas OK**.
- **Verificación:** probado en navegador (escritorio y móvil): `/usuarios/perfil/` sin sesión → login → perfil;
  cambio de contraseña con clave actual errónea y correcta; "Mi actividad" con firmas válidas/no válidas.

### [9] Usuarios: perfil organizado con menú lateral
- **Rama Git:** `feature/migracion-usuarios`.
- **Plantillas**: `perfil.html` se dividió en **`perfil_base.html`** (avatar con la inicial, nombre, correo, rol,
  "Miembro desde" y menú lateral: Mis datos, Cambiar contraseña, Mi actividad; abajo "Ir a las votaciones",
  "Panel administrativo" para admins y "Cerrar sesión") y una plantilla por opción: **`perfil_datos.html`**,
  **`perfil_contrasena.html`** y **`perfil_actividad.html`**. Igual que `admin_base.html`, la opción activa la
  marca la variable `seccion_perfil`.
- **Responsive**: en escritorio el menú es una columna de 270px a la izquierda; en celular va arriba con las 3
  opciones en fila (los accesos de abajo se ocultan porque ya están en el menú hamburguesa).
- **`usuarios/views.py`**: `perfil_view` (Mis datos), `perfil_contrasena_view` (el POST del cambio de clave,
  redirige a sí misma) y `perfil_actividad_view`.
- **`usuarios/urls.py`**: `perfil/`, `perfil/contrasena/` (`perfil_contrasena`) y `perfil/actividad/` (`perfil_actividad`).
- **`usuarios/models.py`**: propiedad `Usuario.nombre_visible` (parte del correo antes de la @) para el menú.
- **Nota:** el menú no queda fijo al hacer scroll (`position: sticky`) porque `main.app-viewport` de
  `votaciones/base.html` tiene `overflow` y lo impide.
- **`usuarios/tests.py`**: 3 pruebas nuevas (las 3 secciones piden sesión, el menú marca la sección activa,
  Mi actividad por separado). Total: **18 pruebas OK**.

### [10] Configuración: MySQL y secretos fuera del repositorio (Entrega 2)
- **Rama Git:** `feature/migracion-usuarios`.
- **`pr_festivalVallenato/settings.py`**: la base de datos pasa a **MySQL** (`django.db.backends.mysql`,
  `charset utf8mb4`) y los datos de conexión y la `SECRET_KEY` se leen de un archivo **`.env`** con
  `python-dotenv`. Sin `DJANGO_SECRET_KEY` el proyecto no arranca y lo dice. `DB_ENGINE=sqlite` en el `.env`
  queda solo como respaldo temporal para quien aún no instala MySQL.
- **`.env.example`** (sí va al repo): plantilla con las variables y cómo generar la clave. El **`.env`** real
  no se sube (`.gitignore`). La clave vieja quedó en el historial de git, así que cada quien genera la suya.
- **`requirements.txt`**: `Django==6.1.2`, `mysqlclient==2.3.0` (driver recomendado por Django; en Windows
  se instala sin compilar) y `python-dotenv==1.2.4`.
- **`login.html`**: "Un voto único garantizado por categoría" → "Un voto por encuesta, sin duplicados"
  (la regla RN-03 sigue pendiente de validación; lo implementado es un voto por encuesta).
- **Cómo dejar MySQL listo (una sola vez por equipo):**
  1. Instalar MySQL 8. Ubuntu: `sudo apt install mysql-server pkg-config default-libmysqlclient-dev build-essential python3-dev`
     (los últimos cuatro son para compilar `mysqlclient`). Windows: MySQL Installer (Server 8.4).
  2. Crear la base y el usuario (en Ubuntu con `sudo mysql`; en Windows con MySQL Shell o Workbench como root):
     ```sql
     CREATE DATABASE festival_vallenato CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
     CREATE USER 'festival'@'localhost' IDENTIFIED BY 'una-clave-tuya';
     GRANT ALL PRIVILEGES ON festival_vallenato.* TO 'festival'@'localhost';
     GRANT ALL PRIVILEGES ON test_festival_vallenato.* TO 'festival'@'localhost';
     ```
     (la segunda base la crea Django al correr las pruebas).
  3. Copiar `.env.example` como `.env`, generar la clave y poner la contraseña de MySQL.
  4. `pip install -r requirements.txt`, luego `python manage.py migrate` y `python manage.py createsuperuser`.

## 5. Vistas pendientes (por migrar del prototipo)

Públicas (app `votaciones`):
- [ ] `categorias.html` -> vista Categorías
- [ ] `encuestas.html` -> vista Encuestas
- [ ] `votacion.html` -> vista Votación
- [ ] `exito.html` -> vista Éxito

Autenticación (app `usuarios`):
- [x] `login.html` -> `usuarios/templates/usuarios/login.html` (vistas `login`, `registro`, `logout` en `/usuarios/login/`)
- [x] (nueva, sin prototipo) perfil: `perfil_base.html` + `perfil_datos.html`, `perfil_contrasena.html`,
  `perfil_actividad.html` (en `/usuarios/perfil/`, `/usuarios/perfil/contrasena/`, `/usuarios/perfil/actividad/`)

Admin (app `administracion`, usar `admin_base.html`):
- [x] `admin.html` -> `panel_principal.html` (vista `panel_principal`, `/admin-panel/`)
- [x] `admin-categorias.html` -> `categorias.html` (vista `categorias`, `/admin-panel/categorias/`)
- [ ] `admin-votaciones.html` -> gestión de votaciones (`seccion_admin='votaciones'`)
- [ ] `admin-opciones.html` -> gestión de opciones (`seccion_admin='opciones'`)
- [ ] `admin-resultados.html` -> estadísticas (`seccion_admin='resultados'`)

> Nota: `admin.html` del prototipo NO comparte las mismas variables CSS institucionales
> (`--color-gold: #D8A629`) que el resto; revisar al migrarlo.

