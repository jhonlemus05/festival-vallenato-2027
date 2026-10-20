from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
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
