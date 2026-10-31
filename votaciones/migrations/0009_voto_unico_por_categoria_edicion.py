from django.db import migrations, models
import django.db.models.deletion


def rellenar_edicion_y_categoria(apps, schema_editor):
    """
    Copia en cada voto la categoría y la edición de su encuesta.

    Antes la regla era un voto por encuesta, así que un usuario podía tener varios en una misma
    categoría. Con la regla nueva vale el primero (como pasaría al votar) y los demás se eliminan:
    la restricción de unicidad no se podría crear con ellos.
    """
    Voto = apps.get_model('votaciones', 'Voto')
    ya_votaron = set()
    eliminados = 0
    for voto in Voto.objects.select_related('encuesta__categoria').order_by('fecha_creacion', 'pk'):
        categoria = voto.encuesta.categoria
        clave = (voto.usuario_id, categoria.pk)
        if clave in ya_votaron:
            voto.delete()
            eliminados += 1
            continue
        ya_votaron.add(clave)
        voto.categoria_id = categoria.pk
        voto.edicion_id = categoria.edicion_id
        voto.save(update_fields=['categoria', 'edicion'])

    if eliminados:
        print(f'\n  Un voto por categoría y edición: se eliminaron {eliminados} votos repetidos (se conservó el primero).')

    # El texto que ve el votante en las encuestas de las migraciones anteriores.
    Encuesta = apps.get_model('votaciones', 'Encuesta')
    for encuesta in Encuesta.objects.filter(detalle__contains='Un voto por persona'):
        encuesta.detalle = encuesta.detalle.replace('Un voto por persona', 'Un voto por categoría')
        encuesta.save(update_fields=['detalle'])


class Migration(migrations.Migration):

    dependencies = [
        ('votaciones', '0008_fechas_encuesta'),
    ]

    operations = [
        # Primero opcionales, para rellenar los votos existentes; luego obligatorios.
        migrations.AddField(
            model_name='voto',
            name='categoria',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='votos', to='votaciones.categoria', verbose_name='Categoría'),
        ),
        migrations.AddField(
            model_name='voto',
            name='edicion',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='votos', to='votaciones.edicion', verbose_name='Edición'),
        ),
        # Los votos eliminados no se pueden recuperar: al revertir solo se quitan las columnas.
        migrations.RunPython(rellenar_edicion_y_categoria, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='voto',
            name='categoria',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='votos', to='votaciones.categoria', verbose_name='Categoría'),
        ),
        migrations.AlterField(
            model_name='voto',
            name='edicion',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='votos', to='votaciones.edicion', verbose_name='Edición'),
        ),
        migrations.RemoveConstraint(
            model_name='voto',
            name='votacion_un_voto_por_usuario_encuesta',
        ),
        migrations.AddConstraint(
            model_name='voto',
            constraint=models.UniqueConstraint(fields=('usuario', 'categoria', 'edicion'), name='votacion_un_voto_por_usuario_categoria_edicion'),
        ),
    ]
