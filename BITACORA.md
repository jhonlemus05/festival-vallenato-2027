# BITÁCORA DEL PROYECTO — Festival de la Leyenda Vallenata 2027

> Este archivo registra cada modificación hecha al proyecto para mantener el contexto
> entre sesiones/modelos. **Actualizar siempre que se haga un cambio.**

## 1. Descripción general

Migración de un prototipo HTML estático (`festival-de-la-leyenda-vallenata-2027---sistema-de-votación-ciudadana/`)
a un proyecto **Django**. Se migra **vista por vista**. Los assets (CSS/JS/imágenes) pasan a `static/`
y las vistas usan plantillas con herencia (`base.html` + página hija).

## 2. Estructura del proyecto

```
D:\no_borrar\programacion\Python\Django\
├── manage.py
├── db.sqlite3
├── env_django\                     # Entorno virtual (python.exe aquí)
├── pr_festivalVallenato\           # Configuración del proyecto Django
│   ├── settings.py
│   ├── urls.py                     # admin/  y  home/ -> include('home.urls')
│   └── ...
├── home\                           # App Django (startapp)
│   ├── views.py
│   ├── urls.py                     # '' -> views.home  (name='home')
│   ├── models.py
│   └── templates\home\
│       ├── base.html               # Plantilla base compartida
│       └── inicio.html             # Vista Inicio (home)
├── static\                         # Estáticos del proyecto (STATICFILES_DIRS)
│   ├── css\responsive.css
│   ├── js\countdown.js
│   ├── js\navigation.js
│   └── images\hero_accordionist_banner_1791518403166.jpg
└── festival-de-la-leyenda-vallenata-2027---...-ciudadana\   # Prototipo fuente (referencia)
```

## 3. Convenios usados

- **Python/pip:** usar `env_django\Scripts\python.exe` (ej: `& "env_django\Scripts\python.exe" manage.py check`).
- **Rutas Django:** `home` está montada en `/home/` (nombre de URL `home`). Para abrir la vista: `http://127.0.0.1:8000/home/`.
- **Estáticos:** referenciar con `{% static '...' %}`. `settings.py` tiene `STATICFILES_DIRS = [BASE_DIR / 'static']`.
- **Plantillas:** cada página hereda de `home/base.html`; el contenido propio va en `{% block contenido %}`
  y el CSS propio de la página en `{% block extra_css %}`. El base expone `{% block titulo %}`,
  `{% block descripcion %}`, `{% block contenido %}`, `{% block extra_css %}`, `{% block extra_js %}`.
- **Navegación activa:** el base usa la variable de contexto `seccion_activa` (valores: `inicio`,
  `categorias`, `cuenta`, `admin`). La vista debe pasarla.
- **Enlaces a vistas no migradas:** quedaron como `href="#"` (placeholders) y se irán reemplazando
  por `{% url '...' %}` cuando exista cada vista.
- **Idioma:** contenido en español. NO agregar comentarios al código salvo lo ya presente.

## 4. Registro de cambios

### [1] Vistas: Home (plantilla base + inicio)
- **`pr_festivalVallenato/settings.py`**: se agregó `STATICFILES_DIRS = [BASE_DIR / 'static']`.
- **`static/`**: se creó con `css/responsive.css`, `js/countdown.js`, `js/navigation.js`
  e `images/hero_accordionist_banner_1791518403166.jpg` (copiados del prototipo).
- **`static/css/responsive.css`**: se cambió la ruta de la imagen de fondo de
  `/src/assets/images/...` a `/static/images/...`.
- **`home/templates/home/base.html`**: reescrito como plantilla base institucional. Incluye
  head (Google Fonts, Bootstrap 5.3, Bootstrap Icons, `responsive.css`), variables CSS
  institucionales (`--color-gold: #D8A629`, etc.), encabezado, footer desktop, navbar inferior móvil,
  offcanvas lateral y scripts (`countdown.js`, `navigation.js`).
- **`home/templates/home/inicio.html`**: creado a partir del `index.html` del prototipo.
  Contiene el hero (foto acordeonero + titulares) y la sección de cuenta regresiva/CTA/preview de
  categorías. El CSS específico de esta página está en `{% block extra_css %}`.
- **`home/views.py`**: la vista `home` ahora hace `render(request, 'home/inicio.html', {'seccion_activa': 'inicio'})`
  (se eliminó el contexto de ejemplo del blog).
- **Verificación:** `manage.py check` sin errores; la vista responde **200** y renderiza estáticos.

### [2] Control de versiones (Git)
- **`.gitignore`**: creado en la raíz. Excluye `env_django/`, `__pycache__/`, `*.pyc`, `db.sqlite3`,
  `/staticfiles/`, `/media/`, `.env`, archivos de IDE y de sistema. **La carpeta del prototipo
  `festival-de-la-leyenda-vallenata-2027---sistema-de-votación-ciudadana/` SÍ se versiona** (pesa ~4.4 MB)
  como referencia de diseño. El repo todavía NO se ha inicializado (`git init` pendiente, lo hace el usuario).
- Entorno: Git 2.55 (Windows), usuario global `jhonlemus05 <jhonlemus05@gmail.com>`. No hay `gh` CLI.

## 5. Vistas pendientes (por migrar del prototipo)

- [ ] `categorias.html` -> vista Categorías
- [ ] `encuestas.html` -> vista Encuestas
- [ ] `votacion.html` -> vista Votación
- [ ] `login.html` -> vista Login / Registro
- [ ] `exito.html` -> vista Éxito
- [ ] `admin.html`, `admin-categorias.html`, `admin-opciones.html`, `admin-resultados.html`, `admin-votaciones.html` -> vistas de administración

> Nota: `admin.html` del prototipo NO comparte las mismas variables CSS institucionales
> (`--color-gold: #D8A629`) que el resto; revisar al migrarlo.
