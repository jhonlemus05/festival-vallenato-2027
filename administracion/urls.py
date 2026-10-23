from django.urls import path
from . import views

urlpatterns = [
    path('', views.panel_principal, name='panel_principal'),
    path('categorias/', views.categorias, name='categorias'),
    path('votaciones/', views.panel_votaciones, name='admin_votaciones'),
    path('resultados/', views.panel_resultados, name='admin_resultados'),
]
