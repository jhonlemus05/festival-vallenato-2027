import hashlib
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Usuario(models.Model):
    """
    Perfil extendido del votante / administrador (tabla `usuario` del MER del Eje 1).

    Decisión de diseño: NO reinventamos la autenticación. Django ya trae `auth.User`
    con hashing, sesiones y permisos, así que este modelo cuelga de él con un
    OneToOne y solo guarda lo que el negocio necesita (documento, rol, bloqueo...).
    Así evitamos tocar `AUTH_USER_MODEL` y no rompemos las migraciones de los demás
    módulos del equipo.
    """

    ROLES = [
        ('votante', 'Votante'),
        ('administrador', 'Administrador'),
        ('auditor', 'Auditor'),
    ]

    # Política anti fuerza bruta (CU-03, flujo alterno 4c). Se dejan como constantes
    # de clase para que las vistas y los tests lean el mismo valor sin números mágicos.
    MAX_INTENTOS_FALLIDOS = 5
    MINUTOS_BLOQUEO = 15

    # Si se borra el User de Django, se borra también su perfil.
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil_usuario',
        verbose_name='Usuario del sistema',
    )
    # Documento único: es lo que garantiza "una persona = un votante" más adelante,
    # junto con la restricción de un voto por encuesta (la regla definitiva, RN-03, sigue
    # pendiente de validación con la Fundación).
    identificacion = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Número de documento',
    )
    correo = models.EmailField(
        max_length=150,
        unique=True,
        verbose_name='Correo electrónico',
    )
    # Copia del hash de `auth.User.password` (formato `pbkdf2_sha256$iter$salt$hash`).
    # Existe para que el MER (columna `password_hash`) quede evidenciado en BD y en
    # el Admin. La fuente de verdad sigue siendo `User.password`; se sincroniza en save().
    password_hash = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Hash de contraseña (PBKDF2-SHA256)',
    )
    rol = models.CharField(
        max_length=50,
        choices=ROLES,
        default='votante',
        verbose_name='Rol',
    )
    # Aceptación de la política de datos (Ley 1581 de 2012).
    acepta_terminos = models.BooleanField(
        default=True,
        verbose_name='Acepta tratamiento de datos',
    )
    # Estado del mecanismo de bloqueo temporal.
    intentos_fallidos = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Intentos fallidos de acceso',
    )
    bloqueado_hasta = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Bloqueado temporalmente hasta',
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de registro',
    )

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-fecha_registro']

    def save(self, *args, **kwargs):
        # Mantiene `password_hash` espejado con el hash real de Django. Ojo: esto copia
        # el hash ya calculado, jamás la clave en texto plano.
        if self.user_id and self.user.password:
            self.password_hash = self.user.password
        super().save(*args, **kwargs)

    def esta_bloqueado(self):
        """
        Devuelve True si la cuenta sigue bloqueada.

        Efecto secundario intencional: si el bloqueo ya venció, lo limpia aquí mismo
        (contador a 0 y `bloqueado_hasta` a None). Así no necesitamos un cron ni una
        tarea periódica: el desbloqueo es "perezoso" y ocurre en el siguiente intento.
        """
        if self.bloqueado_hasta and self.bloqueado_hasta > timezone.now():
            return True
        if self.bloqueado_hasta and self.bloqueado_hasta <= timezone.now():
            self.intentos_fallidos = 0
            self.bloqueado_hasta = None
            self.save(update_fields=['intentos_fallidos', 'bloqueado_hasta'])
        return False

    def minutos_restantes_bloqueo(self):
        """Minutos que faltan para el desbloqueo, redondeados hacia arriba (mínimo 1) para mostrar en el mensaje."""
        if not self.bloqueado_hasta:
            return 0
        restante = (self.bloqueado_hasta - timezone.now()).total_seconds()
        return max(1, int((restante + 59) // 60))

    def registrar_intento_fallido(self):
        """
        Suma un intento fallido y bloquea al llegar al umbral.

        Retorna True únicamente en el intento que dispara el bloqueo; la vista lo usa
        para decidir qué mensaje mostrar y qué evento escribir en la bitácora.
        """
        self.intentos_fallidos += 1
        bloqueado = False
        if self.intentos_fallidos >= self.MAX_INTENTOS_FALLIDOS:
            self.bloqueado_hasta = timezone.now() + timedelta(minutes=self.MINUTOS_BLOQUEO)
            bloqueado = True
        # update_fields evita pisar otros campos si hay accesos concurrentes.
        self.save(update_fields=['intentos_fallidos', 'bloqueado_hasta'])
        return bloqueado

    def reiniciar_intentos(self):
        """Limpia el contador tras un login exitoso. Solo escribe en BD si había algo que limpiar."""
        if self.intentos_fallidos > 0 or self.bloqueado_hasta is not None:
            self.intentos_fallidos = 0
            self.bloqueado_hasta = None
            self.save(update_fields=['intentos_fallidos', 'bloqueado_hasta'])

    @property
    def nombre_visible(self):
        """Parte del correo antes de la @. El modelo no guarda nombre, así que es lo que se muestra en el perfil."""
        return self.correo.split('@')[0]

    def __str__(self):
        return f"{self.correo} ({self.identificacion})"


class Bitacora(models.Model):
    """
    Registro de auditoría de eventos de autenticación (tabla `bitacora` del MER).

    Cada fila lleva una firma SHA-256 calculada al crearla. Ojo con el alcance: la
    firma permite DETECTAR manipulación (recalculas y comparas), no la impide. Para
    inmutabilidad real habría que quitar el permiso de UPDATE/DELETE en la BD.
    """

    # SET_NULL: si se elimina un usuario, el historial de auditoría se conserva
    # (con usuario nulo) en vez de borrarse en cascada.
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bitacoras',
        verbose_name='Usuario',
    )
    accion = models.CharField(
        max_length=150,
        verbose_name='Acción',
    )
    detalles = models.TextField(
        blank=True,
        verbose_name='Detalles',
    )
    ip_origen = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP de origen',
    )
    # editable=False: no aparece en formularios del Admin, solo lectura.
    hash_sha256 = models.CharField(
        max_length=64,
        blank=True,
        editable=False,
        verbose_name='Firma de integridad SHA-256',
    )
    # default (y NO auto_now_add): auto_now_add pisa la fecha en el INSERT, después de que
    # save() ya firmó con otra, y la firma nunca volvería a coincidir al verificarla.
    fecha_hora = models.DateTimeField(
        default=timezone.now,
        editable=False,
        verbose_name='Fecha y hora',
    )

    class Meta:
        db_table = 'bitacora'
        verbose_name = 'Bitácora'
        verbose_name_plural = 'Bitácoras'
        ordering = ['-fecha_hora']

    def calcular_firma(self):
        """SHA-256 de los campos auditados. Lo usan save() al firmar y firma_valida() al verificar."""
        identificador = str(self.usuario_id or 'anonimo')
        # Se concatena SECRET_KEY como "pimienta": sin ella cualquiera con acceso a la BD
        # podría recalcular un hash válido tras alterar una fila.
        payload = f"{identificador}|{self.accion}|{self.detalles}|{self.ip_origen or ''}|{self.fecha_hora.isoformat()}|{settings.SECRET_KEY}"
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def firma_valida(self):
        """True si la fila no se alteró desde que se creó (la firma recalculada coincide con la guardada)."""
        return bool(self.hash_sha256) and self.hash_sha256 == self.calcular_firma()

    def save(self, *args, **kwargs):
        # Solo se firma una vez (al crear). Si ya trae hash, no se recalcula.
        if not self.hash_sha256:
            self.hash_sha256 = self.calcular_firma()
        super().save(*args, **kwargs)

    def __str__(self):
        correo = self.usuario.correo if self.usuario else 'Anónimo'
        return f"{correo} - {self.accion}"
