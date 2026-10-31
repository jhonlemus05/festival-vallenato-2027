# Estructura del Proyecto: pr_festivalVallenato

Este proyecto está organizado en **3 aplicaciones modulares** para separar la lógica de autenticación, la experiencia pública del votante y el panel de control administrativo.

```text
pr_festivalVallenato/
│
├── manage.py                        # Script de gestión de Django
│
├── pr_festivalVallenato/            # Carpeta de configuración del proyecto
│   ├── __init__.py
│   ├── settings.py                  # Configuración global (Base de datos, Apps, etc.)
│   ├── urls.py                      # Enrutador principal (Redirige a las URLs de cada app)
│   └── wsgi.py / asgi.py
│
├── static/                          # Archivos estáticos globales (Opcional)
│   ├── css/                         # Estilos compartidos
│   ├── js/                          # Scripts compartidos
│   └── imagenes/                    # Logos y recursos visuales del festival
│
├── usuarios/                        # APP 1: Gestión de Autenticación
│   ├── migrations/
│   ├── templates/
│   │   └── usuarios/
│   │       └── login.html           # Formulario de ingreso
│   ├── urls.py                      # Rutas de usuarios (ej: /usuarios/login/)
│   └── views.py                     # Lógica de inicio y cierre de sesión
│
├── votaciones/                      # APP 2: Experiencia del Votante (Pública)
│   ├── migrations/                  # Categorías, encuestas, opciones y votos
│   ├── templates/
│   │   └── votaciones/
│   │       ├── base.html            # Layout público (Navbar festivo, footer, estilos)
│   │       ├── index.html           # Página de bienvenida / Inicio
│   │       ├── categorias.html       # Catálogo público de categorías activas
│   │       ├── encuestas_categoria.html # Encuestas de una categoría
│   │       ├── votacion.html         # Selección y confirmación de voto
│   │       └── exito.html            # Comprobante de voto registrado
│   ├── forms.py                     # VotoForm: valida en el servidor la opción enviada
│   ├── models.py                    # Edicion, Categoria, Encuesta, OpcionEncuesta y Voto
│   ├── urls.py                      # Catálogo, detalle de encuesta, voto, confirmación y API
│   └── views.py                     # Catálogo, flujo público de votación y API GET
│
└── administracion/                  # APP 3: Panel de Control (modo de demostración)
    ├── migrations/
    ├── templates/
    │   └── administracion/
    │       ├── admin_base.html      # Layout privado (Sidebar de navegación, barra superior)
    │       ├── panel_principal.html # Vista 'admin' general / Dashboard principal
    │       ├── categorias.html      # Gestión de categorías y encuestas
    │       ├── votaciones.html      # Estado y resultados agregados por opción
    │       └── votos.html           # Consulta de los votos registrados
    ├── forms.py                     # Formularios de categorías, encuestas y candidatos/opciones
    ├── urls.py                      # Rutas de categorías, votaciones y resultados
    └── views.py                     # Gestión de categorías y vistas del panel
```
