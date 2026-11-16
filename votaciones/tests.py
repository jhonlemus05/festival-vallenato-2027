from datetime import date, timedelta
from io import StringIO
import json
import threading
from unittest import mock

from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connections, transaction
from django.test import Client, LiveServerTestCase, TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

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

        self.assertRedirects(response, reverse('categoria_encuestas', args=[self.encuesta.categoria_id]))
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

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'no pertenece a esta votación', status_code=400)
        self.assertEqual(Voto.objects.count(), 0)

    def test_no_permite_votar_en_encuesta_cerrada(self):
        self.encuesta.estado = 'cerrada'
        self.encuesta.save(update_fields=['estado'])
        self.client.force_login(self.usuario)

        # CU-04, flujo 6a: se rechaza e informa que está cerrada (antes era un 404 sin explicación).
        response = self.client.post(self.url, {'opcion': self.opciones[0].pk}, follow=True)

        self.assertRedirects(response, reverse('categoria_encuestas', args=[self.encuesta.categoria_id]))
        self.assertContains(response, 'ya está cerrada')
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


    def test_voto_tiene_comprobante_y_queda_en_bitacora_sin_opcion_ni_votante(self):
        self.client.force_login(self.usuario)

        self.client.post(self.url, {'opcion': self.opciones[1].pk})

        voto = Voto.objects.get()
        self.assertRegex(voto.codigo_comprobante, r'^FV-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$')
        evento = Bitacora.objects.get(accion='Voto registrado')
        self.assertIn(voto.codigo_comprobante, evento.detalles)
        # Ni el sentido del voto ni quién lo emitió quedan en este evento (RF-10): el comprobante se
        # puede buscar en la consulta de votos, así que junto al usuario revelaría su opción.
        self.assertNotIn(self.opciones[1].nombre, evento.detalles)
        self.assertIsNone(evento.usuario)
        self.assertIsNone(evento.ip_origen)
        self.assertTrue(evento.firma_valida())
        self.assertContains(self.client.get(reverse('voto_exitoso', args=[voto.pk])), voto.codigo_comprobante)

    def test_intento_de_voto_duplicado_queda_en_bitacora(self):
        self.client.force_login(self.usuario)
        self.client.post(self.url, {'opcion': self.opciones[0].pk})

        self.client.post(self.url, {'opcion': self.opciones[1].pk})

        voto = Voto.objects.get()
        evento = Bitacora.objects.get(accion='Intento de voto duplicado')
        self.assertEqual(evento.usuario.user, self.usuario)
        # Este evento sí identifica al usuario, por eso no puede llevar su comprobante (RF-10).
        self.assertNotIn(voto.codigo_comprobante, evento.detalles)


class SecretoDelVotoTests(TestCase):
    """RF-10: Django Admin no permite cruzar a un votante con su voto filtrando por URL."""

    def setUp(self):
        encuesta = Encuesta.objects.get(nombre='Artista favorito del público')
        self.votante = User.objects.create_user(username='secreto@correo.com', password='TestPassword123!')
        self.voto = Voto.objects.create(encuesta=encuesta, opcion=encuesta.opciones.first(), usuario=self.votante)
        self.client.force_login(User.objects.create_superuser(username='admin-secreto', password='TestPassword123!'))

    def test_no_se_filtran_votos_por_usuario(self):
        for filtro in ('usuario', 'usuario__exact', 'usuario_id__exact', 'usuario__id__exact'):
            with self.subTest(filtro=filtro):
                response = self.client.get(reverse('admin:votaciones_voto_changelist'), {filtro: self.votante.pk})
                self.assertEqual(response.status_code, 400)

    def test_no_se_filtran_usuarios_por_voto(self):
        for filtro in ('votos_festival', 'votos_festival__exact'):
            with self.subTest(filtro=filtro):
                response = self.client.get(reverse('admin:auth_user_changelist'), {filtro: self.voto.pk})
                self.assertEqual(response.status_code, 400)

    def test_los_filtros_normales_siguen_funcionando(self):
        votos = self.client.get(reverse('admin:votaciones_voto_changelist'), {'categoria__id__exact': self.voto.categoria_id})
        usuarios = self.client.get(reverse('admin:auth_user_changelist'), {'is_staff__exact': 1})

        self.assertContains(votos, self.voto.codigo_comprobante)
        self.assertEqual(usuarios.status_code, 200)


