from .models import actualizar_estados_por_fecha


class EstadoEncuestasMiddleware:
    """
    Antes de cada petición abre o cierra las encuestas cuya fecha ya se cumplió (RN-05).

    Así ninguna vista (pública, panel o Django Admin) muestra una encuesta abierta después de su
    cierre, y no hace falta una tarea programada (cron) para cerrarlas a tiempo.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        actualizar_estados_por_fecha()
        return self.get_response(request)
