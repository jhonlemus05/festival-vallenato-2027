from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from usuarios.views import obtener_perfil, registrar_evento_bitacora

from .forms import VotoForm
from .models import Edicion, Categoria, Encuesta, Voto


def voto_en_categoria(usuario, categoria):
    """El voto del usuario en esa categoría y edición, si ya lo emitió (regla central de la Entrega 3)."""
    return Voto.objects.filter(
        usuario=usuario,
        categoria=categoria,
        edicion_id=categoria.edicion_id,
    ).select_related('encuesta').first()


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
    categorias_votadas = set()
    if request.user.is_authenticated:
        categorias_votadas = set(
            Voto.objects.filter(usuario=request.user, edicion=edicion).values_list('categoria_id', flat=True)
        )
    return render(
        request,
        'votaciones/categorias.html',
        {
            'seccion_activa': 'categorias',
            'edicion': edicion,
            'categorias': categorias_visibles,
            'categorias_votadas': categorias_votadas,
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
            'voto_usuario': voto_en_categoria(request.user, categoria) if request.user.is_authenticated else None,
        },
    )


def rechazar_voto_duplicado(request, encuesta, voto_previo):
    """Un voto por usuario, categoría y edición: el segundo se rechaza aunque sea en otra encuesta (subevento)."""
    categoria = encuesta.categoria
    # Enviar otro voto se audita (RNF-03, RNF-04); solo abrir la encuesta no.
    if request.method == 'POST':
        registrar_evento_bitacora(
            request,
            obtener_perfil(request.user),
            'Intento de voto duplicado',
            f'Encuesta «{encuesta.nombre}» · categoría {categoria.nombre} · '
            f'ya votó con el comprobante {voto_previo.codigo_comprobante}',
        )
    messages.error(
        request,
        f'Ya votaste en la categoría {categoria.nombre} (en «{voto_previo.encuesta.nombre}»). '
        'Solo se permite un voto por categoría en cada edición; puedes votar en las demás categorías.',
    )
    return redirect('categoria_encuestas', categoria_id=categoria.pk)


@login_required
def votar_encuesta(request, encuesta_id):
    encuesta = get_object_or_404(
        Encuesta.objects.select_related('categoria__edicion').prefetch_related('opciones'),
        pk=encuesta_id,
        categoria__activa=True,
    )
    categoria = encuesta.categoria
    voto_previo = voto_en_categoria(request.user, categoria)
    if voto_previo:
        # Volver a abrir la encuesta en la que ya votó es normal: lleva a su comprobante.
        if request.method != 'POST' and voto_previo.encuesta_id == encuesta.pk:
            return redirect('voto_exitoso', voto_id=voto_previo.pk)
        return rechazar_voto_duplicado(request, encuesta, voto_previo)

    # Una edición en preparación o finalizada no recibe votos, aunque una encuesta siga marcada como activa.
    if categoria.edicion.estado != 'activa':
        messages.error(request, f'La edición {categoria.edicion.anio} no está habilitada para votar.')
        return redirect('categoria_encuestas', categoria_id=encuesta.categoria_id)

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
        form = VotoForm(request.POST, encuesta=encuesta)
        if not form.is_valid():
            # Una opción enviada que no es de esta encuesta no sale del formulario: es una solicitud alterada.
            if request.POST.get('opcion'):
                registrar_evento_bitacora(
                    request,
                    obtener_perfil(request.user),
                    'Intento de voto con opción inválida',
                    f'Encuesta «{encuesta.nombre}» · opción enviada {request.POST["opcion"][:20]}',
                )
            messages.error(request, form.errors['opcion'][0])
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
                    opcion=form.cleaned_data['opcion'],
                    usuario=request.user,
                )
        except IntegrityError:
            # Dos solicitudes simultáneas pueden pasar juntas la consulta de arriba: la restricción de
            # unicidad de MySQL deja entrar solo a la primera y aquí se rechaza a la otra.
            voto_previo = voto_en_categoria(request.user, categoria)
            if voto_previo is None:
                raise
            return rechazar_voto_duplicado(request, encuesta, voto_previo)

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


@require_GET
def api_categorias(request):
    """
    GET /api/categorias/: categorías visibles de la edición vigente con sus votaciones y opciones, en JSON.

    Es pública como el catálogo. No expone votos ni conteos: los resultados parciales siguen sin
    publicarse (RN-06).
    """
    edicion = Edicion.vigente()
    categorias_visibles = Categoria.objects.filter(activa=True, edicion=edicion).prefetch_related('encuestas__opciones')
    datos = {
        'edicion': edicion and {
            'id': edicion.pk,
            'nombre': edicion.nombre,
            'anio': edicion.anio,
            'estado': edicion.estado,
            'fecha_inicio': edicion.fecha_inicio,
            'fecha_fin': edicion.fecha_fin,
        },
        'total_categorias': len(categorias_visibles),
        'categorias': [
            {
                'id': categoria.pk,
                'nombre': categoria.nombre,
                'descripcion': categoria.descripcion,
                'votaciones': [
                    {
                        'id': encuesta.pk,
                        'nombre': encuesta.nombre,
                        'estado': encuesta.estado,
                        'fecha_apertura': encuesta.fecha_apertura,
                        'fecha_cierre': encuesta.fecha_cierre,
                        'opciones': [
                            {'id': opcion.pk, 'nombre': opcion.nombre, 'descripcion': opcion.descripcion}
                            for opcion in encuesta.opciones.all()
                        ],
                    }
                    for encuesta in categoria.encuestas.all()
                ],
            }
            for categoria in categorias_visibles
        ],
    }
    # ensure_ascii=False e indent: las tildes y la estructura se leen bien en el navegador.
    return JsonResponse(datos, json_dumps_params={'ensure_ascii': False, 'indent': 2})
