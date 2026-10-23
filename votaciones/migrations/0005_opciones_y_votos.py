from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def cargar_opciones_artista(apps, schema_editor):
    Encuesta = apps.get_model('votaciones', 'Encuesta')
    OpcionEncuesta = apps.get_model('votaciones', 'OpcionEncuesta')
    encuesta = Encuesta.objects.filter(
        categoria__nombre='Música',
        nombre='Artista favorito del público',
    ).first()
    if encuesta is None:
        return

    opciones = [
        ('Mateo Díaz', 'Mi tierra canta', 'images/contestant_mateo_diaz_1791516984186.jpg'),
        ('Lucía Pineda', 'Raíces del alma', 'images/contestant_lucia_pineda_1791516993941.jpg'),
        ('Samuel Rojas', 'Aires de mi pueblo', 'images/contestant_samuel_rojas_1791517002103.jpg'),
        ('Valentina López', 'Corazón del Valle', 'images/contestant_valentina_lopez_1791517011267.jpg'),
    ]
    for orden, (nombre, descripcion, imagen) in enumerate(opciones, start=1):
        OpcionEncuesta.objects.get_or_create(
            encuesta=encuesta,
            nombre=nombre,
            defaults={
                'descripcion': descripcion,
                'imagen': imagen,
                'orden': orden,
            },
        )


def eliminar_opciones_artista(apps, schema_editor):
    OpcionEncuesta = apps.get_model('votaciones', 'OpcionEncuesta')
    OpcionEncuesta.objects.filter(
        encuesta__nombre='Artista favorito del público',
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('votaciones', '0004_ordenar_encuestas_musica'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OpcionEncuesta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=120, verbose_name='Nombre')),
                ('descripcion', models.CharField(blank=True, max_length=160, verbose_name='Descripción')),
                ('imagen', models.CharField(blank=True, max_length=255, verbose_name='Ruta de imagen')),
                ('orden', models.PositiveSmallIntegerField(default=0, verbose_name='Orden')),
                ('encuesta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='opciones', to='votaciones.encuesta', verbose_name='Encuesta')),
            ],
            options={
                'verbose_name': 'Opción de encuesta',
                'verbose_name_plural': 'Opciones de encuesta',
                'ordering': ['orden', 'nombre'],
            },
        ),
        migrations.CreateModel(
            name='Voto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True, verbose_name='Fecha del voto')),
                ('encuesta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votos', to='votaciones.encuesta', verbose_name='Encuesta')),
                ('opcion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votos', to='votaciones.opcionencuesta', verbose_name='Opción elegida')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votos_festival', to=settings.AUTH_USER_MODEL, verbose_name='Votante')),
            ],
            options={
                'verbose_name': 'Voto',
                'verbose_name_plural': 'Votos',
                'ordering': ['-fecha_creacion'],
            },
        ),
        migrations.AddConstraint(
            model_name='voto',
            constraint=models.UniqueConstraint(fields=('encuesta', 'usuario'), name='votacion_un_voto_por_usuario_encuesta'),
        ),
        migrations.RunPython(cargar_opciones_artista, eliminar_opciones_artista),
    ]
