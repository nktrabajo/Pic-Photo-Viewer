"""Fondo de la pantalla de inicio de sesión (GDM), lado usuario.

GNOME 48 ya no tiene fondo de bloqueo propio (la pantalla de bloqueo muestra el
fondo del escritorio difuminado); lo que sí se puede cambiar es el de GDM,
que se ve al encender, al cerrar sesión y al cambiar de usuario. Decidido con
el usuario el 2026-11-08. El trabajo de root lo hace
/usr/libexec/picphotoviewer/picphotoviewer-gdm vía pkexec; acá solo se
convierte la foto a un JPEG razonable y se lo pasa.
"""
import os
import subprocess
import tempfile

from core import config
from core.idioma import tr
from core.logger import get_logger

log = get_logger()
AYUDANTE = "/usr/libexec/picphotoviewer/picphotoviewer-gdm"
LADO_MAXIMO = 3840


class ErrorGdm(Exception):
    pass


def disponible():
    return os.path.isfile(AYUDANTE)


def _pkexec(*args):
    r = subprocess.run(["pkexec", AYUDANTE, *args], capture_output=True, text=True)
    if r.returncode in (126, 127):  # 126 = cancelado en el diálogo, 127 = sin autorización
        raise ErrorGdm("cancelado")
    if r.returncode != 0:
        raise ErrorGdm(r.stderr.strip() or tr("el ayudante falló"))
    return r.stdout.strip()


def aplicar(ruta):
    from PIL import Image, ImageOps
    os.makedirs(config.DIR_CACHE, exist_ok=True)
    with Image.open(ruta) as img:
        img = ImageOps.exif_transpose(img)
        img.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
        img = img.convert("RGB")
        fd, tmp = tempfile.mkstemp(prefix="gdm-", suffix=".jpg", dir=config.DIR_CACHE)
        os.close(fd)
        img.save(tmp, "JPEG", quality=92)
    try:
        os.chmod(tmp, 0o644)
        _pkexec("aplicar", tmp)
    finally:
        os.remove(tmp)
    log.info("Fondo de GDM aplicado", {"imagen": ruta})


def restaurar():
    _pkexec("restaurar")
    log.info("Fondo de GDM restaurado al original")
