from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404, redirect, render

from usuarios.permisos import administrador_requerido
from votaciones.models import Categoria, Encuesta, OpcionEncuesta, Voto
from .forms import CategoriaForm, EncuestaForm, OpcionEncuestaForm


@administrador_requerido
def panel_principal(request):
    encuestas_activas = list(
        Encuesta.objects.filter(
            estado='activa',
            categoria__activa=True,
        )
        .select_related('categoria')
        .annotate(
            total_votos=Count('votos', distinct=True),
            total_opciones=Count('opciones', distinct=True),
        )
        .order_by('categoria__orden', 'orden', 'nombre')
    )
    total_votos_activos = sum(encuesta.total_votos for encuesta in encuestas_activas)
    for encuesta in encuestas_activas:
        encuesta.porcentaje_votos = (
            round(encuesta.total_votos * 100 / total_votos_activos)
            if total_votos_activos
            else 0
        )

    categorias_activas = list(
        Categoria.objects.filter(activa=True).order_by('orden', 'nombre').values_list('nombre', flat=True)
    )
    votos_recientes = list(
        Voto.objects.select_related(
            'opcion',
            'encuesta',
            'encuesta__categoria',
        ).order_by('-fecha_creacion')[:6]
    )
    encuestas_con_votos = Encuesta.objects.filter(votos__isnull=False).distinct().count()
    total_votos = Voto.objects.count()
    usuario_model = get_user_model()

    return render(
        request,
        'administracion/panel_principal.html',
        {
            'seccion_admin': 'panel',
            'total_votos': total_votos,
            'total_encuestas_activas': len(encuestas_activas),
            'total_usuarios': usuario_model.objects.count(),
            'encuestas_con_votos': encuestas_con_votos,
            'encuestas_activas': encuestas_activas,
            'votos_recientes': votos_recientes,
            'total_votos_recientes': len(votos_recientes),
            'total_categorias_activas': len(categorias_activas),
            'categorias_activas': categorias_activas,
        },
    )


def _render_panel_votaciones(request, seccion_admin):
    estado_encuesta = 'activa' if seccion_admin == 'votaciones' else 'cerrada'
    # order_by explícito: con annotate (GROUP BY) Django no aplica el ordering del modelo.
    opciones_con_votos = OpcionEncuesta.objects.annotate(
        votos_recibidos=Count('votos'),
    ).order_by('orden', 'nombre')
    encuestas = list(
        Encuesta.objects.filter(estado=estado_encuesta).select_related('categoria')
        .prefetch_related(Prefetch('opciones', queryset=opciones_con_votos))
        .order_by('categoria__orden', 'orden', 'nombre')
        .annotate(votos_totales=Count('votos', distinct=True))
    )
    for encuesta in encuestas:
        for opcion in encuesta.opciones.all():
            opcion.porcentaje = (
                round(opcion.votos_recibidos * 100 / encuesta.votos_totales)
                if encuesta.votos_totales
                else 0
            )

    return render(
        request,
        'administracion/votaciones.html',
        {
            'seccion_admin': seccion_admin,
            'encuestas': encuestas,
            'total_votos': sum(encuesta.votos_totales for encuesta in encuestas),
            'total_encuestas': len(encuestas),
            'total_opciones': sum(encuesta.opciones.count() for encuesta in encuestas),
            'estado_encuesta': estado_encuesta,
        },
    )


@administrador_requerido
def panel_votaciones(request):
    return _render_panel_votaciones(request, 'votaciones')


@administrador_requerido
def panel_resultados(request):
    return _render_panel_votaciones(request, 'resultados')


