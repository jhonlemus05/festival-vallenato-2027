from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from votaciones.models import Encuesta, Voto

from .models import Usuario, Bitacora


class UsuariosAuthSecurityTests(TestCase):
    """
    Pruebas de integración del flujo de autenticación. Usan el test client de Django,
    así que pasan por URLs, middleware, sesiones y templates reales (no mockeamos nada).
    Cada test corre en una BD en memoria limpia: no hay que limpiar datos a mano.
    """

    def test_login_page_renders(self):
        # Humo: la pantalla carga, usa el template correcto y marca "Mi cuenta" como sección activa.
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['seccion_activa'], 'cuenta')
        self.assertTemplateUsed(response, 'usuarios/login.html')

    def test_registro_exitoso_cifra_pbkdf2_sha256_y_firma_bitacora(self):
        # follow=True sigue el redirect posterior al registro hasta la pantalla final.
        response = self.client.post(
            reverse('login'),
            {
                'modo': 'register',
                'correo': 'votante1@correo.com',
                'identificacion': '1065888999',
                'password': 'Vallenato2027Segura',
                'terminos': 'on',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email='votante1@correo.com').exists())
        perfil = Usuario.objects.get(correo='votante1@correo.com')
        self.assertEqual(perfil.identificacion, '1065888999')
        self.assertEqual(perfil.rol, 'votante')
        # Lo crítico: el hash tiene el prefijo del algoritmo y la clave en claro NO aparece en BD.
        self.assertTrue(perfil.password_hash.startswith('pbkdf2_sha256$'))
        self.assertNotIn('Vallenato2027Segura', perfil.password_hash)

        # La bitácora debe existir y traer una firma SHA-256 (64 caracteres hex).
        registro_bitacora = Bitacora.objects.filter(usuario=perfil, accion='Registro de cuenta').first()
        self.assertIsNotNone(registro_bitacora)
        self.assertEqual(len(registro_bitacora.hash_sha256), 64)
        # El registro deja al usuario autenticado (login automático).
        self.assertTrue(response.context['user'].is_authenticated)

    def test_registro_duplicado_rechazado(self):
        self.client.post(
            reverse('login'),
            {
                'modo': 'register',
                'correo': 'votante1@correo.com',
                'identificacion': '1065888999',
                'password': 'Vallenato2027Segura',
                'terminos': 'on',
            },
        )
        # Cerramos sesión para simular a otra persona intentando registrarse con el mismo correo.
        self.client.post(reverse('logout'))

        response = self.client.post(
            reverse('login'),
            {
                'modo': 'register',
                'correo': 'votante1@correo.com',
                # Documento distinto a propósito: aquí lo que debe chocar es el correo.
                'identificacion': '1065999000',
                'password': 'Vallenato2027Segura',
                'terminos': 'on',
            },
        )
        # No se creó un segundo perfil y se redirige la pestaña a "login".
        self.assertEqual(Usuario.objects.count(), 1)
        self.assertEqual(response.context['modo_activo'], 'login')

    def test_login_y_logout_funcional(self):
        # Se crea la cuenta pasando por el registro real (no con create_user) para
        # probar de paso que lo que se guarda en el registro es lo que luego valida el login.
        self.client.post(
            reverse('login'),
            {
                'modo': 'register',
                'correo': 'acordeon@correo.com',
                'identificacion': '1065123456',
                'password': 'Vallenato2027Segura',
                'terminos': 'on',
            },
        )
        self.client.post(reverse('logout'))

        perfil = Usuario.objects.get(correo='acordeon@correo.com')
        response = self.client.post(
            reverse('login'),
            {
                'modo': 'login',
                'correo': 'acordeon@correo.com',
                'password': 'Vallenato2027Segura',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertTrue(Bitacora.objects.filter(usuario=perfil, accion='Inicio de sesión').exists())

        # Tras el logout la sesión debe quedar anónima y el evento auditado.
        logout_resp = self.client.post(reverse('logout'), follow=True)
        self.assertEqual(logout_resp.status_code, 200)
        self.assertFalse(logout_resp.context['user'].is_authenticated)
        self.assertTrue(Bitacora.objects.filter(usuario=perfil, accion='Cierre de sesión').exists())

    def test_bloqueo_temporal_tras_5_intentos_fallidos(self):
        self.client.post(
            reverse('login'),
            {
                'modo': 'register',
                'correo': 'seguridad@correo.com',
                'identificacion': '1065777888',
                'password': 'ClaveFuerte2027',
                'terminos': 'on',
            },
        )
        self.client.post(reverse('logout'))

        # 5 intentos con clave incorrecta = umbral de MAX_INTENTOS_FALLIDOS.
        for _ in range(5):
            self.client.post(
                reverse('login'),
                {
                    'modo': 'login',
                    'correo': 'seguridad@correo.com',
                    'password': 'ClaveIncorrecta99',
                },
            )

        perfil = Usuario.objects.get(correo='seguridad@correo.com')
        self.assertTrue(perfil.esta_bloqueado())
        self.assertEqual(perfil.intentos_fallidos, 5)
        self.assertTrue(Bitacora.objects.filter(usuario=perfil, accion='Bloqueo temporal de cuenta').exists())

        # Con la cuenta bloqueada, ni la contraseña CORRECTA debe permitir entrar.
        intento_en_bloqueo = self.client.post(
            reverse('login'),
            {
                'modo': 'login',
                'correo': 'seguridad@correo.com',
                'password': 'ClaveFuerte2027',
            },
            follow=True,
        )
        self.assertFalse(intento_en_bloqueo.context['user'].is_authenticated)
        self.assertTrue(Bitacora.objects.filter(usuario=perfil, accion='Intento en cuenta bloqueada').exists())

    def test_validacion_documento_invalido_y_clave_similar(self):
        # Caso 1: documento con caracteres no numéricos (intento de inyección) -> debe rechazarse.
        resp_doc = self.client.post(
            reverse('login'),
            {
                'modo': 'register',
                'correo': 'nuevo@correo.com',
                'identificacion': '123<script>',
                'password': 'ClaveSegura2027',
                'terminos': 'on',
            },
        )
        self.assertEqual(Usuario.objects.count(), 0)
        self.assertEqual(resp_doc.status_code, 200)

        # Caso 2: clave casi igual al correo ("valledupar1" vs valledupar@...) -> la rechaza
        # UserAttributeSimilarityValidator. Pasa los chequeos básicos (8+ chars, letras y números),
        # así que esto prueba que los validadores de Django sí se están ejecutando.
        resp_sim = self.client.post(
            reverse('login'),
            {
                'modo': 'register',
                'correo': 'valledupar@correo.com',
                'identificacion': '1065444333',
                'password': 'valledupar1',
                'terminos': 'on',
            },
        )
        self.assertEqual(Usuario.objects.count(), 0)
        self.assertEqual(resp_sim.status_code, 200)

    def test_firma_bitacora_verificable_y_detecta_alteracion(self):
        self.client.post(
            reverse('login'),
            {
                'modo': 'register',
                'correo': 'auditoria@correo.com',
                'identificacion': '1065222333',
                'password': 'Vallenato2027Segura',
                'terminos': 'on',
            },
        )
        # Se lee de la BD (no del objeto en memoria): así se prueba que la fecha guardada
        # es la misma con la que se firmó. Con auto_now_add esto fallaba.
        registro = Bitacora.objects.get(usuario__correo='auditoria@correo.com', accion='Registro de cuenta')
        self.assertTrue(registro.firma_valida())

        # Si alguien edita la fila "por debajo", la firma deja de coincidir.
        Bitacora.objects.filter(pk=registro.pk).update(detalles='Registro alterado a mano')
        registro.refresh_from_db()
        self.assertFalse(registro.firma_valida())

    def test_logout_por_get_no_cierra_sesion(self):
        # El registro deja la sesión iniciada.
        self.client.post(
            reverse('login'),
            {
                'modo': 'register',
                'correo': 'sesion@correo.com',
                'identificacion': '1065444555',
                'password': 'Vallenato2027Segura',
                'terminos': 'on',
            },
        )
        # Un GET (p. ej. un <img src="/usuarios/logout/"> en otra página) debe rechazarse con 405.
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_next_externo_no_redirige_fuera_del_sitio(self):
        self.client.post(
            reverse('login'),
            {
                'modo': 'register',
                'correo': 'redireccion@correo.com',
                'identificacion': '1065666777',
                'password': 'Vallenato2027Segura',
                'terminos': 'on',
            },
        )
        self.client.post(reverse('logout'))
        credenciales = {'modo': 'login', 'correo': 'redireccion@correo.com', 'password': 'Vallenato2027Segura'}

        # `next` hacia otro dominio: se ignora y se cae al destino por defecto (el perfil).
        response = self.client.post(reverse('login'), {**credenciales, 'next': 'https://sitio-falso.com/'})
        self.assertRedirects(response, reverse('perfil'), fetch_redirect_response=False)

        # `next` interno: se respeta.
        self.client.post(reverse('logout'))
        response = self.client.post(reverse('login'), {**credenciales, 'next': '/'})
        self.assertRedirects(response, '/', fetch_redirect_response=False)


class PerfilUsuarioTests(TestCase):
    """Pruebas de /usuarios/perfil/: acceso con sesión, datos, actividad y cambio de contraseña."""

    PASSWORD = 'Vallenato2027Segura'

    def registrar(self, correo, identificacion):
        """Registra por el flujo real (no con create_user); el registro deja la sesión iniciada."""
        return self.client.post(
            reverse('login'),
            {
                'modo': 'register',
                'correo': correo,
                'identificacion': identificacion,
                'password': self.PASSWORD,
                'terminos': 'on',
            },
        )

    def cambiar_password(self, actual, nueva, confirmacion=None):
        return self.client.post(
            reverse('perfil_contrasena'),
            {
                'password_actual': actual,
                'password_nueva': nueva,
                'password_confirmacion': nueva if confirmacion is None else confirmacion,
            },
        )

    def test_perfil_requiere_sesion_y_vuelve_tras_login(self):
        self.registrar('perfil@correo.com', '1065101010')
        self.client.post(reverse('logout'))

        # Sin sesión, @login_required manda al login con ?next=/usuarios/perfil/ ...
        response = self.client.get(reverse('perfil'))
        url_login = f"{reverse('login')}?next={reverse('perfil')}"
        self.assertRedirects(response, url_login, fetch_redirect_response=False)

        # ... esa pantalla abre la pestaña "login" y guarda el `next` en un campo oculto ...
        pantalla = self.client.get(url_login)
        self.assertEqual(pantalla.context['modo_activo'], 'login')
        self.assertContains(pantalla, 'name="next" value="/usuarios/perfil/"')

        # ... y al entrar se vuelve al perfil.
        response = self.client.post(
            reverse('login'),
            {'modo': 'login', 'correo': 'perfil@correo.com', 'password': self.PASSWORD, 'next': reverse('perfil')},
        )
        self.assertRedirects(response, reverse('perfil'), fetch_redirect_response=False)

    def test_login_con_sesion_iniciada_redirige_al_perfil(self):
        self.registrar('ya.dentro@correo.com', '1065202020')
        response = self.client.get(reverse('login'))
        self.assertRedirects(response, reverse('perfil'), fetch_redirect_response=False)

    def test_secciones_del_perfil_requieren_sesion(self):
        for nombre in ('perfil', 'perfil_contrasena', 'perfil_actividad', 'perfil_comprobantes'):
            with self.subTest(seccion=nombre):
                response = self.client.get(reverse(nombre))
                self.assertRedirects(response, f"{reverse('login')}?next={reverse(nombre)}", fetch_redirect_response=False)

    def test_menu_lateral_marca_la_seccion_activa(self):
        self.registrar('menu@correo.com', '1065707070')
        secciones = [
            ('perfil', 'datos', 'usuarios/perfil_datos.html'),
            ('perfil_contrasena', 'contrasena', 'usuarios/perfil_contrasena.html'),
            ('perfil_actividad', 'actividad', 'usuarios/perfil_actividad.html'),
            ('perfil_comprobantes', 'comprobantes', 'usuarios/perfil_comprobantes.html'),
        ]
        for nombre, seccion, template in secciones:
            with self.subTest(seccion=seccion):
                response = self.client.get(reverse(nombre))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'usuarios/perfil_base.html')
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.context['seccion_perfil'], seccion)
                # Solo el enlace de la sección actual lleva aria-current.
                self.assertContains(response, 'aria-current="page"', count=1)

    def test_perfil_muestra_datos(self):
        self.registrar('datos@correo.com', '1065303030')
        response = self.client.get(reverse('perfil'))
        self.assertEqual(response.context['perfil'].identificacion, '1065303030')
        self.assertIsNotNone(response.context['iteraciones'])
        self.assertContains(response, '1065303030')

    def test_actividad_muestra_eventos_con_firma_verificada(self):
        self.registrar('actividad@correo.com', '1065808080')
        response = self.client.get(reverse('perfil_actividad'))
        # El registro aparece en "Mi actividad" con su firma verificada.
        actividad = response.context['actividad']
        self.assertEqual(actividad[0].accion, 'Registro de cuenta')
        self.assertTrue(actividad[0].firma_ok)
        self.assertEqual(response.context['firmas_validas'], len(actividad))

    def test_cambio_password_exitoso_mantiene_esta_sesion_y_cierra_las_demas(self):
        self.registrar('cambio@correo.com', '1065404040')
        # Segunda sesión de la misma cuenta (p. ej. otro computador).
        otra_sesion = Client()
        otra_sesion.post(reverse('login'), {'modo': 'login', 'correo': 'cambio@correo.com', 'password': self.PASSWORD})
        self.assertEqual(otra_sesion.get(reverse('perfil')).status_code, 200)

        response = self.cambiar_password(self.PASSWORD, 'Acordeon2027Nueva')
        self.assertRedirects(response, reverse('perfil_contrasena'), fetch_redirect_response=False)

        perfil = Usuario.objects.get(correo='cambio@correo.com')
        self.assertTrue(perfil.user.check_password('Acordeon2027Nueva'))
        self.assertFalse(perfil.user.check_password(self.PASSWORD))
        # El espejo `password_hash` quedó con el hash nuevo.
        self.assertEqual(perfil.password_hash, perfil.user.password)
        self.assertTrue(perfil.password_hash.startswith('pbkdf2_sha256$'))
        self.assertTrue(Bitacora.objects.filter(usuario=perfil, accion='Cambio de contraseña').exists())

        # Esta sesión sigue viva (update_session_auth_hash); la otra quedó cerrada.
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 200)
        self.assertEqual(otra_sesion.get(reverse('perfil')).status_code, 302)

    def test_cambio_password_rechazos(self):
        self.registrar('rechazos@correo.com', '1065505050')
        casos = [
            (('ClaveEquivocada1', 'Acordeon2027Nueva', None), 'La contraseña actual no es correcta.'),
            ((self.PASSWORD, 'Acordeon2027Nueva', 'Acordeon2027Otra'), 'no coinciden'),
            ((self.PASSWORD, self.PASSWORD, None), 'distinta de la actual'),
            ((self.PASSWORD, 'corta1', None), 'al menos 8 caracteres'),
            # Pasa la regla básica, pero la frena CommonPasswordValidator.
            ((self.PASSWORD, 'password1', None), 'demasiado común'),
        ]
        for argumentos, mensaje in casos:
            with self.subTest(mensaje=mensaje):
                response = self.cambiar_password(*argumentos)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, mensaje)

        # Ningún intento cambió la clave, y el de clave actual errónea quedó auditado.
        perfil = Usuario.objects.get(correo='rechazos@correo.com')
        self.assertTrue(perfil.user.check_password(self.PASSWORD))
        self.assertTrue(Bitacora.objects.filter(usuario=perfil, accion='Intento fallido de cambio de contraseña').exists())

    def test_cambio_password_bloquea_y_cierra_sesion_tras_5_fallos(self):
        self.registrar('robo@correo.com', '1065606060')
        for _ in range(5):
            response = self.cambiar_password('NoEsLaClave99', 'Acordeon2027Nueva')

        # El quinto fallo bloquea la cuenta y cierra la sesión.
        self.assertRedirects(response, '/usuarios/login/?modo=login', fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)
        perfil = Usuario.objects.get(correo='robo@correo.com')
        self.assertTrue(perfil.esta_bloqueado())
        self.assertTrue(perfil.user.check_password(self.PASSWORD))


