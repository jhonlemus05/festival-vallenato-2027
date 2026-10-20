from django.contrib import admin
from .models import Usuario, Bitacora


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    # Columnas pensadas para soporte: de un vistazo se ve quién está bloqueado y por qué.
    list_display = (
        'id',
        'correo',
        'identificacion',
        'rol',
        'intentos_fallidos',
        'bloqueado_hasta',
        'fecha_registro',
    )
    list_filter = ('rol', 'acepta_terminos', 'fecha_registro')
    # `user__username` permite buscar atravesando la relación OneToOne hacia auth.User.
    search_fields = ('correo', 'identificacion', 'user__username')
    # El hash es solo de lectura: se sincroniza solo desde User.password (ver Usuario.save).
    readonly_fields = ('password_hash', 'fecha_registro')


@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'accion', 'ip_origen', 'hash_sha256', 'fecha_hora')
    list_filter = ('accion', 'fecha_hora')
    search_fields = ('usuario__correo', 'usuario__identificacion', 'accion', 'detalles', 'hash_sha256')
    # La firma y la fecha no deben editarse a mano desde el Admin: sería falsear la auditoría.
    readonly_fields = ('hash_sha256', 'fecha_hora')
