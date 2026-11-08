"""Configuración del usuario.

Desviación del estándar (§4, `.env` en la raíz de la instalación): esto es una
aplicación de escritorio instalada en /usr con un .deb, sin secretos, y cada
persona de la máquina tiene sus preferencias. Por eso vive en
~/.config/picphotoviewer/config.ini (XDG), con los defaults acá. Prioridad:
variable de entorno PPV_<CLAVE> > config.ini > default.
"""
import configparser
import os

DIR_CONFIG = os.path.join(
    os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "picphotoviewer")
DIR_DATOS = os.path.join(
    os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "picphotoviewer")
DIR_CACHE = os.path.join(
    os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "picphotoviewer")
ARCHIVO = os.path.join(DIR_CONFIG, "config.ini")

DEFAULTS = {
    "editor": "",                 # vacío = el primero que exista de EDITORES_CONOCIDOS
    "segundos_presentacion": "4",
    "opacidad_fondo": "0.72",     # 0..1, qué tanto se oscurece el escritorio detrás
    "buscar_actualizaciones": "si",
    "ultima_busqueda": "0",       # epoch de la última consulta a GitHub
    "version_ignorada": "",       # «no volver a avisar de esta versión»
    "preguntar_predeterminado": "si",   # «no» = el usuario pidió no volver a preguntar
    "ultima_pregunta_predeterminado": "0",
}

EDITORES_CONOCIDOS = ["gimp", "pinta", "krita", "kolourpaint", "drawing", "darktable"]


def _leer():
    cp = configparser.ConfigParser()
    cp.read(ARCHIVO, encoding="utf-8")
    if not cp.has_section("general"):
        cp.add_section("general")
    return cp


def get(clave):
    env = os.environ.get("PPV_" + clave.upper())
    if env is not None:
        return env
    return _leer().get("general", clave, fallback=DEFAULTS.get(clave, ""))


def get_float(clave):
    try:
        return float(get(clave))
    except ValueError:
        return float(DEFAULTS[clave])


def set(clave, valor):
    cp = _leer()
    cp.set("general", clave, str(valor))
    os.makedirs(DIR_CONFIG, exist_ok=True)
    tmp = ARCHIVO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        cp.write(f)
    os.replace(tmp, ARCHIVO)


def version():
    """Versión instalada: el archivo VERSION que viaja junto al código."""
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        with open(os.path.join(raiz, "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "0.0.0"
