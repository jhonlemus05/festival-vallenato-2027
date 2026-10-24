from .permisos import es_administrador


def permisos(request):
    """Deja `es_administrador` en todas las plantillas (p. ej. para mostrar el enlace al panel)."""
    return {'es_administrador': es_administrador(request.user)}
