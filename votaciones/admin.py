from django.contrib import admin
from .models import Edicion, Categoria, Encuesta, OpcionEncuesta, Voto


class CategoriaInline(admin.TabularInline):
    model = Categoria
    fields = ('nombre', 'descripcion', 'icono', 'activa', 'orden')
    extra = 0


@admin.register(Edicion)
class EdicionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'anio', 'fecha_inicio', 'fecha_fin', 'estado')
    list_filter = ('estado',)
    search_fields = ('nombre',)
    inlines = [CategoriaInline]


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'edicion', 'activa', 'orden', 'fecha_actualizacion')
    list_filter = ('edicion', 'activa')
    search_fields = ('nombre', 'descripcion')
    ordering = ('-edicion__anio', 'orden', 'nombre')


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
