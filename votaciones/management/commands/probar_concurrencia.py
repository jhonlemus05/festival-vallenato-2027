import http.client
import re
import secrets
import threading
from urllib.parse import urlencode, urlsplit

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.models import Count, Q
from django.test import Client
from django.urls import reverse

from usuarios.models import Usuario
from votaciones.models import Edicion, Categoria, Voto


DOMINIO_PRUEBA = 'demo.festivalvallenato.test'


class Command(BaseCommand):
    help = (
        'Prueba CP-09: envía solicitudes HTTP simultáneas al servidor en ejecución, con el mismo usuario y a '
        'encuestas de una misma categoría, y consulta en MySQL cuántos votos quedaron. Usa cuentas temporales '
        'que se borran al terminar, junto con sus votos.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--url', default='http://127.0.0.1:8000', help='Servidor en ejecución (runserver).')
        parser.add_argument('--rondas', type=int, default=5, help='Veces que se repite la prueba.')
        parser.add_argument('--solicitudes', type=int, default=2, help='Solicitudes simultáneas por ronda.')

    def handle(self, *args, **options):
        url = urlsplit(options['url'])
        self.host, self.puerto = url.hostname, url.port or 80
        categoria, encuestas = self.elegir_encuestas()
        self.stdout.write(f'Categoría: {categoria.nombre} · edición {categoria.edicion.anio}')
        self.stdout.write(f'Encuestas: {", ".join(encuesta.nombre for encuesta in encuestas)}')

        aprobadas = 0
        for ronda in range(1, options['rondas'] + 1):
            usuario = self.crear_usuario()
            try:
                self.stdout.write(f'\nRonda {ronda} · {usuario.username}')
                respuestas = self.enviar_simultaneas(usuario, encuestas, options['solicitudes'])
                aceptadas = 0
                for numero, (encuesta, estado, destino) in enumerate(respuestas, start=1):
                    aceptada = estado == 302 and destino.endswith('/exito/')
                    aceptadas += aceptada
                    resultado = 'aceptada' if aceptada else 'rechazada'
                    self.stdout.write(f'  Solicitud {numero} a «{encuesta.nombre}»: HTTP {estado} → {destino} ({resultado})')
                votos = Voto.objects.filter(usuario=usuario, categoria=categoria, edicion=categoria.edicion).count()
                self.stdout.write(f'  Votos en MySQL para este usuario, categoría y edición: {votos}')
                aprobadas += votos == 1 and aceptadas == 1
            finally:
                # El voto y el perfil se van en cascada; la bitácora conserva el evento sin el usuario.
                usuario.delete()

        resumen = f'\n{aprobadas} de {options["rondas"]} rondas dejaron exactamente un voto.'
        if aprobadas != options['rondas']:
            raise CommandError(resumen)
        self.stdout.write(self.style.SUCCESS(resumen))

    def elegir_encuestas(self):
        categoria = (
            Categoria.objects.filter(activa=True, edicion=Edicion.vigente())
            .annotate(activas=Count('encuestas', filter=Q(encuestas__estado='activa', encuestas__opciones__isnull=False), distinct=True))
            .filter(activas__gte=2)
            .select_related('edicion')
            .order_by('orden', 'nombre')
            .first()
        )
        if categoria is None:
            raise CommandError('Se necesita una categoría con dos encuestas activas con opciones: corre "python manage.py cargar_datos_prueba".')
        return categoria, [encuesta for encuesta in categoria.encuestas.filter(estado='activa') if encuesta.opciones.exists()]

    def crear_usuario(self):
        correo = f'concurrencia.{secrets.token_hex(4)}@{DOMINIO_PRUEBA}'
        usuario = User.objects.create_user(username=correo, email=correo, password=None)
        Usuario.objects.create(user=usuario, identificacion=secrets.token_hex(8), correo=correo, rol='votante')
        return usuario

    def enviar_simultaneas(self, usuario, encuestas, solicitudes):
        cliente = Client()
        cliente.force_login(usuario)
        sesion = cliente.cookies['sessionid'].value

        # Cada solicitud va a una encuesta distinta de la categoría, con su opción y su token CSRF.
        preparadas = []
        for numero in range(solicitudes):
            encuesta = encuestas[numero % len(encuestas)]
            ruta = reverse('votar_encuesta', args=[encuesta.pk])
            token, cookie = self.obtener_csrf(ruta, sesion)
            cuerpo = urlencode({'opcion': encuesta.opciones.first().pk, 'csrfmiddlewaretoken': token})
            cabeceras = {
                'Cookie': f'sessionid={sesion}; csrftoken={cookie}',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            preparadas.append((encuesta, ruta, cuerpo, cabeceras))

        # Cada hilo abre su conexión y espera en la barrera: así todas las solicitudes salen a la vez.
        barrera = threading.Barrier(solicitudes)
        respuestas = [None] * solicitudes

        def enviar(indice):
            encuesta, ruta, cuerpo, cabeceras = preparadas[indice]
            conexion = http.client.HTTPConnection(self.host, self.puerto, timeout=30)
            conexion.connect()
            barrera.wait()
            conexion.request('POST', ruta, cuerpo, cabeceras)
            respuesta = conexion.getresponse()
            respuestas[indice] = (encuesta, respuesta.status, respuesta.getheader('Location', ''))
            conexion.close()

        hilos = [threading.Thread(target=enviar, args=[indice]) for indice in range(solicitudes)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()
        connections.close_all()
        if None in respuestas:
            raise CommandError('Alguna solicitud no recibió respuesta: revisa el servidor.')
        return respuestas

    def obtener_csrf(self, ruta, sesion):
        """Pide el formulario de votación y devuelve el token del HTML y el de la cookie."""
        conexion = http.client.HTTPConnection(self.host, self.puerto, timeout=30)
        try:
            conexion.request('GET', ruta, headers={'Cookie': f'sessionid={sesion}'})
            respuesta = conexion.getresponse()
        except ConnectionError:
            raise CommandError(f'No hay un servidor en {self.host}:{self.puerto}: inicia "python manage.py runserver".')
        html = respuesta.read().decode()
        cookie = re.search(r'csrftoken=([^;]+)', respuesta.getheader('Set-Cookie', ''))
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
        conexion.close()
        if respuesta.status != 200 or not cookie or not token:
            raise CommandError(f'No se pudo abrir {ruta} (HTTP {respuesta.status}).')
        return token.group(1), cookie.group(1)
