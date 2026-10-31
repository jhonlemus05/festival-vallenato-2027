import hashlib
import re

from django.conf import settings
from django.db import migrations, models
from django.db.models.functions import Cast


def firmar(evento):
    """Misma fórmula de Bitacora.calcular_firma: las migraciones no pueden usar métodos del modelo."""
    payload = (
        f'{evento.usuario_firmado}|{evento.accion}|{evento.detalles}|{evento.ip_origen or ""}|'
        f'{evento.fecha_hora.isoformat()}|{settings.SECRET_KEY}'
    )
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def rellenar_usuario_firmado(apps, schema_editor):
    """
    Copia el autor con el que se firmó cada evento, para que las firmas existentes sigan valiendo.

    Los eventos de cuentas ya borradas se firmaron con un id que se perdió: quedan como anónimos y su
    firma sigue sin coincidir, salvo los de voto, que se vuelven a firmar en el paso siguiente.
    """
    Bitacora = apps.get_model('usuarios', 'Bitacora')
    Bitacora.objects.exclude(usuario=None).update(usuario_firmado=Cast('usuario_id', models.CharField()))
    Bitacora.objects.filter(usuario=None).update(usuario_firmado='anonimo')


def anonimizar_eventos_de_voto(apps, schema_editor):
    """
    RF-10 en los eventos ya guardados. Antes de esta migración quedaban el usuario junto a su comprobante,
    y la consulta de votos muestra ese comprobante con su opción, así que se podía saber qué eligió cada persona.
    """
    Bitacora = apps.get_model('usuarios', 'Bitacora')
    for evento in Bitacora.objects.filter(accion='Voto registrado'):
        evento.usuario_id = None
        evento.ip_origen = None
        evento.usuario_firmado = 'anonimo'
        evento.hash_sha256 = firmar(evento)
        evento.save(update_fields=['usuario', 'ip_origen', 'usuario_firmado', 'hash_sha256'])
    for evento in Bitacora.objects.filter(accion='Intento de voto duplicado'):
        evento.detalles = re.sub(r' · ya votó con el comprobante \S+$', '', evento.detalles)
        evento.hash_sha256 = firmar(evento)
        evento.save(update_fields=['detalles', 'hash_sha256'])


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0003_nombre_visible_perfil'),
    ]

    operations = [
        migrations.AddField(
            model_name='bitacora',
            name='usuario_firmado',
            field=models.CharField(blank=True, editable=False, max_length=20, verbose_name='Autor firmado'),
        ),
        migrations.RunPython(rellenar_usuario_firmado, migrations.RunPython.noop),
        # Lo anonimizado no se puede recuperar: al revertir solo se quita la columna.
        migrations.RunPython(anonimizar_eventos_de_voto, migrations.RunPython.noop),
    ]