class ReglaVotoPorCategoriaTests(TestCase):
    """Regla central de la Entrega 3 y casos CP-01 a CP-08 y CP-10 de la guía."""

    def setUp(self):
        self.musica = Categoria.objects.get(nombre='Música')
        self.edicion = self.musica.edicion
        self.artista = Encuesta.objects.get(nombre='Artista favorito del público')
        self.opcion = self.artista.opciones.first()
        self.subevento = Encuesta.objects.create(
            categoria=self.musica,
            nombre='Subevento de Música',
            descripcion='Otra encuesta activa de la misma categoría.',
            estado='activa',
        )
        self.opcion_subevento = OpcionEncuesta.objects.create(encuesta=self.subevento, nombre='Opción del subevento')
        self.piloneras = Categoria.objects.get(nombre='Piloneras')
        self.otra_encuesta = Encuesta.objects.create(
            categoria=self.piloneras,
            nombre='Encuesta de Piloneras',
            descripcion='Encuesta activa de otra categoría.',
            estado='activa',
        )
        self.otra_opcion = OpcionEncuesta.objects.create(encuesta=self.otra_encuesta, nombre='Opción de Piloneras')
        self.usuario = User.objects.create_user(username='votante-regla', password='TestPassword123!')
        self.client.force_login(self.usuario)

    def votar(self, encuesta, opcion, **kwargs):
        return self.client.post(reverse('votar_encuesta', args=[encuesta.pk]), {'opcion': opcion.pk}, **kwargs)

    def test_cp01_voto_valido_guarda_usuario_edicion_categoria_y_opcion(self):
        self.votar(self.artista, self.opcion)

        voto = Voto.objects.get()
        self.assertEqual(voto.usuario, self.usuario)
        self.assertEqual(voto.edicion, self.edicion)
        self.assertEqual(voto.categoria, self.musica)
        self.assertEqual(voto.encuesta, self.artista)
        self.assertEqual(voto.opcion, self.opcion)

    def test_cp02_segundo_voto_en_otro_subevento_de_la_categoria_se_rechaza(self):
        self.votar(self.artista, self.opcion)

        response = self.votar(self.subevento, self.opcion_subevento, follow=True)

        self.assertContains(response, 'Ya votaste en la categoría Música')
        self.assertEqual(Voto.objects.count(), 1)
        self.assertEqual(Voto.objects.get().encuesta, self.artista)
        evento = Bitacora.objects.get(accion='Intento de voto duplicado')
        self.assertIn('Subevento de Música', evento.detalles)

    def test_cp02_abrir_otro_subevento_tras_votar_no_ofrece_el_formulario(self):
        self.votar(self.artista, self.opcion)

        response = self.client.get(reverse('votar_encuesta', args=[self.subevento.pk]), follow=True)

        self.assertRedirects(response, reverse('categoria_encuestas', args=[self.musica.pk]))
        self.assertContains(response, 'Ya votaste en esta categoría')
        self.assertNotContains(response, 'Elegir mi favorito')
        # Solo abrirla no es un intento de voto.
        self.assertFalse(Bitacora.objects.filter(accion='Intento de voto duplicado').exists())

    def test_cp02_reabrir_la_encuesta_votada_lleva_al_comprobante(self):
        self.votar(self.artista, self.opcion)

        response = self.client.get(reverse('votar_encuesta', args=[self.artista.pk]))

        self.assertRedirects(response, reverse('voto_exitoso', args=[Voto.objects.get().pk]))

    def test_cp03_permite_votar_en_otra_categoria(self):
        self.votar(self.artista, self.opcion)

        response = self.votar(self.otra_encuesta, self.otra_opcion)

        self.assertEqual(Voto.objects.count(), 2)
        voto = Voto.objects.get(categoria=self.piloneras)
        self.assertRedirects(response, reverse('voto_exitoso', args=[voto.pk]))

    def test_la_regla_es_por_edicion_la_misma_categoria_se_vota_en_otra(self):
        edicion_2028 = Edicion.objects.create(
            nombre='Edición 2028', anio=2028, fecha_inicio=date(2028, 4, 26), fecha_fin=date(2028, 4, 29), estado='activa',
        )
        musica_2028 = Categoria.objects.create(edicion=edicion_2028, nombre='Música', descripcion='Edición 2028.')
        encuesta_2028 = Encuesta.objects.create(categoria=musica_2028, nombre='Artista 2028', descripcion='.', estado='activa')
        opcion_2028 = OpcionEncuesta.objects.create(encuesta=encuesta_2028, nombre='Opción 2028')
        self.votar(self.artista, self.opcion)

        self.votar(encuesta_2028, opcion_2028)

        self.assertEqual(Voto.objects.filter(usuario=self.usuario, categoria__nombre='Música').count(), 2)

    def test_cp04_sin_sesion_se_exige_autenticacion(self):
        self.client.logout()
        url = reverse('votar_encuesta', args=[self.artista.pk])

        response = self.client.post(url, {'opcion': self.opcion.pk})

        self.assertRedirects(response, f'{reverse("login")}?next={url}')
        self.assertEqual(Voto.objects.count(), 0)

    def test_cp05_categoria_oculta_se_rechaza(self):
        Categoria.objects.filter(pk=self.musica.pk).update(activa=False)

        response = self.votar(self.artista, self.opcion)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Voto.objects.count(), 0)

    def test_cp05_encuesta_cerrada_se_rechaza(self):
        Encuesta.objects.filter(pk=self.artista.pk).update(estado='cerrada')

        response = self.votar(self.artista, self.opcion, follow=True)

        self.assertContains(response, 'ya está cerrada')
        self.assertEqual(Voto.objects.count(), 0)

    def test_cp05_edicion_no_habilitada_se_rechaza_aunque_la_encuesta_este_activa(self):
        Edicion.objects.filter(pk=self.edicion.pk).update(estado='finalizada')

        response = self.votar(self.artista, self.opcion, follow=True)

        self.assertContains(response, 'no está habilitada para votar')
        self.assertEqual(Voto.objects.count(), 0)

    def test_cp06_opcion_de_otra_categoria_se_rechaza_y_se_audita(self):
        response = self.votar(self.artista, self.otra_opcion)

        self.assertContains(response, 'no pertenece a esta votación', status_code=400)
        self.assertEqual(Voto.objects.count(), 0)
        self.assertTrue(Bitacora.objects.filter(accion='Intento de voto con opción inválida').exists())

    def test_opcion_vacia_o_mal_formada_se_rechaza_sin_error_del_servidor(self):
        url = reverse('votar_encuesta', args=[self.artista.pk])

        for valor in ('', 'abc', '-1', '1 OR 1=1', '9' * 30):
            with self.subTest(valor=valor):
                self.assertEqual(self.client.post(url, {'opcion': valor}).status_code, 400)
        self.assertEqual(Voto.objects.count(), 0)

    def test_post_sin_token_csrf_se_rechaza(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)

        response = cliente.post(reverse('votar_encuesta', args=[self.artista.pk]), {'opcion': self.opcion.pk})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Voto.objects.count(), 0)

    def test_cp07_el_votante_consulta_sus_categorias_votadas(self):
        self.votar(self.artista, self.opcion)

        response = self.client.get(reverse('perfil_comprobantes'))

        filas = {fila['categoria'].nombre: fila['voto'] for fila in response.context['participacion']}
        self.assertEqual(filas['Música'], Voto.objects.get())
        self.assertIsNone(filas['Piloneras'])
        self.assertContains(response, 'Votaste en «Artista favorito del público»')
        self.assertContains(response, 'Aún no has votado en esta categoría')
        # El votante no ve aquí la opción elegida (CU-05).
        self.assertNotContains(response, self.opcion.nombre)

    def test_catalogo_marca_las_categorias_votadas(self):
        self.votar(self.artista, self.opcion)

        response = self.client.get(reverse('categorias_publicas'))

        self.assertEqual(response.context['categorias_votadas'], {self.musica.pk})
        self.assertContains(response, 'Ya votaste')

    def test_cp08_administrador_consulta_los_votos_registrados(self):
        self.votar(self.artista, self.opcion)
        voto = Voto.objects.get()
        self.client.force_login(User.objects.create_user(username='admin-votos', password='TestPassword123!', is_staff=True))

        response = self.client.get(reverse('admin_votos'))

        self.assertEqual(list(response.context['pagina']), [voto])
        self.assertContains(response, voto.codigo_comprobante)
        self.assertContains(response, self.opcion.nombre)
        # La consulta no asocia la opción con la persona que votó (RF-10).
        self.assertNotContains(response, self.usuario.username)

    def test_cp08_django_admin_tampoco_asocia_la_opcion_con_el_votante(self):
        self.votar(self.artista, self.opcion)
        voto = Voto.objects.get()
        self.client.force_login(User.objects.create_superuser('admin-django', 'admin@festivalvallenato.com', 'ClaveAdmin2027!'))

        lista = self.client.get(reverse('admin:votaciones_voto_changelist'))
        detalle = self.client.get(reverse('admin:votaciones_voto_change', args=[voto.pk]))

        self.assertContains(lista, voto.codigo_comprobante)
        self.assertContains(detalle, voto.codigo_comprobante)
        self.assertNotContains(lista, self.usuario.username)
        self.assertNotContains(detalle, self.usuario.username)

    def test_cp08_filtro_por_categoria(self):
        self.votar(self.artista, self.opcion)
        self.votar(self.otra_encuesta, self.otra_opcion)
        self.client.force_login(User.objects.create_user(username='admin-votos', password='TestPassword123!', is_staff=True))

        response = self.client.get(reverse('admin_votos'), {'categoria': self.piloneras.pk})

        self.assertEqual([voto.categoria for voto in response.context['pagina']], [self.piloneras])

    def test_mysql_rechaza_el_duplicado_aunque_se_salte_la_vista(self):
        Voto.objects.create(encuesta=self.artista, opcion=self.opcion, usuario=self.usuario)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Voto.objects.create(encuesta=self.subevento, opcion=self.opcion_subevento, usuario=self.usuario)

        self.assertEqual(Voto.objects.count(), 1)

    def test_la_vista_gestiona_el_error_de_integridad_de_una_solicitud_simultanea(self):
        # Simula a la solicitud que pasó la validación justo antes de que la otra guardara su voto.
        Voto.objects.create(encuesta=self.artista, opcion=self.opcion, usuario=self.usuario)
        voto_real = Voto.objects.get()

        with mock.patch('votaciones.views.voto_en_categoria', side_effect=[None, voto_real]):
            response = self.votar(self.subevento, self.opcion_subevento)

        self.assertRedirects(response, reverse('categoria_encuestas', args=[self.musica.pk]))
        self.assertEqual(Voto.objects.count(), 1)
        self.assertTrue(Bitacora.objects.filter(accion='Intento de voto duplicado').exists())

    def test_el_modelo_no_acepta_una_opcion_de_otra_encuesta(self):
        with self.assertRaises(ValidationError):
            Voto.objects.create(encuesta=self.artista, opcion=self.otra_opcion, usuario=self.usuario)

    def test_no_se_mueve_una_encuesta_ni_una_categoria_con_votos(self):
        Voto.objects.create(encuesta=self.artista, opcion=self.opcion, usuario=self.usuario)
        otra_edicion = Edicion.objects.create(
            nombre='Edición 2028', anio=2028, fecha_inicio=date(2028, 4, 26), fecha_fin=date(2028, 4, 29),
        )

        self.artista.categoria = self.piloneras
        with self.assertRaises(ValidationError):
            self.artista.full_clean()
        self.musica.edicion = otra_edicion
        with self.assertRaises(ValidationError):
            self.musica.full_clean()

    def test_no_se_mueve_una_opcion_con_votos(self):
        Voto.objects.create(encuesta=self.artista, opcion=self.opcion, usuario=self.usuario)

        self.opcion.encuesta = self.subevento
        with self.assertRaises(ValidationError):
            self.opcion.full_clean()


