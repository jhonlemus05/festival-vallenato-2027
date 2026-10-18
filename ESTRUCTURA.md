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
│   ├── migrations/
│   ├── templates/
│   │   └── votaciones/
│   │       ├── base.html            # Layout público (Navbar festivo, footer, estilos)
│   │       ├── index.html           # Página de bienvenida / Inicio
│   │       ├── encuestas.html       # Formulario de votación / Preguntas
│   │       └── exito.html           # Pantalla de "Voto registrado con éxito"
│   ├── urls.py                      # Rutas públicas (ej: /, /encuestas/, /exito/)
│   └── views.py                     # Lógica para mostrar encuestas y procesar votos
│
└── administracion/                  # APP 3: Panel de Control (Privado)
    ├── migrations/
    ├── templates/
    │   └── administracion/
    │       ├── admin_base.html      # Layout privado (Sidebar de navegación, barra superior)
    │       ├── panel_principal.html # Vista 'admin' general / Dashboard principal
    │       ├── categorias.html      # Gestión de categorías del festival
    │       ├── opciones.html        # Gestión de opciones por categoría
    │       └── resultados.html      # Visualización de estadísticas y votos en vivo
    ├── urls.py                      # Rutas administrativas (ej: /admin-panel/resultados/)
    └── views.py                     # Lógica del panel (Protegida para que solo entre el staff)
```

## Notas de Implementación

1. **Creación de Apps:** Recuerda ejecutar los comandos `python manage.py startapp usuarios`, `python manage.py startapp votaciones` y `python manage.py startapp administracion` desde la raíz.
2. **Registro:** No olvides añadir `'usuarios',`, `'votaciones',` y `'administracion',` en la lista `INSTALLED_APPS` dentro de tu `settings.py`.
3. **Herencia de Plantillas:** Los archivos de la carpeta `votaciones` heredarán de `votaciones/base.html`, mientras que los archivos de `administracion` utilizarán `administracion/admin_base.html` para mantener sus diseños totalmente independientes.
