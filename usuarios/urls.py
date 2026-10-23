from django.urls import path
from . import views

# Todas estas rutas cuelgan de `/usuarios/` (ver pr_festivalVallenato/urls.py).
# Los `name` son los que usan los templates con {% url '...' %}; sin namespace,
# igual que `index` y `panel_principal`, para mantener la convención del proyecto.
urlpatterns = [
    # `/usuarios/` y `/usuarios/login/` apuntan a la misma vista (pantalla con pestañas registro/login).
    path('', views.login_view, name='usuarios_index'),
    path('login/', views.login_view, name='login'),
    # Atajo que abre directamente la pestaña "Registrarse".
    path('registro/', views.registro_view, name='registro'),
    # Perfil (requiere sesión): una URL por cada opción del menú lateral.
    path('perfil/', views.perfil_view, name='perfil'),
    path('perfil/contrasena/', views.perfil_contrasena_view, name='perfil_contrasena'),
    path('perfil/actividad/', views.perfil_actividad_view, name='perfil_actividad'),
    path('logout/', views.logout_view, name='logout'),
]
