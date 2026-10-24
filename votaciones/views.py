from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from usuarios.views import obtener_perfil, registrar_evento_bitacora

from .models import Edicion, Categoria, Encuesta, OpcionEncuesta, Voto


def index(request):
    # La edición vigente alimenta el contador regresivo y las fechas de la portada.
    return render(request, 'votaciones/index.html', {'seccion_activa': 'inicio', 'edicion': Edicion.vigente()})


def ediciones(request):
    # order_by explícito: con annotate (GROUP BY) Django no aplica el ordering del modelo.
    lista = Edicion.objects.annotate(
        total_categorias=Count('categorias', filter=Q(categorias__activa=True)),
    ).order_by('-anio')
    return render(
        request,
        'votaciones/ediciones.html',
        {
            'seccion_activa': 'categorias',
            'ediciones': lista,
            'vigente': Edicion.vigente(),
        },
    )


def categorias(request, anio=None):
    # Sin año se muestra la edición vigente; /ediciones/<año>/ permite consultar las demás.
    edicion = Edicion.vigente() if anio is None else get_object_or_404(Edicion, anio=anio)
    categorias_visibles = Categoria.objects.filter(activa=True, edicion=edicion).annotate(
        encuestas_activas=Count('encuestas', filter=Q(encuestas__estado='activa')),
    ).order_by('orden', 'nombre')
    return render(
        request,
        'votaciones/categorias.html',
        {
            'seccion_activa': 'categorias',
            'edicion': edicion,
            'categorias': categorias_visibles,
        },
    )


def categoria_encuestas(request, categoria_id):
    categoria = get_object_or_404(
        Categoria.objects.filter(activa=True).select_related('edicion'),
        pk=categoria_id,
    )
    encuestas = Encuesta.objects.filter(categoria=categoria).order_by('orden', 'nombre').annotate(
        total_opciones=Count('opciones'),
    )
    return render(
        request,
        'votaciones/encuestas_categoria.html',
        {
            'seccion_activa': 'categorias',
            'categoria': categoria,
            'encuestas': encuestas,
            'encuestas_activas': encuestas.filter(estado='activa').count(),
        },
    )


@login_required
def votar_encuesta(request, encuesta_id):
    encuesta = get_object_or_404(
        Encuesta.objects.select_related('categoria').prefetch_related('opciones'),
        pk=encuesta_id,
        categoria__activa=True,
    )
    voto_existente = Voto.objects.filter(
        encuesta=encuesta,
        usuario=request.user,
    ).first()
    if voto_existente:
        # Volver a abrir la encuesta es normal; intentar enviar otro voto se audita (RNF-03, RNF-04).
        if request.method == 'POST':
            registrar_evento_bitacora(
                request,
                obtener_perfil(request.user),
                'Intento de voto duplicado',
                f'Encuesta «{encuesta.nombre}» · ya votó con el comprobante {voto_existente.codigo_comprobante}',
            )
        return redirect('voto_exitoso', voto_id=voto_existente.pk)

    # CU-04, flujo 6a: fuera de la ventana de votación se rechaza el voto y se explica por qué.
    if encuesta.estado != 'activa':
        if encuesta.estado == 'cerrada':
            messages.error(request, f'La votación «{encuesta.nombre}» ya está cerrada.')
        elif encuesta.fecha_apertura:
            apertura = timezone.localtime(encuesta.fecha_apertura).strftime('%d/%m/%Y a las %H:%M')
            messages.info(request, f'La votación «{encuesta.nombre}» abre el {apertura}.')
        else:
            messages.info(request, f'La votación «{encuesta.nombre}» todavía no está abierta.')
        return redirect('categoria_encuestas', categoria_id=encuesta.categoria_id)

    opciones = encuesta.opciones.all()
    if not opciones.exists():
        messages.info(request, 'Esta encuesta aún no tiene opciones disponibles.')
        return redirect('categoria_encuestas', categoria_id=encuesta.categoria_id)

    if request.method == 'POST':
        opcion_id = request.POST.get('opcion')
        opcion = get_object_or_404(opciones, pk=opcion_id) if opcion_id and opcion_id.isdecimal() else None
        if opcion is None:
            messages.error(request, 'Selecciona una opción válida para registrar tu voto.')
            return render(
                request,
                'votaciones/votacion.html',
                {
                    'seccion_activa': 'categorias',
                    'encuesta': encuesta,
                    'opciones': opciones,
                    'opcion_seleccionada': None,
                },
                status=400,
            )

        try:
            with transaction.atomic():
                voto = Voto.objects.create(
                    encuesta=encuesta,
                    opcion=opcion,
                    usuario=request.user,
                )
        except IntegrityError:
            voto = Voto.objects.filter(
                encuesta=encuesta,
                usuario=request.user,
            ).first()
            if voto is None:
                raise
            return redirect('voto_exitoso', voto_id=voto.pk)

        # Se audita el voto con su comprobante pero SIN la opción elegida: ni el administrador ni el
        # auditor deben ver el sentido del voto individual (RF-10).
        registrar_evento_bitacora(
            request,
            obtener_perfil(request.user),
            'Voto registrado',
            f'Encuesta «{encuesta.nombre}» · comprobante {voto.codigo_comprobante}',
        )
        return redirect('voto_exitoso', voto_id=voto.pk)

    return render(
        request,
        'votaciones/votacion.html',
        {
            'seccion_activa': 'categorias',
            'encuesta': encuesta,
            'opciones': opciones,
            # Sin preselección: el votante debe elegir a propósito (el botón Votar arranca deshabilitado).
            'opcion_seleccionada': None,
        },
    )


@login_required
def voto_exitoso(request, voto_id):
    voto = get_object_or_404(
        Voto.objects.select_related('encuesta', 'encuesta__categoria', 'opcion'),
        pk=voto_id,
        usuario=request.user,
    )
    return render(
        request,
        'votaciones/exito.html',
        {
            'seccion_activa': 'inicio',
            'voto': voto,
        },
    )
