from datetime import date, datetime

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from usuarios.models import Usuario
from votaciones.models import Edicion, Categoria, Encuesta, OpcionEncuesta, Voto


# Todo lo que crea este comando es de PRUEBA (capturas y video de la entrega), no datos de la Fundación.
# 24 votantes: en Música de 2027 votan 12 en cada encuesta, porque nadie puede votar dos veces en una categoría.
VOTANTES_PRUEBA = 24
DOMINIO_PRUEBA = 'demo.festivalvallenato.test'


class Command(BaseCommand):
    help = (
        'Carga datos de prueba: una edición 2026 finalizada, opciones para las encuestas sin opciones '
        'y votos de votantes de prueba. Se puede correr varias veces sin duplicar nada.'
    )

    @transaction.atomic
    def handle(self, *args, **options):
        edicion_2027 = Edicion.objects.filter(anio=2027).first()
        if edicion_2027 is None:
            raise CommandError('Falta la edición 2027: corre primero "python manage.py migrate".')

        votantes = self.crear_votantes()

        # Edición 2027 (la de las migraciones): opciones y votos para que los paneles tengan datos.
        musica = self.buscar(Categoria, edicion=edicion_2027, nombre='Música')
        artista = self.buscar(Encuesta, categoria=musica, nombre='Artista favorito del público')
        self.registrar_votos(artista, list(artista.opciones.order_by('orden', 'nombre')), [5, 3, 2, 2], votantes[:12])

        cancion = self.buscar(Encuesta, categoria=musica, nombre='Canción favorita del público')
        self.crear_opciones(cancion, ['Canción de prueba A', 'Canción de prueba B', 'Canción de prueba C'])
        # El texto original de la migración dice "6 canciones"; con los datos de prueba son 3.
        if cancion.detalle.startswith('6 canciones'):
            cancion.detalle = '3 canciones de prueba · Un voto por categoría'
            cancion.save(update_fields=['detalle'])

        # RN-05: fechas de prueba para mostrar la ventana de votación (solo si la encuesta no tiene).
        cierre = timezone.make_aware(datetime(2027, 4, 27, 23, 59))
        for encuesta in (artista, cancion):
            if encuesta.fecha_cierre is None:
                encuesta.fecha_cierre = cierre
                encuesta.save(update_fields=['fecha_cierre'])
        acordeonista = self.buscar(Encuesta, categoria=musica, nombre='Acordeonista')
        if acordeonista.fecha_apertura is None:
            acordeonista.fecha_apertura = timezone.make_aware(datetime(2027, 4, 28, 8, 0))
            acordeonista.save(update_fields=['fecha_apertura'])

        clasico = self.buscar(Encuesta, categoria=musica, nombre='Clásico vallenato favorito')
        opciones_clasico = self.crear_opciones(clasico, ['Clásico de prueba A', 'Clásico de prueba B', 'Clásico de prueba C'])
        self.registrar_votos(clasico, opciones_clasico, [5, 4, 3], votantes[12:])

        # Otras categorías: una abierta para votar en una categoría distinta (CP-03) y una sin
        # votaciones abiertas para el intento de voto en una categoría no habilitada (CP-05).
        piloneras = self.buscar(Categoria, edicion=edicion_2027, nombre='Piloneras')
        grupo, _ = Encuesta.objects.get_or_create(
            categoria=piloneras,
            nombre='Grupo de piloneras favorito',
            defaults={
                'descripcion': 'Elige al grupo de piloneras que más te emociona.',
                'detalle': '3 grupos de prueba · Un voto por categoría',
                'estado': 'activa',
                'fecha_cierre': cierre,
                'orden': 1,
            },
        )
        self.crear_opciones(grupo, ['Grupo de prueba A', 'Grupo de prueba B', 'Grupo de prueba C'])
        comparsas = self.buscar(Categoria, edicion=edicion_2027, nombre='Comparsas')
        comparsa, _ = Encuesta.objects.get_or_create(
            categoria=comparsas,
            nombre='Comparsa favorita',
            defaults={
                'descripcion': 'Consulta de prueba ya finalizada.',
                'detalle': 'La consulta de esta edición ha finalizado.',
                'estado': 'cerrada',
                'orden': 1,
            },
        )
        self.crear_opciones(comparsa, ['Comparsa de prueba A', 'Comparsa de prueba B'])

        # Una segunda edición, ya finalizada, para mostrar que el sistema maneja varias ediciones.
        edicion_2026, _ = Edicion.objects.get_or_create(
            anio=2026,
            defaults={
                'nombre': 'Edición de prueba 2026',
                'fecha_inicio': date(2026, 4, 29),
                'fecha_fin': date(2026, 5, 2),
                'estado': 'finalizada',
            },
        )
        musica_2026, _ = Categoria.objects.get_or_create(
            edicion=edicion_2026,
            nombre='Música',
            defaults={'descripcion': 'Categoría de la edición de prueba 2026.', 'icono': 'music', 'orden': 1},
        )
        artista_2026, _ = Encuesta.objects.get_or_create(
            categoria=musica_2026,
            nombre='Artista favorito 2026',
            defaults={
                'descripcion': 'Encuesta cerrada de la edición de prueba 2026.',
                'detalle': '3 participantes · Datos de prueba',
                'estado': 'cerrada',
                'orden': 1,
            },
        )
        opciones_2026 = self.crear_opciones(artista_2026, ['Artista de prueba A', 'Artista de prueba B', 'Artista de prueba C'])
        # Los mismos votantes de 2027: la regla es por edición, así que Música se puede votar en cada una.
        self.registrar_votos(artista_2026, opciones_2026, [6, 4, 2], votantes[:12])

        self.stdout.write(self.style.SUCCESS(
            f'Datos de prueba listos: {Edicion.objects.count()} ediciones, '
            f'{OpcionEncuesta.objects.count()} opciones, {Voto.objects.count()} votos, '
            f'{VOTANTES_PRUEBA} votantes de prueba (sin contraseña: no pueden iniciar sesión).'
        ))

    def buscar(self, modelo, **filtros):
        objeto = modelo.objects.filter(**filtros).first()
        if objeto is None:
            raise CommandError(f'No se encontró {modelo._meta.verbose_name} con {filtros}: ¿se cambió desde el admin?')
        return objeto

    def crear_votantes(self):
        votantes = []
        for n in range(1, VOTANTES_PRUEBA + 1):
            correo = f'votante.prueba{n:02d}@{DOMINIO_PRUEBA}'
            user, creado = User.objects.get_or_create(username=correo, defaults={'email': correo})
            if creado:
                # Sin contraseña utilizable: estas cuentas existen solo para tener votos que mostrar.
                user.set_unusable_password()
                user.save(update_fields=['password'])
            Usuario.objects.get_or_create(
                user=user,
                defaults={'identificacion': f'9000000{n:03d}', 'correo': correo, 'rol': 'votante'},
            )
            votantes.append(user)
        return votantes

    def crear_opciones(self, encuesta, nombres):
        opciones = []
        for orden, nombre in enumerate(nombres, start=1):
            opcion, _ = OpcionEncuesta.objects.get_or_create(
                encuesta=encuesta,
                nombre=nombre,
                defaults={'descripcion': 'Opción de prueba', 'orden': orden},
            )
            opciones.append(opcion)
        return opciones

    def registrar_votos(self, encuesta, opciones, reparto, votantes):
        # reparto[i] = cuántos votantes eligen opciones[i]. Cada votante vota una sola vez por categoría,
        # así que al correr el comando otra vez get_or_create encuentra el voto y no lo repite.
        siguiente = iter(votantes)
        for opcion, cantidad in zip(opciones, reparto):
            for _ in range(cantidad):
                Voto.objects.get_or_create(encuesta=encuesta, usuario=next(siguiente), defaults={'opcion': opcion})