class ApiCategoriasTests(TestCase):
    """CP-10: GET /api/categorias/."""

    def setUp(self):
        self.url = reverse('api_categorias')

    def test_cp10_devuelve_json_con_categorias_y_opciones_de_mysql(self):
        response = self.client.get(self.url)

        self.assertEqual(self.url, '/api/categorias/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        datos = json.loads(response.content)
        self.assertEqual(datos['edicion']['anio'], 2027)
        self.assertEqual(datos['total_categorias'], 3)
        self.assertEqual([categoria['nombre'] for categoria in datos['categorias']], ['Música', 'Piloneras', 'Comparsas'])
        artista = next(v for v in datos['categorias'][0]['votaciones'] if v['nombre'] == 'Artista favorito del público')
        self.assertEqual(
            [opcion['nombre'] for opcion in artista['opciones']],
            list(Encuesta.objects.get(pk=artista['id']).opciones.values_list('nombre', flat=True)),
        )
        self.assertIn('Mateo Díaz', response.content.decode())

    def test_refleja_los_cambios_de_la_base_de_datos(self):
        encuesta = Encuesta.objects.get(nombre='Artista favorito del público')
        OpcionEncuesta.objects.create(encuesta=encuesta, nombre='Opción recién creada', orden=9)

        self.assertContains(self.client.get(self.url), 'Opción recién creada')

    def test_no_incluye_categorias_ocultas(self):
        Categoria.objects.filter(nombre='Piloneras').update(activa=False)

        datos = self.client.get(self.url).json()

        self.assertNotIn('Piloneras', [categoria['nombre'] for categoria in datos['categorias']])

    def test_es_publica_y_no_expone_votos(self):
        encuesta = Encuesta.objects.get(nombre='Artista favorito del público')
        usuario = User.objects.create_user(username='votante-api', password='TestPassword123!')
        voto = Voto.objects.create(encuesta=encuesta, opcion=encuesta.opciones.first(), usuario=usuario)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, voto.codigo_comprobante)
        self.assertNotIn('votos', response.content.decode())

    def test_solo_acepta_get(self):
        self.assertEqual(self.client.post(self.url).status_code, 405)

    def test_sin_ediciones_responde_lista_vacia(self):
        Voto.objects.all().delete()
        Encuesta.objects.all().delete()
        Categoria.objects.all().delete()
        Edicion.objects.all().delete()

        datos = self.client.get(self.url).json()

        self.assertIsNone(datos['edicion'])
        self.assertEqual(datos['categorias'], [])


