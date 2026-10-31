# Cuentas de prueba

> Cuentas **ficticias** para desarrollo local, capturas y video. Viven en la base MySQL de cada integrante, que no se
> sube al repositorio, así que cada quien las crea con la sección 4 y elige su propia contraseña local.
> Aquí no se publican contraseñas: la guía de la Entrega 3 lo prohíbe.

## 1. Cuenta de Votante

| Campo | Valor |
| :--- | :--- |
| Correo electrónico | `votante@festivalvallenato.com` |
| Número de documento | `1065888999` |
| Rol | Votante |

## 2. Cuenta de Administrador (también accede a Django Admin `/admin/`)

| Campo | Valor |
| :--- | :--- |
| Correo electrónico / usuario | `admin@festivalvallenato.com` |
| Número de documento | `1065000111` |
| Rol | Administrador (`is_staff=True`, `is_superuser=True`) |

## 3. Cómo iniciar sesión

- Ruta: `http://127.0.0.1:8000/usuarios/login/`
- Se puede ingresar con el **correo** o con el **número de documento** más la contraseña.
- Al entrar se llega a **Mi perfil**: `http://127.0.0.1:8000/usuarios/perfil/` (datos, cambio de contraseña y actividad).
- Django Admin (solo administrador): `http://127.0.0.1:8000/admin/`

## 4. Crear las cuentas en tu entorno

Con MySQL configurado (README, sección 8):

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py shell
```

En Windows, el intérprete es `.venv\Scripts\python`. Dentro del shell, pega esto; pide las dos contraseñas sin
mostrarlas en pantalla:

```python
from getpass import getpass
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from usuarios.models import Usuario

def crear(correo, doc, clave, rol, staff):
    u, _ = User.objects.update_or_create(
        username=correo,
        defaults={'email': correo, 'is_staff': staff, 'is_superuser': staff,
                  'password': make_password(clave, hasher='pbkdf2_sha256')},
    )
    Usuario.objects.update_or_create(
        user=u,
        defaults={'identificacion': doc, 'correo': correo,
                  'password_hash': u.password, 'rol': rol, 'acepta_terminos': True},
    )

crear('votante@festivalvallenato.com', '1065888999', getpass('Clave del votante: '), 'votante', False)
crear('admin@festivalvallenato.com', '1065000111', getpass('Clave del administrador: '), 'administrador', True)
```

## 5. Seguridad aplicada a estas cuentas

- Contraseñas cifradas con **PBKDF2-HMAC-SHA256** (1.500.000 iteraciones, sal aleatoria); nunca en texto plano.
- Cada evento queda en la tabla `bitacora` con firma de integridad **SHA-256**.
- Bloqueo temporal de 15 minutos tras 5 intentos fallidos de inicio de sesión.
