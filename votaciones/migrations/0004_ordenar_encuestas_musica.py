from django.db import migrations


def ordenar_encuestas_musica(apps, schema_editor):
    Encuesta = apps.get_model('votaciones', 'Encuesta')
    ordenes = {
        'Artista favorito del público': 1,
        'Canción favorita del público': 2,
        'Clásico vallenato favorito': 3,
        'Acordeonista': 4,
    }
    for nombre, orden in ordenes.items():
        Encuesta.objects.filter(
            categoria__nombre='Música',
            nombre=nombre,
        ).update(orden=orden)


class Migration(migrations.Migration):
    dependencies = [
        ('votaciones', '0003_mover_acordeonista_a_musica'),
    ]

    operations = [
        migrations.RunPython(ordenar_encuestas_musica, migrations.RunPython.noop),
    ]