class DatosConcurrenciaMixin:
    """Datos propios: TransactionTestCase vacía la base al terminar y no conserva las migraciones de datos."""

    def crear_categoria_con_dos_encuestas(self):
        edicion = Edicion.objects.create(
            nombre='Edición de concurrencia', anio=2099, fecha_inicio=date(2099, 4, 1), fecha_fin=date(2099, 4, 2), estado='activa',
        )
        categoria = Categoria.objects.create(edicion=edicion, nombre='Concurrencia', descripcion='Prueba.')
        encuestas = [
            Encuesta.objects.create(categoria=categoria, nombre=f'Subevento {numero}', descripcion='.', estado='activa', orden=numero)
            for numero in (1, 2)
        ]
        for encuesta in encuestas:
            OpcionEncuesta.objects.create(encuesta=encuesta, nombre=f'Opción de {encuesta.nombre}')
        return categoria, encuestas


class ConcurrenciaVotoTests(DatosConcurrenciaMixin, TransactionTestCase):
    """CP-09 con hilos y conexiones reales a MySQL (TestCase no sirve: todo correría en una sola transacción)."""

    def test_cp09_solicitudes_simultaneas_dejan_un_solo_voto(self):
        categoria, encuestas = self.crear_categoria_con_dos_encuestas()

        for ronda in range(10):
            usuario = User.objects.create_user(username=f'votante-simultaneo-{ronda}')
            # timeout: si un hilo falla antes de llegar a la barrera, la prueba falla en vez de colgarse.
            barrera = threading.Barrier(4, timeout=30)

            def votar(encuesta):
                cliente = Client()
                cliente.force_login(usuario)
                barrera.wait()
                cliente.post(reverse('votar_encuesta', args=[encuesta.pk]), {'opcion': encuesta.opciones.first().pk})
                connections.close_all()

            hilos = [threading.Thread(target=votar, args=[encuestas[numero % 2]]) for numero in range(4)]
            for hilo in hilos:
                hilo.start()
            for hilo in hilos:
                hilo.join()

            with self.subTest(ronda=ronda):
                self.assertEqual(Voto.objects.filter(usuario=usuario, categoria=categoria).count(), 1)


