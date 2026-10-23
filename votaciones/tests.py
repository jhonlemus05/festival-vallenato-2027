from datetime import date
from io import StringIO

from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from usuarios.models import Bitacora

from .models import Edicion, Categoria, Encuesta, OpcionEncuesta, Voto


class CategoriasPublicasTests(TestCase):
    def test_catalogo_muestra_categorias_activas(self):
        response = self.client.get(reverse('categorias_publicas'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Música')
        self.assertContains(response, 'Piloneras')
        self.assertContains(response, 'Comparsas')
        musica = Categoria.objects.get(nombre='Música')
        self.assertContains(response, reverse('categoria_encuestas', args=[musica.pk]))

    def test_categoria_inactiva_no_se_muestra_en_el_catalogo_publico(self):
        Categoria.objects.filter(nombre='Piloneras').update(activa=False)

        response = self.client.get(reverse('categorias_publicas'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Música')
        self.assertNotContains(response, 'Piloneras')

    def test_inicio_carga_con_el_enlace_al_catalogo(self):
        response = self.client.get(reverse('index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('categorias_publicas'))

    def test_categoria_muestra_encuestas_asociadas_y_sus_estados(self):
        musica = Categoria.objects.get(nombre='Música')

        response = self.client.get(reverse('categoria_encuestas', args=[musica.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['encuestas'].count(), 4)
        self.assertContains(response, 'Acordeonista')
        self.assertContains(response, 'Artista favorito del público')
        self.assertContains(response, 'Canción favorita del público')
        self.assertContains(response, 'Clásico vallenato favorito')
        self.assertContains(response, 'Elegir mi favorito')
        self.assertContains(response, 'Opciones próximamente')
        self.assertEqual(
            list(response.context['encuestas'].values_list('nombre', flat=True)),
            [
                'Artista favorito del público',
                'Canción favorita del público',
                'Clásico vallenato favorito',
                'Acordeonista',
            ],
        )

    def test_detalle_no_muestra_categoria_oculta(self):
        musica = Categoria.objects.get(nombre='Música')
        musica.activa = False
        musica.save()

        response = self.client.get(reverse('categoria_encuestas', args=[musica.pk]))

        self.assertEqual(response.status_code, 404)

    def test_encuesta_activa_se_cuenta_en_tarjeta_de_categoria(self):
        musica = Categoria.objects.get(nombre='Música')
        response = self.client.get(reverse('categorias_publicas'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2 activas')
        self.assertTrue(Encuesta.objects.filter(categoria=musica, estado='activa').exists())


class VotacionPublicaTests(TestCase):
    def setUp(self):
        self.encuesta = Encuesta.objects.get(nombre='Artista favorito del público')
        self.opciones = list(self.encuesta.opciones.all())
        self.url = reverse('votar_encuesta', args=[self.encuesta.pk])
        self.usuario = User.objects.create_user(
            username='votante-prueba',
            password='TestPassword123!',
        )

    def test_votar_requiere_inicio_de_sesion(self):
        response = self.client.get(self.url)

        self.assertRedirects(response, f'{reverse("login")}?next={self.url}')
        self.assertEqual(Voto.objects.count(), 0)

    def test_ninguna_opcion_viene_preseleccionada(self):
        self.client.force_login(self.usuario)

        response = self.client.get(self.url)

        self.assertIsNone(response.context['opcion_seleccionada'])
        # Ningún radio de opción marcado ("checked" también aparece en el CSS y el JS de la página).
        html = response.content.decode()
        self.assertNotRegex(html, r'<input[^>]*name="opcion"[^>]*\bchecked\b[^>]*>')
        self.assertRegex(html, r'class="voting-submit"[^>]*\bdisabled\b')
        self.assertContains(response, 'Selecciona a quién quieres darle tu voto.')

    def test_pagina_muestra_opciones_y_guarda_voto_confirmado(self):
        self.client.force_login(self.usuario)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mateo Díaz')
        self.assertContains(response, 'Lucía Pineda')
        self.assertContains(response, 'Samuel Rojas')
        self.assertContains(response, 'Valentina López')
        self.assertContains(response, 'Confirmar voto')

        response = self.client.post(self.url, {'opcion': self.opciones[1].pk})

        voto = Voto.objects.get()
        self.assertRedirects(response, reverse('voto_exitoso', args=[voto.pk]))
        self.assertEqual(voto.usuario, self.usuario)
        self.assertEqual(voto.encuesta, self.encuesta)
        self.assertEqual(voto.opcion, self.opciones[1])
        self.assertContains(self.client.get(reverse('voto_exitoso', args=[voto.pk])), 'Lucía Pineda')

    def test_opcion_sin_imagen_no_genera_src_vacio_en_confirmacion(self):
        OpcionEncuesta.objects.create(
            encuesta=self.encuesta,
            nombre='Artista sin retrato',
            descripcion='Participante agregado por administración.',
            imagen='',
            orden=5,
        )
        self.client.force_login(self.usuario)

        response = self.client.get(self.url)

        self.assertContains(response, 'Artista sin retrato')
        self.assertContains(response, 'id="confirmOptionImage"')
        self.assertNotContains(response, 'id="confirmOptionImage" src=""')

    def test_un_usuario_no_puede_cambiar_ni_repetir_su_voto(self):
        self.client.force_login(self.usuario)
        self.client.post(self.url, {'opcion': self.opciones[0].pk})
        voto_original = Voto.objects.get()

        response = self.client.post(self.url, {'opcion': self.opciones[1].pk})

        self.assertRedirects(response, reverse('voto_exitoso', args=[voto_original.pk]))
        self.assertEqual(Voto.objects.count(), 1)
        voto_original.refresh_from_db()
        self.assertEqual(voto_original.opcion, self.opciones[0])

    def test_no_acepta_opcion_que_pertenece_a_otra_encuesta(self):
        otra_encuesta = Encuesta.objects.create(
            categoria=self.encuesta.categoria,
            nombre='Encuesta alternativa',
            descripcion='Otra encuesta para probar el alcance de las opciones.',
            estado='activa',
        )
        opcion_ajena = OpcionEncuesta.objects.create(
            encuesta=otra_encuesta,
            nombre='Opción ajena',
        )
        self.client.force_login(self.usuario)

        response = self.client.post(self.url, {'opcion': opcion_ajena.pk})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Voto.objects.count(), 0)

    def test_no_permite_votar_en_encuesta_cerrada(self):
        self.encuesta.estado = 'cerrada'
        self.encuesta.save(update_fields=['estado'])
        self.client.force_login(self.usuario)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Voto.objects.count(), 0)

    def test_pantalla_de_exito_solo_es_visible_para_quien_voto(self):
        voto = Voto.objects.create(
            encuesta=self.encuesta,
            opcion=self.opciones[0],
            usuario=self.usuario,
        )
        otro_usuario = User.objects.create_user(
            username='otro-votante',
            password='TestPassword123!',
        )
        self.client.force_login(otro_usuario)

        response = self.client.get(reverse('voto_exitoso', args=[voto.pk]))

        self.assertEqual(response.status_code, 404)


    def test_voto_tiene_comprobante_y_queda_en_bitacora_sin_la_opcion(self):
        self.client.force_login(self.usuario)

        self.client.post(self.url, {'opcion': self.opciones[1].pk})

        voto = Voto.objects.get()
        self.assertRegex(voto.codigo_comprobante, r'^FV-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$')
        evento = Bitacora.objects.get(accion='Voto registrado')
        self.assertIn(voto.codigo_comprobante, evento.detalles)
        # El sentido del voto no queda en la bitácora (RF-10).
        self.assertNotIn(self.opciones[1].nombre, evento.detalles)
        self.assertTrue(evento.firma_valida())
        self.assertContains(self.client.get(reverse('voto_exitoso', args=[voto.pk])), voto.codigo_comprobante)

    def test_intento_de_voto_duplicado_queda_en_bitacora(self):
        self.client.force_login(self.usuario)
        self.client.post(self.url, {'opcion': self.opciones[0].pk})

        self.client.post(self.url, {'opcion': self.opciones[1].pk})

        self.assertEqual(Voto.objects.count(), 1)
        self.assertTrue(Bitacora.objects.filter(accion='Intento de voto duplicado').exists())

class ResultadosAdminTests(TestCase):
    def setUp(self):
        # Estas vistas son del panel administrativo: solo entra una cuenta administradora.
        self.client.force_login(User.objects.create_user(
            username='admin-resultados',
            password='TestPassword123!',
            is_staff=True,
        ))

    def test_votaciones_muestra_solo_encuestas_activas(self):
        encuesta = Encuesta.objects.get(nombre='Artista favorito del público')
        opciones = list(encuesta.opciones.all())
        for index, opcion in enumerate(opciones[:2]):
            usuario = User.objects.create_user(
                username=f'votante-resultados-{index}',
                password='TestPassword123!',
            )
            Voto.objects.create(encuesta=encuesta, opcion=opcion, usuario=usuario)

        response = self.client.get(reverse('admin_votaciones'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Votos registrados')
        self.assertContains(response, '2 votos')
        self.assertContains(response, 'Mateo Díaz')
        self.assertContains(response, 'Lucía Pineda')
        self.assertContains(response, '50%')
        self.assertNotContains(response, 'Clásico vallenato favorito')
        self.assertNotContains(response, 'votante-resultados')

    def test_resultados_muestra_solo_encuestas_cerradas(self):
        response = self.client.get(reverse('admin_resultados'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Clásico vallenato favorito')
        self.assertNotContains(response, 'Artista favorito del público')
        self.assertContains(response, 'Encuestas finalizadas')

    def test_menu_de_resultados_lleva_a_la_vista_de_encuestas_cerradas(self):
        response = self.client.get(reverse('admin_resultados'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Resultados de votaciones finalizadas')


class EdicionesTests(TestCase):
    def crear_edicion(self, anio, estado='finalizada'):
        return Edicion.objects.create(
            nombre=f'Festival de la Leyenda Vallenata {anio}',
            anio=anio,
            fecha_inicio=date(anio, 4, 28),
            fecha_fin=date(anio, 5, 1),
            estado=estado,
        )

    def test_migracion_crea_la_edicion_2027_con_sus_categorias(self):
        edicion = Edicion.objects.get(anio=2027)

        self.assertEqual(edicion.estado, 'activa')
        self.assertEqual(Edicion.vigente(), edicion)
        self.assertEqual(
            set(edicion.categorias.values_list('nombre', flat=True)),
            {'Música', 'Piloneras', 'Comparsas'},
        )

    def test_fecha_de_fin_anterior_al_inicio_no_es_valida(self):
        edicion = Edicion(
            nombre='Edición con fechas al revés',
            anio=2030,
            fecha_inicio=date(2030, 5, 1),
            fecha_fin=date(2030, 4, 1),
        )

        with self.assertRaises(ValidationError):
            edicion.full_clean()

    def test_nombre_de_categoria_no_se_repite_dentro_de_una_edicion(self):
        anterior = self.crear_edicion(2026)
        Categoria.objects.create(edicion=anterior, nombre='Música', descripcion='Edición anterior.')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Categoria.objects.create(edicion=anterior, nombre='Música', descripcion='Repetida.')

    def test_listado_publico_de_ediciones(self):
        self.crear_edicion(2026)

        response = self.client.get(reverse('ediciones'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('edicion_categorias', args=[2027]))
        self.assertContains(response, reverse('edicion_categorias', args=[2026]))

    def test_categorias_muestra_solo_la_edicion_vigente(self):
        anterior = self.crear_edicion(2026)
        Categoria.objects.create(edicion=anterior, nombre='Danza 2026', descripcion='Solo de la edición anterior.')

        response = self.client.get(reverse('categorias_publicas'))

        self.assertEqual(response.context['edicion'].anio, 2027)
        self.assertContains(response, 'Música')
        self.assertNotContains(response, 'Danza 2026')

    def test_categorias_respetan_el_orden_configurado(self):
        # Con annotate Django no aplica el ordering del modelo: sin order_by explícito MySQL
        # devolvía las categorías en orden alfabético.
        response = self.client.get(reverse('categorias_publicas'))

        self.assertEqual(
            [categoria.nombre for categoria in response.context['categorias']],
            ['Música', 'Piloneras', 'Comparsas'],
        )

    def test_se_consultan_las_categorias_de_otra_edicion(self):
        anterior = self.crear_edicion(2026)
        Categoria.objects.create(edicion=anterior, nombre='Danza 2026', descripcion='Solo de la edición anterior.')

        response = self.client.get(reverse('edicion_categorias', args=[2026]))

        self.assertContains(response, 'Danza 2026')
        self.assertNotContains(response, 'Piloneras')
        self.assertEqual(self.client.get(reverse('edicion_categorias', args=[1999])).status_code, 404)

    def test_encuestas_de_otra_edicion_vuelven_a_su_edicion(self):
        anterior = self.crear_edicion(2026)
        musica_2026 = Categoria.objects.create(edicion=anterior, nombre='Música', descripcion='Edición anterior.')

        response = self.client.get(reverse('categoria_encuestas', args=[musica_2026.pk]))

        self.assertContains(response, reverse('edicion_categorias', args=[2026]))
        self.assertContains(response, 'Música · 2026')

    def test_contador_de_la_portada_usa_la_fecha_de_la_edicion_vigente(self):
        response = self.client.get(reverse('index'))

        self.assertContains(response, 'data-inicio="2027-04-28"')
        self.assertNotContains(response, 'Fechas oficiales por anunciar')

    def test_django_admin_registra_y_lista_ediciones(self):
        admin = User.objects.create_superuser('admin-ediciones', 'admin@festivalvallenato.com', 'ClaveAdmin2027!')
        self.client.force_login(admin)

        response = self.client.post(reverse('admin:votaciones_edicion_add'), {
            'nombre': 'Festival de la Leyenda Vallenata 2028',
            'anio': 2028,
            'fecha_inicio': '26/04/2028',
            'fecha_fin': '29/04/2028',
            'estado': 'preparacion',
            'categorias-TOTAL_FORMS': '0',
            'categorias-INITIAL_FORMS': '0',
            'categorias-MIN_NUM_FORMS': '0',
            'categorias-MAX_NUM_FORMS': '1000',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Edicion.objects.filter(anio=2028).exists())
        self.assertContains(self.client.get(reverse('admin:votaciones_edicion_changelist')), '2028')


class CargarDatosPruebaTests(TestCase):
    def cargar(self):
        call_command('cargar_datos_prueba', stdout=StringIO())

    def test_carga_ediciones_opciones_y_votos(self):
        self.cargar()

        self.assertEqual(Edicion.objects.count(), 2)
        self.assertTrue(Edicion.objects.filter(anio=2026, estado='finalizada').exists())
        self.assertEqual(Encuesta.objects.get(nombre='Canción favorita del público').opciones.count(), 3)
        # 12 votos en Artista favorito, 12 en Clásico vallenato y 12 en la edición 2026.
        self.assertEqual(Voto.objects.count(), 36)

    def test_se_puede_correr_varias_veces_sin_duplicar(self):
        self.cargar()
        conteos = (Edicion.objects.count(), OpcionEncuesta.objects.count(), Voto.objects.count(), User.objects.count())

        self.cargar()

        self.assertEqual(
            (Edicion.objects.count(), OpcionEncuesta.objects.count(), Voto.objects.count(), User.objects.count()),
            conteos,
        )

    def test_votantes_de_prueba_no_pueden_iniciar_sesion(self):
        self.cargar()

        votantes = User.objects.filter(username__endswith='@demo.festivalvallenato.test')
        self.assertEqual(votantes.count(), 12)
        self.assertFalse(any(votante.has_usable_password() for votante in votantes))
