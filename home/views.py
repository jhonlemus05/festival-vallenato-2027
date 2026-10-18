from django.shortcuts import render


def home(request):
    return render(request, 'home/inicio.html', {'seccion_activa': 'inicio'})
