from django.db import migrations


def mover_acordeonista_a_musica(apps, schema_editor):
    Categoria = apps.get_model('votaciones', 'Categoria')
    Encuesta = apps.get_model('votaciones', 'Encuesta')

    musica = Categoria.objects.filter(nombre='Música').first()
    acordeonista = Categoria.objects.filter(nombre='Acordeonista').first()
    if not musica or not acordeonista:
        return

    encuesta_acordeonista = Encuesta.objects.filter(
        categoria=musica,
        nombre='Acordeonista',
    ).first()
    if encuesta_acordeonista:
        if acordeonista.descripcion:
            encuesta_acordeonista.descripcion = acordeonista.descripcion
            encuesta_acordeonista.save(update_fields=['descripcion'])
    else:
        Encuesta.objects.create(
            categoria=musica,
            nombre=acordeonista.nombre,
            descripcion=acordeonista.descripcion or 'Encuesta de acordeonistas.',
            estado='proxima',
            orden=1,
        )

    Encuesta.objects.filter(categoria=acordeonista).update(categoria=musica)
    acordeonista.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('votaciones', '0002_encuesta'),
    ]

    operations = [
        migrations.RunPython(mover_acordeonista_a_musica, migrations.RunPython.noop),
    ]
