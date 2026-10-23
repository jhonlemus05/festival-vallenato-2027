from django.contrib import admin
from .models import Categoria, Encuesta, OpcionEncuesta, Voto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activa', 'orden', 'fecha_actualizacion')
    list_filter = ('activa',)
    search_fields = ('nombre', 'descripcion')
    ordering = ('orden', 'nombre')


@admin.register(Encuesta)
class EncuestaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'estado', 'orden', 'fecha_actualizacion')
    list_filter = ('categoria', 'estado')
    search_fields = ('nombre', 'descripcion', 'categoria__nombre')
    ordering = ('categoria__orden', 'orden', 'nombre')


@admin.register(OpcionEncuesta)
class OpcionEncuestaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'encuesta', 'orden')
    list_filter = ('encuesta__categoria', 'encuesta')
    search_fields = ('nombre', 'descripcion', 'encuesta__nombre')
    ordering = ('encuesta__orden', 'orden', 'nombre')


@admin.register(Voto)
class VotoAdmin(admin.ModelAdmin):
    list_display = ('encuesta', 'opcion', 'fecha_creacion')
    list_filter = ('encuesta__categoria', 'encuesta')
    ordering = ('-fecha_creacion',)
    readonly_fields = ('encuesta', 'opcion', 'usuario', 'fecha_creacion')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
