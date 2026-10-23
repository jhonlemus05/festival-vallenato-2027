import datetime

from django.db import migrations, models
import django.db.models.deletion


def crear_edicion_2027(apps, schema_editor):
    # Fechas del 60° Festival según el boletín de prensa n.° 028 de la Fundación (citado en la Entrega 1).
    Edicion = apps.get_model('votaciones', 'Edicion')
    Categoria = apps.get_model('votaciones', 'Categoria')
    edicion, _ = Edicion.objects.get_or_create(
        anio=2027,
        defaults={
            'nombre': '60° Festival de la Leyenda Vallenata',
            'fecha_inicio': datetime.date(2027, 4, 28),
            'fecha_fin': datetime.date(2027, 5, 1),
            'estado': 'activa',
        },
    )
    # Las categorías que ya existían (Música, Piloneras, Comparsas) pasan a la edición 2027.
    Categoria.objects.filter(edicion__isnull=True).update(edicion=edicion)


def eliminar_edicion_2027(apps, schema_editor):
    Edicion = apps.get_model('votaciones', 'Edicion')
    Categoria = apps.get_model('votaciones', 'Categoria')
    Categoria.objects.update(edicion=None)
    Edicion.objects.filter(anio=2027).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('votaciones', '0005_opciones_y_votos'),
    ]

    operations = [
        migrations.CreateModel(
            name='Edicion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=150, verbose_name='Nombre')),
                ('anio', models.PositiveSmallIntegerField(unique=True, verbose_name='Año')),
                ('fecha_inicio', models.DateField(verbose_name='Fecha de inicio')),
                ('fecha_fin', models.DateField(verbose_name='Fecha de finalización')),
                ('estado', models.CharField(choices=[('preparacion', 'En preparación'), ('activa', 'Activa'), ('finalizada', 'Finalizada')], default='preparacion', max_length=20, verbose_name='Estado')),
            ],
            options={
                'verbose_name': 'Edición',
                'verbose_name_plural': 'Ediciones',
                'ordering': ['-anio'],
            },
        ),
        # Primero opcional, para poder asignar las categorías existentes; luego obligatoria (RN-01).
        migrations.AddField(
            model_name='categoria',
            name='edicion',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='categorias', to='votaciones.edicion', verbose_name='Edición'),
        ),
        migrations.RunPython(crear_edicion_2027, eliminar_edicion_2027),
        migrations.AlterField(
            model_name='categoria',
            name='edicion',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='categorias', to='votaciones.edicion', verbose_name='Edición'),
        ),
        migrations.AlterField(
            model_name='categoria',
            name='nombre',
            field=models.CharField(max_length=100, verbose_name='Nombre'),
        ),
        migrations.AddConstraint(
            model_name='categoria',
            constraint=models.UniqueConstraint(fields=('edicion', 'nombre'), name='votacion_categoria_unica_por_edicion'),
        ),
    ]
