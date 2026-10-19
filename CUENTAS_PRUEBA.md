# Cuentas de prueba — Módulo `usuarios`

> Datos **unicamente para prueba** de desarrollo local, capturas y video de la Entrega 2.
> Las cuentas viven en `db.sqlite3` (ignorado por git),
> por lo que cada compañero debe recrearlas en su entorno (ver sección 4).

## 1. Cuenta de Votante

| Campo | Valor |
| :--- | :--- |
| Correo electrónico | `votante@festivalvallenato.com` |
| Número de documento | `1065888999` |
| Contraseña | `Vallenato2027*` |
| Rol | Votante |
| `password_hash` | `pbkdf2_sha256$1500000$WUJlTFXmRrZAU1nsVUDvL6$...` |
| Firma Bitácora (`hash_sha256`) | `50f0b98e1bbd4e422204a6225c2309bf2fc39863981c0028390e8a14bc0a3a06` |

## 2. Cuenta de Administrador (también accede a Django Admin `/admin/`)

| Campo | Valor |
| :--- | :--- |
| Correo electrónico / usuario | `admin@festivalvallenato.com` |
| Número de documento | `1065000111` |
| Contraseña | `AdminFestival2027*` |
| Rol | Administrador (`is_staff=True`, `is_superuser=True`) |
| `password_hash` | `pbkdf2_sha256$1500000$sUPb6qjGg669CoRNY6DenN$...` |
| Firma Bitácora (`hash_sha256`) | `68f44514976aa0b77bd620732d6949cb28e33d66ac345ab67754250ca6c7011c` |

## 3. Cómo iniciar sesión

- Ruta: `http://127.0.0.1:8000/usuarios/login/`
- Se puede ingresar con el **correo** o con el **número de documento** más la contraseña.
- Django Admin (solo administrador): `http://127.0.0.1:8000/admin/`

## 4. Recrear las cuentas en otro entorno

```bash
./env_django/bin/python manage.py migrate
./env_django/bin/python manage.py shell
```

```python
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

crear('votante@festivalvallenato.com', '1065888999', 'Vallenato2027*', 'votante', False)
crear('admin@festivalvallenato.com', '1065000111', 'AdminFestival2027*', 'administrador', True)
```

## 5. Seguridad aplicada a estas cuentas

- Contraseñas cifradas con **PBKDF2-HMAC-SHA256** (1.500.000 iteraciones, sal aleatoria); nunca en texto plano.
- Cada evento queda en la tabla `bitacora` con IP de origen y firma de integridad **SHA-256**.
- Bloqueo temporal de 15 minutos tras 5 intentos fallidos de inicio de sesión.