from django.shortcuts import render


def panel_principal(request):
    return render(request, 'administracion/panel_principal.html', {'seccion_admin': 'panel'})


def categorias(request):
    return render(request, 'administracion/categorias.html', {'seccion_admin': 'categorias'})
