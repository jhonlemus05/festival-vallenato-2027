from django.utils.functional import SimpleLazyObject

from .models import Edicion


def edicion_vigente(request):
    """
    Deja `edicion_vigente` en todas las plantillas: el año de los títulos, la marca y el pie salen de la base de
    datos, así una edición nueva (2028) no exige tocar el código. Es perezosa: solo consulta MySQL si la plantilla
    usa la variable. Sin ediciones vale None y `{{ edicion_vigente.anio }}` queda vacío.
    """
    return {'edicion_vigente': SimpleLazyObject(Edicion.vigente)}
