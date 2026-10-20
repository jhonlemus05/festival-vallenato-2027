from django.urls import path
from . import views

urlpatterns = [
    path('', views.panel_principal, name='panel_principal'),
    path('categorias/', views.categorias, name='categorias'),
]
