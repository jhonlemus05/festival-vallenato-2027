from django import forms

from .models import OpcionEncuesta


class VotoForm(forms.Form):
    """
    Valida en el servidor la opción enviada por POST. El queryset se limita a la encuesta que se está
    votando: una opción de otra encuesta, categoría o edición es inválida aunque exista en MySQL.
    """

    opcion = forms.ModelChoiceField(
        queryset=OpcionEncuesta.objects.none(),
        error_messages={
            'required': 'Selecciona una opción válida para registrar tu voto.',
            'invalid_choice': 'La opción enviada no pertenece a esta votación.',
        },
    )

    def __init__(self, *args, encuesta, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['opcion'].queryset = encuesta.opciones.all()
