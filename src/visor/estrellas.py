"""Estrellas compatibles con Picasa: archivo `.picasa.ini` de cada carpeta.

Formato que escribía Picasa (y que se respeta para que las carpetas viejas
traigan sus estrellas y Picasa en Windows vea las nuevas):

    [foto.jpg]
    star=yes

Se toca solo la clave `star` de la sección de la foto; el resto del archivo
(caras, rotaciones, álbumes de Picasa) se conserva tal cual.
"""
import configparser
import os

NOMBRE = ".picasa.ini"


def _parser():
    cp = configparser.RawConfigParser(strict=False, interpolation=None,
                                      delimiters=("=",), comment_prefixes=(";", "#"))
    cp.optionxform = str  # Picasa distingue mayúsculas en las claves
    return cp


def _leer(carpeta):
    cp = _parser()
    ruta = os.path.join(carpeta, NOMBRE)
    if os.path.isfile(ruta):
        # Picasa en Windows escribía en ANSI; latin-1 nunca falla al leer
        try:
            with open(ruta, encoding="utf-8") as f:
                cp.read_file(f)
        except UnicodeDecodeError:
            with open(ruta, encoding="latin-1") as f:
                cp.read_file(f)
    return cp


def tiene_estrella(ruta_imagen):
    carpeta, nombre = os.path.split(ruta_imagen)
    try:
        cp = _leer(carpeta)
    except (configparser.Error, OSError):
        return False
    return cp.has_section(nombre) and cp.get(nombre, "star", fallback="").lower() == "yes"


def estrellas_de_carpeta(carpeta):
    try:
        cp = _leer(carpeta)
    except (configparser.Error, OSError):
        return set()
    return {s for s in cp.sections() if cp.get(s, "star", fallback="").lower() == "yes"}


def poner_estrella(ruta_imagen, valor):
    """Devuelve el nuevo estado. Lanza OSError si la carpeta no es escribible."""
    carpeta, nombre = os.path.split(ruta_imagen)
    cp = _leer(carpeta)
    if valor:
        if not cp.has_section(nombre):
            cp.add_section(nombre)
        cp.set(nombre, "star", "yes")
    elif cp.has_section(nombre):
        cp.remove_option(nombre, "star")
        if not cp.items(nombre):
            cp.remove_section(nombre)
    ruta = os.path.join(carpeta, NOMBRE)
    if not cp.sections() and not os.path.exists(ruta):
        return valor
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        cp.write(f, space_around_delimiters=False)
    os.replace(tmp, ruta)
    return valor
