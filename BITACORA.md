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
│   ├── js\countdown.js
│   ├── js\navigation.js
│   └── images\hero_accordionist_banner_1791518403166.jpg
├── usuarios\                       # APP 1: autenticación (aún sin vistas)
│   ├── templates\usuarios\         # (vacío)
│   ├── urls.py                     # urlpatterns = [] (pendiente)
│   └── views.py
├── votaciones\                     # APP 2: experiencia pública (MIGRANDO)
│   ├── templates\votaciones\
│   │   ├── base.html               # Layout público (navbar, footer, offcanvas, scripts)
│   │   └── index.html              # Página de Inicio (ex inicio.html)
│   ├── urls.py                     # '' -> views.index (name='index')
│   └── views.py                    # def index(...)
├── administracion\                 # APP 3: panel privado (aún sin vistas)
│   ├── templates\administracion\   # (vacío)
│   ├── urls.py                     # urlpatterns = [] (pendiente)
│   └── views.py
└── festival-de-la-leyenda-vallenata-2027---...-ciudadana\   # Prototipo fuente (referencia)
```

## 3. Convenios usados

- **Python/pip:** usar `env_django\Scripts\python.exe` (ej: `& "env_django\Scripts\python.exe" manage.py check`).
- **Rutas Django:**
  - `votaciones` montada en **`/`** (raíz). Inicio: `http://127.0.0.1:8000/` (nombre de URL `index`).
  - `usuarios` en `/usuarios/` y `administracion` en `/admin-panel/` (aún sin rutas internas).
- **Estáticos:** referenciar con `{% static '...' %}`. `settings.py` tiene `STATICFILES_DIRS = [BASE_DIR / 'static']`.
- **Plantillas:** cada página hereda de la base de su app:
  - Público: `votaciones/base.html` (bloques `titulo`, `descripcion`, `contenido`, `extra_css`, `extra_js`).
  - Admin (futuro): `administracion/admin_base.html`.
- **Navegación activa:** el base usa la variable de contexto `seccion_activa` (valores: `inicio`,
  `categorias`, `cuenta`, `admin`). La vista debe pasarla.
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

## 5. Vistas pendientes (por migrar del prototipo)

Públicas (app `votaciones`):
- [ ] `categorias.html` -> vista Categorías
- [ ] `encuestas.html` -> vista Encuestas
- [ ] `votacion.html` -> vista Votación
- [ ] `exito.html` -> vista Éxito

Autenticación (app `usuarios`):
- [ ] `login.html` -> vista Login / Registro

Admin (app `administracion`, usar `admin_base.html`):
- [ ] `admin.html` -> panel principal
- [ ] `admin-categorias.html` -> gestión de categorías
- [ ] `admin-opciones.html` -> gestión de opciones
- [ ] `admin-resultados.html` -> estadísticas
- [ ] `admin-votaciones.html` -> gestión de votaciones

> Nota: `admin.html` del prototipo NO comparte las mismas variables CSS institucionales
> (`--color-gold: #D8A629`) que el resto; revisar al migrarlo.
