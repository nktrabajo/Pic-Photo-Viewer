"""Qué archivos son imágenes, en qué orden se recorren y cómo se cargan.

Sin dependencias de UI salvo QImage/QImageReader (QtGui funciona sin pantalla,
así que esto se prueba en `tools/pruebas/`).
"""
import os
import re

from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QImageReader

# Extensiones que se muestran. Se cruza con lo que Qt sabe leer en esta máquina
# (qt6-image-formats-plugins agrega webp/tiff/heic/avif/raw...).
_PREFERIDAS = {
    "jpg", "jpeg", "jpe", "jfif", "png", "gif", "bmp", "webp", "tif", "tiff",
    "heic", "heif", "avif", "jxl", "ico", "svg", "tga", "psd", "xcf", "pcx",
    "ppm", "pgm", "pbm", "dng", "cr2", "cr3", "nef", "arw", "orf", "rw2", "raf",
}


def extensiones_soportadas():
    qt = {bytes(f).decode().lower() for f in QImageReader.supportedImageFormats()}
    exts = (_PREFERIDAS & qt) | {"jpg", "jpeg", "png", "gif", "bmp"}
    if "jpeg" in exts:
        exts |= {"jpe", "jfif"}
    return exts


_EXTS = None


def es_imagen(ruta):
    global _EXTS
    if _EXTS is None:
        _EXTS = extensiones_soportadas()
    ext = os.path.splitext(ruta)[1][1:].lower()
    return ext in _EXTS and not os.path.basename(ruta).startswith(".")


def clave_natural(nombre):
    """'img2.jpg' antes que 'img10.jpg', sin distinguir mayúsculas."""
    return [int(t) if t.isdigit() else t.casefold() for t in re.split(r"(\d+)", nombre)]


def listar_carpeta(carpeta):
    try:
        nombres = os.listdir(carpeta)
    except OSError:
        return []
    rutas = [os.path.join(carpeta, n) for n in nombres]
    rutas = [r for r in rutas if es_imagen(r) and os.path.isfile(r)]
    rutas.sort(key=lambda r: clave_natural(os.path.basename(r)))
    return rutas


def cargar(ruta, maximo=None):
    """Carga respetando la orientación EXIF. `maximo` (QSize) reduce al leer —
    para JPEG es mucho más rápido que leer entero y escalar después."""
    lector = QImageReader(ruta)
    lector.setAutoTransform(True)
    lector.setDecideFormatFromContent(True)
    if maximo is not None:
        tam = lector.size()
        if tam.isValid():
            # el tamaño viene sin la rotación EXIF aplicada: se usa el lado mayor
            lado = max(maximo.width(), maximo.height())
            tam.scale(QSize(lado, lado), _mantener_menor())
            if tam.width() < lector.size().width():
                lector.setScaledSize(tam)
    img = lector.read()
    return img, (lector.errorString() if img.isNull() else "")


def _mantener_menor():
    from PySide6.QtCore import Qt
    return Qt.AspectRatioMode.KeepAspectRatio


def dimensiones(ruta):
    """Ancho x alto ya orientado, sin decodificar la imagen."""
    lector = QImageReader(ruta)
    lector.setAutoTransform(True)
    tam = lector.size()
    if not tam.isValid():
        return None
    from PySide6.QtGui import QImageIOHandler
    t = lector.transformation()
    if t & QImageIOHandler.Transformation.TransformationRotate90:
        tam = tam.transposed()
    return tam


def es_animada(ruta):
    lector = QImageReader(ruta)
    return lector.supportsAnimation() and lector.imageCount() > 1