@administrador_requerido
def categorias(request):
    category_form = CategoriaForm()
    form_category_id = None
    open_modal = None
    encuesta_form = EncuestaForm(prefix='encuesta')
    encuesta_category_id = None
    encuesta_id = None
    open_survey_modal = False
    opcion_form = OpcionEncuestaForm(
        encuesta=Encuesta.objects.first(),
        prefix='opcion',
    )
    opcion_encuesta_id = None
    opcion_id = None
    open_option_modal = False

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_opcion':
            survey_id = request.POST.get('opcion_encuesta_id', '')
            option_id = request.POST.get('opcion_id', '')
            if not survey_id.isdecimal() or (option_id and not option_id.isdecimal()):
                messages.error(request, 'No se pudo identificar la encuesta o la opción.')
                return redirect('categorias')

            encuesta = get_object_or_404(Encuesta, pk=survey_id)
            instance = get_object_or_404(
                OpcionEncuesta,
                pk=option_id,
                encuesta=encuesta,
            ) if option_id else None
            form = OpcionEncuestaForm(
                request.POST,
                instance=instance,
                encuesta=encuesta,
                prefix='opcion',
            )
            form.instance.encuesta = encuesta
            if form.is_valid():
                opcion = form.save(commit=False)
                opcion.encuesta = encuesta
                if not opcion.pk:
                    opcion.orden = encuesta.opciones.count() + 1
                opcion.save()
                messages.success(
                    request,
                    f'La opción «{opcion.nombre}» se '
                    f'{"actualizó" if instance else "registró"} en «{encuesta.nombre}».',
                )
                return redirect('categorias')

            messages.error(request, 'Revisa los campos de la opción antes de guardar.')
            opcion_form = form
            opcion_encuesta_id = encuesta.pk
            opcion_id = instance.pk if instance else None
            open_option_modal = True
        elif action == 'save_encuesta':
            category_id = request.POST.get('encuesta_categoria_id', '')
            survey_id = request.POST.get('encuesta_id', '')
            if not category_id.isdecimal() or (survey_id and not survey_id.isdecimal()):
                messages.error(request, 'No se pudo identificar la categoría o encuesta.')
                return redirect('categorias')

            categoria = get_object_or_404(Categoria, pk=category_id)
            instance = get_object_or_404(
                Encuesta,
                pk=survey_id,
                categoria=categoria,
            ) if survey_id else None
            form = EncuestaForm(request.POST, instance=instance, prefix='encuesta')
            form.instance.categoria = categoria

            if form.is_valid():
                encuesta = form.save(commit=False)
                encuesta.categoria = categoria
                encuesta.save()
                messages.success(
                    request,
                    f'La encuesta «{encuesta.nombre}» se '
                    f'{"actualizó" if instance else "creó"} en {categoria.nombre}.',
                )
                return redirect('categorias')

            messages.error(request, 'Revisa los campos de la encuesta antes de guardar.')
            encuesta_form = form
            encuesta_category_id = categoria.pk
            encuesta_id = instance.pk if instance else None
            open_survey_modal = True
        else:
            categoria_id = request.POST.get('categoria_id', '')
            if categoria_id and not categoria_id.isdecimal():
                messages.error(request, 'No se pudo identificar la categoría que intentas editar.')
                return redirect('categorias')
            instance = get_object_or_404(Categoria, pk=categoria_id) if categoria_id else None
            form = CategoriaForm(request.POST, instance=instance)

            if form.is_valid():
                categoria = form.save()
                messages.success(
                    request,
                    f'La categoría «{categoria.nombre}» se '
                    f'{"actualizó" if instance else "creó"} correctamente.',
                )
                return redirect('categorias')

            messages.error(request, 'Revisa los campos señalados antes de guardar.')
            category_form = form
            if instance:
                form_category_id = instance.pk
                open_modal = 'edit'
            else:
                open_modal = 'new'

    categorias = Categoria.objects.prefetch_related(
        Prefetch(
            'encuestas',
            queryset=Encuesta.objects.prefetch_related('opciones').order_by('orden', 'nombre'),
        ),
    )
    if opcion_encuesta_id and opcion_form.instance.encuesta_id:
        opcion_encuesta_nombre = opcion_form.instance.encuesta.nombre
    else:
        opcion_encuesta_nombre = ''
    context = {
        'seccion_admin': 'categorias',
        'categorias': categorias,
        'total_categorias': categorias.count(),
        'categorias_activas': categorias.filter(activa=True).count(),
        'categorias_inactivas': categorias.filter(activa=False).count(),
        'category_form': category_form,
        'form_category_id': form_category_id,
        'open_modal': open_modal,
        'encuesta_form': encuesta_form,
        'encuesta_category_id': encuesta_category_id,
        'encuesta_id': encuesta_id,
        'open_survey_modal': open_survey_modal,
        'opcion_form': opcion_form,
        'opcion_encuesta_id': opcion_encuesta_id,
        'opcion_encuesta_nombre': opcion_encuesta_nombre,
        'opcion_id': opcion_id,
        'open_option_modal': open_option_modal,
    }
    return render(request, 'administracion/categorias.html', context)
