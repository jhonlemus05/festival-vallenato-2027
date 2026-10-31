from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('ediciones/', views.ediciones, name='ediciones'),
    path('ediciones/<int:anio>/', views.categorias, name='edicion_categorias'),
    path('categorias/', views.categorias, name='categorias_publicas'),
    path('categorias/<int:categoria_id>/', views.categoria_encuestas, name='categoria_encuestas'),
    path('encuestas/<int:encuesta_id>/votar/', views.votar_encuesta, name='votar_encuesta'),
    path('votos/<int:voto_id>/exito/', views.voto_exitoso, name='voto_exitoso'),
    path('api/categorias/', views.api_categorias, name='api_categorias'),
]
