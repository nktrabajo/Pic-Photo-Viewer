"""Lectura y escritura del fondo de GNOME (gsettings org.gnome.desktop.background).

Hecho relevado en la máquina de dev (GNOME 48.7, 2026-11-08): GNOME tiene UNA
sola imagen para todo el escritorio. Con `picture-options = 'spanned'` la estira
al rectángulo que encierra todas las pantallas (mutter, meta-background.c,
caso SPANNED: el área de textura es el tamaño total de la pantalla, con el
origen corrido al de cada monitor). Así se arma «un fondo por pantalla».
"""
import os
import re
import subprocess
from urllib.parse import quote, unquote, urlparse

ESQUEMA = "org.gnome.desktop.background"

# modo de PicPhotoViewer <-> picture-options de GNOME
MODO_A_GNOME = {"rellenar": "zoom", "ajustar": "scaled", "centrar": "centered",
                "estirar": "stretched", "mosaico": "wallpaper"}
GNOME_A_MODO = {v: k for k, v in MODO_A_GNOME.items()}
GNOME_A_MODO["spanned"] = "estirar"


def _gsettings(*args):
    r = subprocess.run(["gsettings", *args], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"gsettings {' '.join(args)} falló")
    return r.stdout.strip()


def leer(clave, esquema=ESQUEMA):
    valor = _gsettings("get", esquema, clave)
    if valor.startswith("'") and valor.endswith("'"):
        valor = valor[1:-1]
    return valor


def escribir(clave, valor, esquema=ESQUEMA):
    _gsettings("set", esquema, clave, valor)


def ruta_a_uri(ruta):
    return "file://" + quote(os.path.abspath(ruta))


def uri_a_ruta(uri):
    if not uri:
        return None
    if uri.startswith("/"):
        return uri
    p = urlparse(uri)
    if p.scheme != "file":
        return None
    return unquote(p.path)


def modo_oscuro():
    try:
        return leer("color-scheme", "org.gnome.desktop.interface") == "prefer-dark"
    except Exception:
        return False


def fondo_actual():
    """(ruta de imagen visible, picture-options, color de relleno).

    Si el fondo es un XML de GNOME (fondos que cambian con la hora), se toma el
    primer <file> que nombra: no se puede reproducir la animación, pero el
    escritorio queda con una de sus imágenes en vez de negro."""
    try:
        clave = "picture-uri-dark" if modo_oscuro() else "picture-uri"
        ruta = uri_a_ruta(leer(clave)) or uri_a_ruta(leer("picture-uri"))
        opciones = leer("picture-options")
        color = leer("primary-color")
    except Exception:
        return None, "zoom", "#000000"
    if ruta and ruta.lower().endswith(".xml"):
        ruta = primera_imagen_xml(ruta)
    if ruta and not os.path.isfile(ruta):
        ruta = None
    return ruta, opciones, color


def primera_imagen_xml(ruta_xml):
    try:
        with open(ruta_xml, encoding="utf-8", errors="replace") as f:
            texto = f.read()
    except OSError:
        return None
    for m in re.finditer(r"<file>\s*([^<]+?)\s*</file>", texto):
        cand = m.group(1)
        if os.path.isfile(cand):
            return cand
    # formato <file><size ...>ruta</size></file>
    m = re.search(r"<size[^>]*>\s*([^<]+?)\s*</size>", texto)
    return m.group(1) if m and os.path.isfile(m.group(1)) else None


def aplicar(ruta_imagen, opciones):
    uri = ruta_a_uri(ruta_imagen)
    escribir("picture-options", opciones)
    escribir("picture-uri", uri)
    escribir("picture-uri-dark", uri)  # sin esto, en modo oscuro no cambia nada