class ComandoConcurrenciaTests(DatosConcurrenciaMixin, LiveServerTestCase):
    """El comando de la demostración, contra un servidor HTTP real."""

    def test_probar_concurrencia_deja_un_voto_por_ronda_y_borra_lo_temporal(self):
        self.crear_categoria_con_dos_encuestas()
        usuarios_antes = User.objects.count()
        salida = StringIO()

        call_command('probar_concurrencia', url=self.live_server_url, rondas=3, stdout=salida)

        self.assertIn('3 de 3 rondas dejaron exactamente un voto.', salida.getvalue())
        self.assertEqual(Voto.objects.count(), 0)
        self.assertEqual(User.objects.count(), usuarios_antes)


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

    def test_nueva_edicion_cambia_portada_y_titulos_sin_tocar_codigo(self):
        Edicion.objects.filter(anio=2027).update(estado='finalizada')
        nueva = self.crear_edicion(2028, estado='activa')
        Categoria.objects.create(edicion=nueva, nombre='Canción inédita', descripcion='Votación de 2028.')

        portada = self.client.get(reverse('index'))
        login = self.client.get(reverse('login'))

        self.assertContains(portada, '<div class="hero-year">2028</div>', html=True)
        self.assertContains(portada, 'Festival de la Leyenda Vallenata 2028 | Inicio')
        self.assertContains(portada, 'Canción inédita')
        # Las categorías de 2027 ya no aparecen en la vista previa, ni el año anterior en ninguna parte.
        self.assertNotContains(portada, 'Piloneras')
        self.assertNotContains(portada, '2027')
        self.assertContains(login, 'Festival de la Leyenda Vallenata 2028 | Registro')

    def test_categorias_y_encuestas_muestran_su_anio_en_django_admin(self):
        musica_2028 = Categoria.objects.create(edicion=self.crear_edicion(2028), nombre='Música', descripcion='2028.')
        encuesta = Encuesta.objects.create(categoria=musica_2028, nombre='Acordeonista', descripcion='2028.')

        self.assertEqual(str(Categoria.objects.get(nombre='Música', edicion__anio=2027)), 'Música (2027)')
        self.assertEqual(str(musica_2028), 'Música (2028)')
        self.assertEqual(str(encuesta), 'Música (2028) - Acordeonista')


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

    def test_deja_votaciones_para_las_pruebas_de_la_entrega_3(self):
        self.cargar()

        self.assertTrue(Encuesta.objects.filter(categoria__nombre='Piloneras', estado='activa', opciones__isnull=False).exists())
        self.assertFalse(Encuesta.objects.filter(categoria__nombre='Comparsas', estado='activa').exists())
        self.assertTrue(Encuesta.objects.filter(categoria__nombre='Comparsas', estado='cerrada', opciones__isnull=False).exists())

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
        self.assertEqual(votantes.count(), 24)
        self.assertFalse(any(votante.has_usable_password() for votante in votantes))


