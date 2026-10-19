from django.shortcuts import render


def panel_principal(request):
    return render(request, 'administracion/panel_principal.html', {'seccion_admin': 'panel'})
