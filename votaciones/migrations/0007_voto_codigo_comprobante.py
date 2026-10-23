import secrets

from django.db import migrations, models


ALFABETO = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def asignar_codigos(apps, schema_editor):
    # Los votos que ya existían reciben su código (mismo formato que Voto.save()).
    Voto = apps.get_model('votaciones', 'Voto')
    usados = set()
    for voto in Voto.objects.filter(codigo_comprobante__isnull=True):
        while True:
            cuerpo = ''.join(secrets.choice(ALFABETO) for _ in range(8))
            codigo = f'FV-{cuerpo[:4]}-{cuerpo[4:]}'
            if codigo not in usados:
                break
        usados.add(codigo)
        voto.codigo_comprobante = codigo
        voto.save(update_fields=['codigo_comprobante'])


class Migration(migrations.Migration):

    dependencies = [
        ('votaciones', '0006_edicion'),
    ]

    operations = [
        # Primero opcional para poder llenar los votos existentes; luego obligatorio y único.
        migrations.AddField(
            model_name='voto',
            name='codigo_comprobante',
            field=models.CharField(editable=False, max_length=20, null=True, verbose_name='Código de comprobante'),
        ),
        migrations.RunPython(asignar_codigos, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='voto',
            name='codigo_comprobante',
            field=models.CharField(editable=False, max_length=20, unique=True, verbose_name='Código de comprobante'),
        ),
    ]
