"""Acciones sobre el archivo: rotar, papelera, editor, carpeta, visor predeterminado.

Todo lo que toca el disco o lanza otro programa vive acá, fuera de la ventana,
para poder probarlo sin UI.
"""
import os
import shutil
import subprocess

from core import config
from core.logger import get_logger

log = get_logger()

_JPEG = {".jpg", ".jpeg", ".jpe", ".jfif"}


class ErrorAccion(Exception):
    pass


def rotar(ruta, grados):
    """Rota el ARCHIVO (no solo la vista), 90 o -90 grados.

    JPEG: con `exiftran`, que es sin pérdida y además corrige la etiqueta de
    orientación EXIF (con `jpegtran` a secas, una foto con orientación EXIF ≠ 1
    quedaría rotada dos veces). Resto: PIL, conservando formato; PNG/BMP/TIFF
    son sin pérdida, WEBP se guarda sin pérdida si el original lo era.
    """
    if grados not in (90, -90):
        raise ValueError(grados)
    ext = os.path.splitext(ruta)[1].lower()
    if ext in _JPEG:
        exiftran = shutil.which("exiftran")
        if not exiftran:
            raise ErrorAccion("Falta el programa «exiftran» (sudo apt install exiftran).")
        bandera = "-9" if grados == 90 else "-2"
        r = subprocess.run([exiftran, "-i", "-p", bandera, ruta],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise ErrorAccion(f"exiftran falló: {r.stderr.strip()}")
    else:
        _rotar_pil(ruta, grados)
    log.info("Imagen rotada", {"archivo": ruta, "grados": grados})


def _rotar_pil(ruta, grados):
    from PIL import Image, ImageOps
    with Image.open(ruta) as img:
        if getattr(img, "n_frames", 1) > 1:
            raise ErrorAccion("No se rotan imágenes animadas.")
        fmt = img.format
        info = dict(img.info)
        img = ImageOps.exif_transpose(img)  # dejar la orientación aplicada en píxeles
        # PIL rota en sentido antihorario con valores positivos
        nueva = img.rotate(-grados, expand=True)
    kw = {}
    if "icc_profile" in info:
        kw["icc_profile"] = info["icc_profile"]
    if fmt == "WEBP":
        kw["lossless"] = bool(info.get("lossless", False))
        kw["quality"] = 95
    tmp = ruta + ".ppv-tmp"
    nueva.save(tmp, format=fmt, **kw)
    shutil.copymode(ruta, tmp)
    os.replace(tmp, ruta)


def mandar_a_papelera(ruta):
    from PySide6.QtCore import QFile
    ok = QFile.moveToTrash(ruta)
    if isinstance(ok, tuple):  # PySide devuelve (bool, ruta_en_papelera)
        ok = ok[0]
    if not ok:
        r = subprocess.run(["gio", "trash", ruta], capture_output=True, text=True)
        if r.returncode != 0:
            raise ErrorAccion(f"No se pudo mandar a la papelera: {r.stderr.strip()}")
    log.info("Imagen enviada a la papelera", {"archivo": ruta})


def editor_disponible():
    elegido = config.get("editor").strip()
    if elegido:
        return elegido if shutil.which(elegido.split()[0]) else None
    for e in config.EDITORES_CONOCIDOS:
        if shutil.which(e):
            return e
    return None


def abrir_con_editor(ruta):
    editor = editor_disponible()
    if editor:
        subprocess.Popen(editor.split() + [ruta], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return editor
    # sin editor conocido: que el sistema ofrezca su «Abrir con»
    subprocess.Popen(["xdg-open", ruta], start_new_session=True, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
    return None


def mostrar_en_carpeta(ruta):
    """Abre el gestor de archivos con la foto seleccionada (D-Bus FileManager1,
    que Nautilus implementa); si no responde, abre solo la carpeta."""
    from urllib.parse import quote
    uri = "file://" + quote(os.path.abspath(ruta))
    r = subprocess.run(
        ["gdbus", "call", "--session", "--dest", "org.freedesktop.FileManager1",
         "--object-path", "/org/freedesktop/FileManager1",
         "--method", "org.freedesktop.FileManager1.ShowItems", f"['{uri}']", ""],
        capture_output=True, text=True, timeout=5)
    if r.returncode != 0:
        subprocess.Popen(["xdg-open", os.path.dirname(ruta)], start_new_session=True)


TIPOS_MIME = [
    "image/jpeg", "image/png", "image/gif", "image/bmp", "image/webp", "image/tiff",
    "image/heic", "image/heif", "image/avif", "image/jxl", "image/x-icon",
    "image/svg+xml", "image/x-tga", "image/vnd.adobe.photoshop", "image/x-xcf",
    "image/x-portable-pixmap", "image/x-portable-graymap", "image/x-portable-bitmap",
]


def hacer_predeterminado():
    """Visor predeterminado para el usuario actual (no se puede desde el .deb:
    la asociación es por usuario, en ~/.config/mimeapps.list)."""
    # Probado 2026-11-08: si la carpeta de config no existe, xdg-mime falla a
    # medias (escribe solo parte de los tipos) y devuelve error.
    os.makedirs(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), exist_ok=True)
    r = subprocess.run(["xdg-mime", "default", "picphotoviewer.desktop", *TIPOS_MIME],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise ErrorAccion(r.stderr.strip() or "xdg-mime falló")
    log.info("PicPhotoViewer quedó como visor predeterminado", {"tipos": len(TIPOS_MIME)})


DIAS_ENTRE_PREGUNTAS = 7


def debe_preguntar_predeterminado(ahora=None):
    """¿Ofrecer «usar como visor predeterminado» al abrir? Una vez, y si dijo
    «Ahora no», de nuevo a los 7 días; nunca si dijo «No volver a preguntar»."""
    import time
    if config.get("preguntar_predeterminado").lower() not in ("si", "sí", "1", "true", "yes"):
        return False
    try:
        ultima = float(config.get("ultima_pregunta_predeterminado") or 0)
    except ValueError:
        ultima = 0
    if (ahora or time.time()) - ultima < DIAS_ENTRE_PREGUNTAS * 86400:
        return False
    return not es_predeterminado()


def es_predeterminado():
    r = subprocess.run(["xdg-mime", "query", "default", "image/jpeg"],
                       capture_output=True, text=True)
    return r.stdout.strip() == "picphotoviewer.desktop"
