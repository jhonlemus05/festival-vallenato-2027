from django.db import migrations, models


def crear_categorias_iniciales(apps, schema_editor):
    Categoria = apps.get_model('votaciones', 'Categoria')
    categorias = [
        {
            'nombre': 'Música',
            'descripcion': 'Acordeones, voces y canciones que nos unen.',
            'icono': 'music',
            'orden': 1,
        },
        {
            'nombre': 'Piloneras',
            'descripcion': 'El baile que celebra nuestras raíces.',
            'icono': 'flower',
            'orden': 2,
        },
        {
            'nombre': 'Comparsas',
            'descripcion': 'Creatividad y alegría en las calles.',
            'icono': 'mask',
            'orden': 3,
        },
    ]
    for categoria in categorias:
        Categoria.objects.get_or_create(nombre=categoria['nombre'], defaults=categoria)


def eliminar_categorias_iniciales(apps, schema_editor):
    Categoria = apps.get_model('votaciones', 'Categoria')
    Categoria.objects.filter(nombre__in=['Música', 'Piloneras', 'Comparsas']).delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True, verbose_name='Nombre')),
                ('descripcion', models.CharField(max_length=220, verbose_name='Descripción')),
                ('icono', models.CharField(
                    choices=[
                        ('music', 'Nota musical'),
                        ('flower', 'Danza y flores'),
                        ('mask', 'Máscaras'),
                        ('trophy', 'Trofeo'),
                    ],
                    default='music',
                    max_length=20,
                    verbose_name='Icono',
                )),
                ('activa', models.BooleanField(default=True, verbose_name='Visible en la aplicación')),
                ('orden', models.PositiveSmallIntegerField(default=0, verbose_name='Orden')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True, verbose_name='Última actualización')),
            ],
            options={
                'verbose_name': 'Categoría',
                'verbose_name_plural': 'Categorías',
                'ordering': ['orden', 'nombre'],
            },
        ),
        migrations.RunPython(crear_categorias_iniciales, eliminar_categorias_iniciales),
    ]
