from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .views import registrar_evento_bitacora


def es_administrador(user):
    """Administrador = cuenta staff de Django (createsuperuser) o perfil con rol 'administrador'."""
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    # Sin perfil, el acceso inverso del OneToOne lanza un error que también es AttributeError.
    perfil = getattr(user, 'perfil_usuario', None)
    return perfil is not None and perfil.rol == 'administrador'


def administrador_requerido(vista):
    """
    Protege las vistas del panel administrativo (RNF-01, riesgo R5102).

    Sin sesión → al login con ?next=. Con sesión pero sin rol de administrador → 403.
    Ojo: a quien ya tiene sesión no se le manda al login, porque el login lo devolvería
    al `next` y quedaría en un bucle de redirecciones.
    """
    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not es_administrador(request.user):
            registrar_evento_bitacora(
                request,
                getattr(request.user, 'perfil_usuario', None),
                'Acceso denegado al panel administrativo',
                f'Intento de entrar a {request.path} sin rol de administrador',
            )
            raise PermissionDenied
        return vista(request, *args, **kwargs)
    return envoltura
