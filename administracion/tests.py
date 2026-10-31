from datetime import date

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from usuarios.models import Bitacora, Usuario
from votaciones.models import Edicion, Categoria, Encuesta, OpcionEncuesta, Voto


class GestionCategoriasTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin-categorias',
            password='TestPassword123!',
            is_staff=True,
        )
        self.votante = User.objects.create_user(
            username='votante-categorias',
            password='TestPassword123!',
        )
        self.url = reverse('categorias')
        self.client.force_login(self.admin)

    def test_panel_solo_para_administradores(self):
        vistas = ['panel_principal', 'categorias', 'admin_votaciones', 'admin_resultados', 'admin_votos']

        # Sin sesión: al login, recordando a dónde quería ir.
        self.client.logout()
        for nombre in vistas:
            with self.subTest(sin_sesion=nombre):
                response = self.client.get(reverse(nombre))
                self.assertRedirects(response, f"{reverse('login')}?next={reverse(nombre)}", fetch_redirect_response=False)

        # Votante con sesión: 403 (al login no, porque lo devolvería aquí en bucle).
        self.client.force_login(self.votante)
        for nombre in vistas:
            with self.subTest(votante=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 403)

        self.client.force_login(self.admin)
        for nombre in vistas:
            with self.subTest(administrador=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)

    def test_votante_no_puede_crear_categorias_y_el_intento_queda_en_bitacora(self):
        self.client.force_login(self.votante)

        response = self.client.post(self.url, {
            'nombre': 'Categoría intrusa',
            'descripcion': 'No debería guardarse.',
            'icono': 'music',
            'activa': 'on',
        })

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Categoria.objects.filter(nombre='Categoría intrusa').exists())
        self.assertTrue(Bitacora.objects.filter(accion='Acceso denegado al panel administrativo').exists())

    def test_perfil_con_rol_administrador_entra_al_panel(self):
        usuario = User.objects.create_user(username='rol-admin@correo.com', password='TestPassword123!')
        Usuario.objects.create(
            user=usuario,
            identificacion='1065999111',
            correo='rol-admin@correo.com',
            rol='administrador',
        )
        self.client.force_login(usuario)

        self.assertEqual(self.client.get(reverse('panel_principal')).status_code, 200)

    def test_enlace_al_panel_solo_se_muestra_a_administradores(self):
        response = self.client.get(reverse('categorias_publicas'))
        self.assertContains(response, reverse('panel_principal'))

        self.client.force_login(self.votante)
        response = self.client.get(reverse('categorias_publicas'))
        self.assertNotContains(response, reverse('panel_principal'))

    def test_crea_categoria_y_la_muestra_en_el_catalogo_publico(self):
        response = self.client.post(self.url, {
            'nombre': 'Canción inédita',
            'descripcion': 'Composiciones originales del festival.',
            'icono': 'music',
            'activa': 'on',
        })

        self.assertRedirects(response, self.url)
        self.assertTrue(Categoria.objects.filter(nombre='Canción inédita', activa=True).exists())
        self.assertContains(self.client.get(reverse('categorias_publicas')), 'Canción inédita')

    def test_edita_categoria_y_puede_ocultarla_de_la_vista_publica(self):
        categoria = Categoria.objects.get(nombre='Música')

        response = self.client.post(self.url, {
            'categoria_id': categoria.pk,
            'nombre': categoria.nombre,
            'descripcion': 'Nueva descripción del festival.',
            'icono': 'music',
        })

        self.assertRedirects(response, self.url)
        categoria.refresh_from_db()
        self.assertEqual(categoria.descripcion, 'Nueva descripción del festival.')
        self.assertFalse(categoria.activa)
        public_response = self.client.get(reverse('categorias_publicas'))
        self.assertFalse(any(
            categoria.nombre == 'Música'
            for categoria in public_response.context['categorias']
        ))

    def test_rechaza_nombres_duplicados_sin_guardar(self):
        response = self.client.post(self.url, {
            'nombre': 'mÚSICA',
            'descripcion': 'Nombre duplicado.',
            'icono': 'music',
            'activa': 'on',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe una categoría con ese nombre.')
        self.assertEqual(Categoria.objects.count(), 3)

    def test_altas_y_cambios_del_panel_quedan_en_bitacora(self):
        self.client.post(self.url, {
            'nombre': 'Canción inédita',
            'descripcion': 'Composiciones originales del festival.',
            'icono': 'music',
            'activa': 'on',
        })
        categoria = Categoria.objects.get(nombre='Canción inédita')
        self.client.post(self.url, {
            'categoria_id': categoria.pk,
            'nombre': 'Canción inédita',
            'descripcion': 'Descripción corregida.',
            'icono': 'music',
            'activa': 'on',
        })

        acciones = list(Bitacora.objects.filter(accion__startswith='Categoría').values_list('accion', flat=True))
        self.assertCountEqual(acciones, ['Categoría creada', 'Categoría actualizada'])

    def test_categoria_nueva_queda_en_la_edicion_vigente(self):
        self.client.post(self.url, {
            'nombre': 'Canción inédita',
            'descripcion': 'Composiciones originales del festival.',
            'icono': 'music',
            'activa': 'on',
        })

        categoria = Categoria.objects.get(nombre='Canción inédita')
        self.assertEqual(categoria.edicion, Edicion.vigente())

    def test_nombre_repetido_de_otra_edicion_no_se_toma_como_duplicado(self):
        anterior = Edicion.objects.create(
            nombre='Festival de la Leyenda Vallenata 2026',
            anio=2026,
            fecha_inicio=date(2026, 4, 29),
            fecha_fin=date(2026, 5, 2),
            estado='finalizada',
        )
        Categoria.objects.create(edicion=anterior, nombre='Canción inédita', descripcion='Edición anterior.')

        response = self.client.post(self.url, {
            'nombre': 'Canción inédita',
            'descripcion': 'Composiciones originales del festival.',
            'icono': 'music',
            'activa': 'on',
        })

        self.assertRedirects(response, self.url)
        self.assertEqual(Categoria.objects.filter(nombre='Canción inédita').count(), 2)

    def test_crea_encuesta_en_categoria_desde_el_panel(self):
        categoria = Categoria.objects.get(nombre='Música')

        response = self.client.post(self.url, {
            'action': 'save_encuesta',
            'encuesta_categoria_id': categoria.pk,
            'encuesta_id': '',
            'encuesta-nombre': 'Piqueria',
            'encuesta-descripcion': 'La tradición de la piqueria vallenata.',
            'encuesta-detalle': 'Encuesta en preparación.',
            'encuesta-estado': 'proxima',
        })

        self.assertRedirects(response, self.url)
        self.assertTrue(Encuesta.objects.filter(
            categoria=categoria,
            nombre='Piqueria',
            estado='proxima',
        ).exists())

    def test_programa_apertura_y_cierre_de_una_encuesta(self):
        categoria = Categoria.objects.get(nombre='Música')
        datos = {
            'action': 'save_encuesta',
            'encuesta_categoria_id': categoria.pk,
            'encuesta_id': '',
            'encuesta-nombre': 'Piqueria',
            'encuesta-descripcion': 'La tradición de la piqueria vallenata.',
            'encuesta-detalle': '',
            'encuesta-estado': 'proxima',
            'encuesta-fecha_apertura': '2027-04-28T08:00',
            'encuesta-fecha_cierre': '2027-05-01T18:00',
        }

        response = self.client.post(self.url, datos)

        self.assertRedirects(response, self.url)
        encuesta = Encuesta.objects.get(nombre='Piqueria')
        self.assertEqual(timezone.localtime(encuesta.fecha_apertura).strftime('%Y-%m-%d %H:%M'), '2027-04-28 08:00')

        # Cierre antes de la apertura: no se guarda y se explica (CU-06, flujo 5b).
        response = self.client.post(self.url, {**datos, 'encuesta-nombre': 'Piqueria 2', 'encuesta-fecha_cierre': '2027-04-27T18:00'})
        self.assertContains(response, 'El cierre debe ser posterior a la apertura.')
        self.assertFalse(Encuesta.objects.filter(nombre='Piqueria 2').exists())

    def test_edita_estado_y_detalle_de_encuesta(self):
        encuesta = Encuesta.objects.get(nombre='Acordeonista')

        response = self.client.post(self.url, {
            'action': 'save_encuesta',
            'encuesta_categoria_id': encuesta.categoria_id,
            'encuesta_id': encuesta.pk,
            'encuesta-nombre': encuesta.nombre,
            'encuesta-descripcion': encuesta.descripcion,
            'encuesta-detalle': '4 participantes · Un voto por persona',
            'encuesta-estado': 'activa',
        })

        self.assertRedirects(response, self.url)
        encuesta.refresh_from_db()
        self.assertEqual(encuesta.estado, 'activa')
        self.assertEqual(encuesta.detalle, '4 participantes · Un voto por persona')

    def test_rechaza_nombre_de_encuesta_duplicado_en_categoria(self):
        musica = Categoria.objects.get(nombre='Música')

        response = self.client.post(self.url, {
            'action': 'save_encuesta',
            'encuesta_categoria_id': musica.pk,
            'encuesta_id': '',
            'encuesta-nombre': 'artista favorito del público',
            'encuesta-descripcion': 'Duplicada.',
            'encuesta-detalle': '',
            'encuesta-estado': 'activa',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe una encuesta con ese nombre en esta categoría.')
        self.assertEqual(Encuesta.objects.filter(categoria=musica).count(), 4)

    def test_crea_opcion_para_encuesta_de_cualquier_categoria(self):
        piloneras = Categoria.objects.get(nombre='Piloneras')
        encuesta = Encuesta.objects.create(
            categoria=piloneras,
            nombre='Reina de Piloneras',
            descripcion='Elige la representante de piloneras.',
            estado='activa',
        )

        response = self.client.post(self.url, {
            'action': 'save_opcion',
            'opcion_encuesta_id': encuesta.pk,
            'opcion_id': '',
            'opcion-nombre': 'María del Valle',
            'opcion-descripcion': 'Comparsa Las Raíces',
            'opcion-imagen': '',
        })

        self.assertRedirects(response, self.url)
        opcion = OpcionEncuesta.objects.get(encuesta=encuesta)
        self.assertEqual(opcion.nombre, 'María del Valle')
        self.assertEqual(opcion.descripcion, 'Comparsa Las Raíces')
        self.assertEqual(opcion.imagen, '')
        self.assertContains(self.client.get(self.url), 'María del Valle')

    def test_edita_opcion_de_una_encuesta(self):
        opcion = OpcionEncuesta.objects.get(nombre='Mateo Díaz')

        response = self.client.post(self.url, {
            'action': 'save_opcion',
            'opcion_encuesta_id': opcion.encuesta_id,
            'opcion_id': opcion.pk,
            'opcion-nombre': 'Mateo Díaz',
            'opcion-descripcion': 'Nueva canción',
            'opcion-imagen': opcion.imagen,
        })

        self.assertRedirects(response, self.url)
        opcion.refresh_from_db()
        self.assertEqual(opcion.descripcion, 'Nueva canción')

    def test_rechaza_opcion_duplicada_en_la_misma_encuesta(self):
        opcion = OpcionEncuesta.objects.get(nombre='Mateo Díaz')

        response = self.client.post(self.url, {
            'action': 'save_opcion',
            'opcion_encuesta_id': opcion.encuesta_id,
            'opcion_id': '',
            'opcion-nombre': 'mateo díaz',
            'opcion-descripcion': '',
            'opcion-imagen': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe una opción con ese nombre en esta encuesta.')
        self.assertEqual(OpcionEncuesta.objects.filter(encuesta=opcion.encuesta).count(), 4)

    def test_rechaza_rutas_de_imagen_que_salen_de_static(self):
        encuesta = Encuesta.objects.get(nombre='Artista favorito del público')

        response = self.client.post(self.url, {
            'action': 'save_opcion',
            'opcion_encuesta_id': encuesta.pk,
            'opcion_id': '',
            'opcion-nombre': 'Participante externo',
            'opcion-descripcion': '',
            'opcion-imagen': '../secreto.jpg',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Indica una ruta relativa dentro de los archivos estáticos.')
        self.assertFalse(OpcionEncuesta.objects.filter(nombre='Participante externo').exists())


class PanelPrincipalTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user(
            username='admin-panel',
            password='TestPassword123!',
            is_staff=True,
        ))

    def test_resumen_se_actualiza_con_votos_usuarios_y_encuestas_visibles(self):
        encuesta = Encuesta.objects.get(nombre='Artista favorito del público')
        categoria_oculta = Categoria.objects.get(nombre='Piloneras')
        categoria_oculta.activa = False
        categoria_oculta.save()
        Encuesta.objects.create(
            categoria=categoria_oculta,
            nombre='Encuesta oculta',
            descripcion='No debe aparecer en el resumen público de votaciones.',
            estado='activa',
        )
        User.objects.create_user(username='panel-votante-1', password='TestPassword123!')
        usuario_2 = User.objects.create_user(username='panel-votante-2', password='TestPassword123!')
        opcion = encuesta.opciones.first()
        Voto.objects.create(encuesta=encuesta, opcion=opcion, usuario=usuario_2)

        response = self.client.get(reverse('panel_principal'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_votos'], 1)
        # Los dos votantes más la cuenta administradora con la que se entra al panel.
        self.assertEqual(response.context['total_usuarios'], 3)
        self.assertEqual(
            response.context['total_encuestas_activas'],
            Encuesta.objects.filter(estado='activa', categoria__activa=True).count(),
        )
        self.assertEqual(response.context['total_votos_recientes'], 1)
        self.assertContains(response, 'Artista favorito del público')
        self.assertNotContains(response, 'Encuesta oculta')
        self.assertNotIn('Piloneras', response.context['categorias_activas'])
        self.assertTrue(all(
            encuesta.categoria.activa
            for encuesta in response.context['encuestas_activas']
        ))
        encuesta_artista = next(
            encuesta for encuesta in response.context['encuestas_activas']
            if encuesta.nombre == 'Artista favorito del público'
        )
        self.assertEqual(encuesta_artista.porcentaje_votos, 100)

    def test_resumen_muestra_estado_vacio_si_no_hay_encuestas_activas_visibles(self):
        Categoria.objects.update(activa=False)

        response = self.client.get(reverse('panel_principal'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_encuestas_activas'], 0)
        self.assertContains(response, 'No hay encuestas activas en categorías visibles.')
        self.assertNotContains(response, 'Artista favorito del público')

    def test_panel_muestra_solo_la_edicion_vigente_y_quien_esta_conectado(self):
        anterior = Edicion.objects.create(
            nombre='Festival de la Leyenda Vallenata 2026',
            anio=2026,
            fecha_inicio=date(2026, 4, 29),
            fecha_fin=date(2026, 5, 2),
            estado='finalizada',
        )
        musica_2026 = Categoria.objects.create(edicion=anterior, nombre='Música', descripcion='Edición anterior.')
        encuesta_2026 = Encuesta.objects.create(
            categoria=musica_2026,
            nombre='Encuesta 2026',
            descripcion='De la edición anterior.',
            estado='activa',
        )
        opcion_2026 = OpcionEncuesta.objects.create(encuesta=encuesta_2026, nombre='Opción 2026')
        votante = User.objects.create_user(username='votante-2026', password='TestPassword123!')
        Voto.objects.create(encuesta=encuesta_2026, opcion=opcion_2026, usuario=votante)

        response = self.client.get(reverse('panel_principal'))

        self.assertEqual(response.context['edicion'].anio, 2027)
        self.assertEqual(response.context['total_votos'], 0)
        self.assertEqual(response.context['categorias_activas'], ['Música', 'Piloneras', 'Comparsas'])
        self.assertNotIn(encuesta_2026, response.context['encuestas_activas'])
        self.assertContains(response, 'admin-panel')
        self.assertNotContains(response, 'Panel sin autenticación')
        self.assertNotContains(response, 'href="#"')
        # El panel tiene su propio "Cerrar sesión" (POST al logout).
        self.assertContains(response, f'action="{reverse("logout")}"')
