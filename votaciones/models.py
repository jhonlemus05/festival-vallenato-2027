import secrets

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from usuarios.models import Bitacora


class Edicion(models.Model):
    """Edición anual del Festival: primer nivel de la jerarquía Edición → Categoría → Votación → Opción (RN-01)."""

    ESTADOS = [
        ('preparacion', 'En preparación'),
        ('activa', 'Activa'),
        ('finalizada', 'Finalizada'),
    ]

    nombre = models.CharField(max_length=150, verbose_name='Nombre')
    anio = models.PositiveSmallIntegerField(unique=True, verbose_name='Año')
    fecha_inicio = models.DateField(verbose_name='Fecha de inicio')
    fecha_fin = models.DateField(verbose_name='Fecha de finalización')
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='preparacion',
        verbose_name='Estado',
    )

    class Meta:
        ordering = ['-anio']
        verbose_name = 'Edición'
        verbose_name_plural = 'Ediciones'

    def __str__(self):
        return f'{self.nombre} ({self.anio})'

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError({'fecha_fin': 'La fecha de finalización no puede ser anterior a la de inicio.'})

    @classmethod
    def vigente(cls):
        """La edición que ve el público: la activa más reciente o, si no hay activa, la más reciente."""
        return cls.objects.filter(estado='activa').first() or cls.objects.first()


class Categoria(models.Model):
    ICONOS = [
        ('music', 'Nota musical'),
        ('flower', 'Danza y flores'),
        ('mask', 'Máscaras'),
        ('trophy', 'Trofeo'),
    ]

    # PROTECT: no se puede borrar una edición que todavía tiene categorías (y con ellas votos).
    edicion = models.ForeignKey(
        Edicion,
        on_delete=models.PROTECT,
        related_name='categorias',
        verbose_name='Edición',
    )
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
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
        # El nombre se repite entre ediciones (Música 2027, Música 2028), no dentro de una misma.
        constraints = [
            models.UniqueConstraint(
                fields=['edicion', 'nombre'],
                name='votacion_categoria_unica_por_edicion',
            ),
        ]
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
    # RN-05: fecha y hora exactas de apertura y cierre. Son opcionales; si se ponen, el estado
    # cambia solo al llegar cada una (ver actualizar_estados_por_fecha y EstadoEncuestasMiddleware).
    fecha_apertura = models.DateTimeField(null=True, blank=True, verbose_name='Apertura')
    fecha_cierre = models.DateTimeField(null=True, blank=True, verbose_name='Cierre')
    orden = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'Encuesta'
        verbose_name_plural = 'Encuestas'

    def __str__(self):
        return f'{self.categoria.nombre} - {self.nombre}'

    def clean(self):
        # CU-06, flujo 5b: el cierre no puede ser anterior (ni igual) a la apertura.
        if self.fecha_apertura and self.fecha_cierre and self.fecha_cierre <= self.fecha_apertura:
            raise ValidationError({'fecha_cierre': 'El cierre debe ser posterior a la apertura.'})


def actualizar_estados_por_fecha():
    """
    Abre y cierra encuestas según sus fechas (RN-05) y deja cada cambio en la bitácora (CU-07, paso 6).

    "Próximamente" con apertura cumplida → Activa. Activa o Próximamente con cierre cumplido → Cerrada.
    Es un cambio "perezoso": se revisa en cada petición, así no hace falta un cron.
    """
    ahora = timezone.now()
    cambios = []
    for encuesta in Encuesta.objects.filter(estado__in=['activa', 'proxima'], fecha_cierre__lte=ahora):
        cambios.append((encuesta, 'cerrada', 'Cierre automático de encuesta'))
    for encuesta in Encuesta.objects.filter(estado='proxima', fecha_apertura__lte=ahora).exclude(fecha_cierre__lte=ahora):
        cambios.append((encuesta, 'activa', 'Apertura automática de encuesta'))

    for encuesta, estado, accion in cambios:
        # El filtro por estado evita registrar dos veces el mismo cambio si dos peticiones llegan a la par.
        actualizadas = Encuesta.objects.filter(pk=encuesta.pk, estado=encuesta.estado).update(estado=estado)
        if actualizadas:
            Bitacora.objects.create(
                usuario=None,
                accion=accion,
                detalles=f'Encuesta «{encuesta.nombre}» pasó a {dict(Encuesta.ESTADOS)[estado]} por su fecha programada',
            )
    return len(cambios)


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
    # Comprobante del voto (CU-04, CU-05 y MER de la Entrega 1). Permite verificar que el voto
    # quedó registrado sin revelar la opción elegida.
    codigo_comprobante = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name='Código de comprobante',
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

    def save(self, *args, **kwargs):
        if not self.codigo_comprobante:
            self.codigo_comprobante = generar_codigo_comprobante()
        super().save(*args, **kwargs)


# Sin 0/O ni 1/I para que el código se pueda dictar o copiar a mano sin confusiones.
ALFABETO_COMPROBANTE = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generar_codigo_comprobante():
    """
    Código tipo FV-7K2Q-M9XA: 8 caracteres de 32 posibles (~10^12 combinaciones), con `secrets`
    (aleatorio criptográfico) para que no se pueda adivinar el de otra persona. Se revisa que no exista.
    """
    while True:
        cuerpo = ''.join(secrets.choice(ALFABETO_COMPROBANTE) for _ in range(8))
        codigo = f'FV-{cuerpo[:4]}-{cuerpo[4:]}'
        if not Voto.objects.filter(codigo_comprobante=codigo).exists():
            return codigo
