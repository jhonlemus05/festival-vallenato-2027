from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    name = 'usuarios'
    # Nombre de la sección en Django Admin (sin esto saldría "Usuarios", igual que la de auth.User).
    verbose_name = 'Cuentas y auditoría'
