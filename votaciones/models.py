from django.db import models
from django.conf import settings


class Categoria(models.Model):
    ICONOS = [
        ('music', 'Nota musical'),
        ('flower', 'Danza y flores'),
        ('mask', 'Máscaras'),
        ('trophy', 'Trofeo'),
    ]

    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    descripcion = models.CharField(max_length=220, verbose_name='Descripción')
    icono = models.CharField(
        max_length=20,
        choices=ICONOS,
        default='music',
        verbose_name='Icono',
    )
    activa = models.BooleanField(default=True, verbose_name='Visible en la aplicación')
    orden = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def __str__(self):
        return self.nombre


class Encuesta(models.Model):
    ESTADOS = [
        ('activa', 'Activa'),
        ('proxima', 'Próximamente'),
        ('cerrada', 'Cerrada'),
    ]

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name='encuestas',
        verbose_name='Categoría',
    )
    nombre = models.CharField(max_length=120, verbose_name='Nombre')
    descripcion = models.CharField(max_length=220, verbose_name='Descripción')
    detalle = models.CharField(
        max_length=160,
        blank=True,
        verbose_name='Información adicional',
    )
    estado = models.CharField(
        max_length=10,
        choices=ESTADOS,
        default='proxima',
        verbose_name='Estado',
    )
    orden = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'Encuesta'
        verbose_name_plural = 'Encuestas'

    def __str__(self):
        return f'{self.categoria.nombre} - {self.nombre}'


class OpcionEncuesta(models.Model):
    encuesta = models.ForeignKey(
        Encuesta,
        on_delete=models.CASCADE,
        related_name='opciones',
        verbose_name='Encuesta',
    )
    nombre = models.CharField(max_length=120, verbose_name='Nombre')
    descripcion = models.CharField(max_length=160, blank=True, verbose_name='Descripción')
    imagen = models.CharField(max_length=255, blank=True, verbose_name='Ruta de imagen')
    orden = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'Opción de encuesta'
        verbose_name_plural = 'Opciones de encuesta'

    def __str__(self):
        return f'{self.encuesta.nombre} - {self.nombre}'


class Voto(models.Model):
    encuesta = models.ForeignKey(
        Encuesta,
        on_delete=models.CASCADE,
        related_name='votos',
        verbose_name='Encuesta',
    )
    opcion = models.ForeignKey(
        OpcionEncuesta,
        on_delete=models.CASCADE,
        related_name='votos',
        verbose_name='Opción elegida',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='votos_festival',
        verbose_name='Votante',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha del voto')

    class Meta:
        ordering = ['-fecha_creacion']
        constraints = [
            models.UniqueConstraint(
                fields=['encuesta', 'usuario'],
                name='votacion_un_voto_por_usuario_encuesta',
            ),
        ]
        verbose_name = 'Voto'
        verbose_name_plural = 'Votos'

    def __str__(self):
        return f'{self.usuario} - {self.encuesta.nombre}: {self.opcion.nombre}'