class FechasEncuestaTests(TestCase):
    """RN-05: cada votación puede tener apertura y cierre; el sistema la abre y la cierra solo."""

    def setUp(self):
        self.encuesta = Encuesta.objects.get(nombre='Artista favorito del público')
        self.url = reverse('votar_encuesta', args=[self.encuesta.pk])
        self.usuario = User.objects.create_user(username='votante-fechas', password='TestPassword123!')
        self.client.force_login(self.usuario)

    def test_se_cierra_sola_al_cumplirse_el_cierre_y_queda_en_bitacora(self):
        self.encuesta.fecha_cierre = timezone.now() - timedelta(minutes=1)
        self.encuesta.save()

        response = self.client.post(self.url, {'opcion': self.encuesta.opciones.first().pk}, follow=True)

        self.encuesta.refresh_from_db()
        self.assertEqual(self.encuesta.estado, 'cerrada')
        self.assertContains(response, 'ya está cerrada')
        self.assertEqual(Voto.objects.count(), 0)
        self.assertTrue(Bitacora.objects.filter(accion='Cierre automático de encuesta').exists())

    def test_se_abre_sola_al_cumplirse_la_apertura(self):
        self.encuesta.estado = 'proxima'
        self.encuesta.fecha_apertura = timezone.now() - timedelta(minutes=1)
        self.encuesta.fecha_cierre = timezone.now() + timedelta(days=1)
        self.encuesta.save()

        response = self.client.get(self.url)

        self.encuesta.refresh_from_db()
        self.assertEqual(self.encuesta.estado, 'activa')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'cierra el')
        self.assertTrue(Bitacora.objects.filter(accion='Apertura automática de encuesta').exists())

    def test_antes_de_la_apertura_informa_cuando_abre(self):
        self.encuesta.estado = 'proxima'
        self.encuesta.fecha_apertura = timezone.now() + timedelta(days=2)
        self.encuesta.save()

        response = self.client.get(self.url, follow=True)

        self.assertContains(response, 'abre el')
        self.assertContains(response, 'Abre el')  # también en la tarjeta de la categoría

    def test_activa_con_apertura_futura_no_recibe_votos(self):
        self.encuesta.fecha_apertura = timezone.now() + timedelta(days=2)
        self.encuesta.save()

        response = self.client.post(self.url, {'opcion': self.encuesta.opciones.first().pk}, follow=True)

        self.encuesta.refresh_from_db()
        self.assertEqual(self.encuesta.estado, 'proxima')
        self.assertContains(response, 'abre el')
        self.assertEqual(Voto.objects.count(), 0)
        self.assertTrue(Bitacora.objects.filter(accion='Aplazamiento automático de encuesta').exists())

    def test_cierre_no_puede_ser_anterior_a_la_apertura(self):
        self.encuesta.fecha_apertura = timezone.now()
        self.encuesta.fecha_cierre = timezone.now() - timedelta(hours=1)

        with self.assertRaises(ValidationError):
            self.encuesta.full_clean()