class MisComprobantesTests(TestCase):
    """CU-05: el votante ve sus comprobantes y puede verificar un código, sin que se muestre la opción elegida."""

    def setUp(self):
        self.encuesta = Encuesta.objects.get(nombre='Artista favorito del público')
        self.opciones = list(self.encuesta.opciones.all())
        self.votante = User.objects.create_user(username='comprobantes@correo.com', password='TestPassword123!')
        self.otro = User.objects.create_user(username='otro@correo.com', password='TestPassword123!')
        self.client.force_login(self.votante)

    def test_sin_votos_lo_informa(self):
        response = self.client.get(reverse('perfil_comprobantes'))

        self.assertContains(response, 'Todavía no has votado en ninguna encuesta.')

    def test_lista_solo_mis_votos_sin_la_opcion_elegida(self):
        mio = Voto.objects.create(encuesta=self.encuesta, opcion=self.opciones[1], usuario=self.votante)
        ajeno = Voto.objects.create(encuesta=self.encuesta, opcion=self.opciones[2], usuario=self.otro)

        response = self.client.get(reverse('perfil_comprobantes'))

        self.assertContains(response, mio.codigo_comprobante)
        self.assertContains(response, self.encuesta.nombre)
        self.assertNotContains(response, ajeno.codigo_comprobante)
        self.assertNotContains(response, self.opciones[1].nombre)

    def test_verificar_un_codigo_confirma_si_existe_sin_revelar_la_opcion(self):
        ajeno = Voto.objects.create(encuesta=self.encuesta, opcion=self.opciones[2], usuario=self.otro)

        # Se acepta en minúsculas y con espacios, como lo escribiría una persona.
        response = self.client.get(reverse('perfil_comprobantes'), {'codigo': f'  {ajeno.codigo_comprobante.lower()} '})

        self.assertContains(response, 'está registrado')
        self.assertNotContains(response, self.opciones[2].nombre)
        self.assertNotContains(response, 'otro@correo.com')

        response = self.client.get(reverse('perfil_comprobantes'), {'codigo': 'FV-AAAA-AAAA'})
        self.assertContains(response, 'No hay ningún voto registrado con el comprobante')
