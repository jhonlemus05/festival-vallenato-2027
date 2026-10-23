# Sistema Web de Votaciones · Festival de la Leyenda Vallenata 2027

Plataforma web para gestionar las votaciones del público del Festival de la Leyenda Vallenata.
Proyecto académico de la asignatura Desarrollo Web (Fundación Universitaria del Área Andina).

La plataforma sigue la jerarquía **Edición → Categoría → Votación → Opción → Voto** definida en la Entrega 1:
cada edición del Festival agrupa sus categorías, cada categoría sus votaciones (encuestas) y cada votación
sus opciones. Un votante registrado emite un solo voto por encuesta.

**Equipo:** _(nombres completos de los cuatro integrantes)_

## Tecnologías

| Componente | Tecnología |
| --- | --- |
| Backend | Python 3.12+ y Django 6.1 (patrón MVT) |
| Base de datos | MySQL 8 (driver `mysqlclient`) |
| Frontend | HTML5, CSS3, Bootstrap 5 y JavaScript |
| Configuración | Variables de entorno en un archivo `.env` (`python-dotenv`) |

## Estructura

| App | Qué contiene |
| --- | --- |
| `usuarios` | Registro, inicio y cierre de sesión, perfil, bitácora de auditoría firmada y permisos de administrador |
| `votaciones` | Ediciones, categorías, encuestas, opciones y votos; vistas públicas y votación |
| `administracion` | Panel administrativo propio (solo administradores) |
| `pr_festivalVallenato` | Configuración del proyecto (`settings.py`, rutas principales) |

## Instalación

Necesitas Python 3.12 o superior, MySQL 8 y Git.

### 1. Clonar y crear el entorno virtual

```bash
git clone https://github.com/jhonlemus05/festival-vallenato-2027.git
cd festival-vallenato-2027
python -m venv env_django
```

Activar el entorno:

- **Windows (PowerShell):** `env_django\Scripts\activate`
- **Linux / macOS:** `source env_django/bin/activate`

### 2. Instalar las dependencias

- **Windows:** `pip install -r requirements.txt` (`mysqlclient` se instala sin compilar).
- **Ubuntu:** primero las librerías para compilar `mysqlclient`, luego las dependencias:

```bash
sudo apt install mysql-server pkg-config default-libmysqlclient-dev build-essential python3-dev
pip install -r requirements.txt
```

### 3. Crear la base de datos en MySQL

Como administrador de MySQL (en Ubuntu `sudo mysql`; en Windows MySQL Shell o Workbench como `root`):

```sql
CREATE DATABASE festival_vallenato CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'festival'@'localhost' IDENTIFIED BY 'una-clave-tuya';
GRANT ALL PRIVILEGES ON festival_vallenato.* TO 'festival'@'localhost';
GRANT ALL PRIVILEGES ON test_festival_vallenato.* TO 'festival'@'localhost';
```

La segunda base la crea y borra Django al correr las pruebas.

### 4. Configurar el `.env`

Copia la plantilla y llénala:

- **Windows:** `copy .env.example .env`
- **Linux / macOS:** `cp .env.example .env`

En el `.env` pon la contraseña de MySQL en `DB_PASSWORD` y genera tu propia clave secreta:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

El `.env` tiene secretos y **no se sube al repositorio** (está en `.gitignore`).

### 5. Crear las tablas y un administrador

```bash
python manage.py migrate
python manage.py createsuperuser
```

Las migraciones crean la edición 2027 con sus categorías, encuestas y participantes iniciales.

### 6. (Opcional) Cargar datos de prueba

```bash
python manage.py cargar_datos_prueba
```

Agrega una edición 2026 finalizada, opciones para las encuestas que no tenían y votos de 12 votantes de
prueba, para que el panel administrativo tenga datos. Los votantes de prueba no tienen contraseña, así que
nadie puede iniciar sesión con ellos. Se puede correr varias veces sin duplicar nada.

### 7. Ejecutar

```bash
python manage.py runserver
```

## Rutas principales

| Ruta | Qué es | Acceso |
| --- | --- | --- |
| `/` | Inicio | Público |
| `/categorias/` | Categorías de la edición vigente | Público |
| `/ediciones/` | Todas las ediciones del Festival | Público |
| `/encuestas/<id>/votar/` | Votar en una encuesta activa | Votante con sesión |
| `/usuarios/login/` | Registro e inicio de sesión | Público |
| `/usuarios/perfil/` | Mis datos, cambio de contraseña y actividad | Votante con sesión |
| `/admin-panel/` | Panel administrativo propio | Solo administradores |
| `/admin/` | Django Admin (ediciones, categorías, encuestas, opciones, usuarios, bitácora) | Solo administradores |

## Pruebas

```bash
python manage.py test
```

Las pruebas corren contra MySQL en una base temporal (`test_festival_vallenato`).

## Seguridad

- Contraseñas con PBKDF2-SHA256 y validadores de Django; bloqueo de 15 minutos tras 5 intentos fallidos.
- Bitácora de auditoría: cada evento de acceso queda firmado con SHA-256.
- Cookies `HttpOnly` y `SameSite=Lax`, protección CSRF y cierre de sesión solo por POST.
- Panel administrativo solo para administradores (cuentas staff o perfil con rol administrador).
- `SECRET_KEY` y credenciales de MySQL fuera del código, en el `.env`.

El historial detallado de cambios está en [`BITACORA.md`](BITACORA.md).
