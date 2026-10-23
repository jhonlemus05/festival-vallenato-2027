from django import forms

from votaciones.models import Edicion, Categoria, Encuesta, OpcionEncuesta


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion', 'icono', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Ej. Canción Inédita',
                'maxlength': 100,
            }),
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Describe brevemente esta categoría',
                'maxlength': 220,
            }),
            'icono': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nombre': 'Nombre de la categoría',
            'descripcion': 'Descripción breve',
            'icono': 'Icono representativo',
            'activa': 'Visible y activa en la aplicación pública',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El panel crea las categorías nuevas en la edición vigente (RN-01: ninguna queda sin edición).
        # Las ediciones se administran desde Django Admin.
        if not self.instance.pk and not self.instance.edicion_id:
            edicion = Edicion.vigente()
            if edicion:
                self.instance.edicion = edicion

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.edicion_id:
            raise forms.ValidationError('Primero registra una edición del Festival en Django Admin.')
        return cleaned_data

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        # Solo choca con categorías de la misma edición: "Música" puede repetirse en otro año.
        duplicadas = Categoria.objects.filter(edicion_id=self.instance.edicion_id)
        if self.instance.pk:
            duplicadas = duplicadas.exclude(pk=self.instance.pk)
        if any(nombre.casefold() == nombre_existente.casefold()
               for nombre_existente in duplicadas.values_list('nombre', flat=True)):
            raise forms.ValidationError('Ya existe una categoría con ese nombre.')
        return nombre

    def clean_descripcion(self):
        return self.cleaned_data['descripcion'].strip()


class EncuestaForm(forms.ModelForm):
    class Meta:
        model = Encuesta
        fields = ['nombre', 'descripcion', 'detalle', 'estado']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Ej. Acordeonista',
                'maxlength': 120,
            }),
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Descripción breve de la encuesta',
                'maxlength': 220,
            }),
            'detalle': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Ej. 4 participantes · Un voto por persona',
                'maxlength': 160,
            }),
            'estado': forms.Select(attrs={'class': 'form-select rounded-3'}),
        }
        labels = {
            'nombre': 'Nombre de la encuesta',
            'descripcion': 'Descripción',
            'detalle': 'Información adicional',
            'estado': 'Estado',
        }

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre')
        categoria = self.instance.categoria if self.instance.categoria_id else None
        if nombre and categoria:
            duplicadas = Encuesta.objects.filter(categoria=categoria, nombre__iexact=nombre.strip())
            if self.instance.pk:
                duplicadas = duplicadas.exclude(pk=self.instance.pk)
            if duplicadas.exists():
                self.add_error('nombre', 'Ya existe una encuesta con ese nombre en esta categoría.')
        return cleaned_data

    def clean_nombre(self):
        return self.cleaned_data['nombre'].strip()

    def clean_descripcion(self):
        return self.cleaned_data['descripcion'].strip()

    def clean_detalle(self):
        return self.cleaned_data['detalle'].strip()


class OpcionEncuestaForm(forms.ModelForm):
    class Meta:
        model = OpcionEncuesta
        fields = ['nombre', 'descripcion', 'imagen']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Nombre del candidato o alternativa',
                'maxlength': 120,
            }),
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Frase, obra o información breve',
                'maxlength': 160,
            }),
            'imagen': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'images/participante.jpg',
                'maxlength': 255,
            }),
        }
        labels = {
            'nombre': 'Nombre del candidato u opción',
            'descripcion': 'Descripción',
            'imagen': 'Ruta de imagen en archivos estáticos (opcional)',
        }
        help_texts = {
            'imagen': 'Usa una ruta dentro de static, por ejemplo: images/participante.jpg.',
        }

    def __init__(self, *args, encuesta, **kwargs):
        self.encuesta = encuesta
        super().__init__(*args, **kwargs)

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        duplicadas = OpcionEncuesta.objects.filter(
            encuesta=self.encuesta,
            nombre__iexact=nombre,
        )
        if self.instance.pk:
            duplicadas = duplicadas.exclude(pk=self.instance.pk)
        if duplicadas.exists():
            raise forms.ValidationError('Ya existe una opción con ese nombre en esta encuesta.')
        return nombre

    def clean_descripcion(self):
        return self.cleaned_data['descripcion'].strip()

    def clean_imagen(self):
        imagen = self.cleaned_data['imagen'].strip()
        if (
            imagen.startswith('/')
            or '\\' in imagen
            or ':' in imagen
            or '..' in imagen.split('/')
        ):
            raise forms.ValidationError('Indica una ruta relativa dentro de los archivos estáticos.')
        return imagen
