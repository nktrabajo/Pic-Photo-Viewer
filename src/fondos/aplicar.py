"""Aplicar una imagen como fondo de una, varias o todas las pantallas.

Cómo se conservan las pantallas que NO se eligieron (lo difícil de esto):
1. Si el fondo actual de GNOME es el compuesto que dejó PicPhotoViewer y el
   lienzo no cambió de tamaño → se copian sus píxeles tal cual (lo más fiel).
2. Si no, y el estado guardado tiene qué había en esa pantalla → se vuelve a
   pintar desde esa imagen (pasa al cambiar la disposición de los monitores).
3. Si tampoco → se pinta el fondo actual de GNOME con su modo (el de fábrica,
   o uno que puso otro programa).

Estado en ~/.local/share/picphotoviewer/fondos.json. Las imágenes se copian a
~/.local/share/picphotoviewer/fondos/ para que el fondo no desaparezca si la
foto original se borra o vive en un disco que se desmonta.
"""
import glob
import json
import os
import shutil
import time

from PySide6.QtCore import QRect
from PySide6.QtGui import QImage

from core import config
from core.idioma import tr
from core.logger import get_logger
from fondos import componer as comp
from fondos import gnome

log = get_logger()

DIR_FONDOS = os.path.join(config.DIR_DATOS, "fondos")
ARCHIVO_ESTADO = os.path.join(config.DIR_DATOS, "fondos.json")


def leer_estado():
    try:
        with open(ARCHIVO_ESTADO, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _guardar_estado(estado):
    os.makedirs(config.DIR_DATOS, exist_ok=True)
    tmp = ARCHIVO_ESTADO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ARCHIVO_ESTADO)


def _copiar_original(ruta):
    """Copia la foto a DIR_FONDOS (una vez por contenido) y devuelve la copia."""
    os.makedirs(DIR_FONDOS, exist_ok=True)
    if os.path.dirname(os.path.abspath(ruta)) == DIR_FONDOS:
        return ruta
    st = os.stat(ruta)
    base, ext = os.path.splitext(os.path.basename(ruta))
    destino = os.path.join(DIR_FONDOS, f"orig-{base}-{st.st_size}-{int(st.st_mtime)}{ext.lower()}")
    if not os.path.exists(destino):
        shutil.copy2(ruta, destino)
    return destino


def _cargar(ruta):
    from visor.imagenes import cargar
    img, _ = cargar(ruta)
    return img


def _limpiar(estado):
    """Borra de DIR_FONDOS lo que ya no usa ningún fondo (solo archivos nuestros)."""
    en_uso = {estado.get("compuesto")}
    en_uso |= {e.get("imagen") for e in estado.get("pantallas", {}).values()}
    for p in glob.glob(os.path.join(DIR_FONDOS, "*")):
        if p not in en_uso:
            try:
                os.remove(p)
            except OSError:
                pass


def aplicar(ruta, seleccion, modo="rellenar", extendida=False, pantallas=None, lienzo=None):
    """Pone `ruta` de fondo en las pantallas cuyo nombre está en `seleccion`.

    Devuelve la ruta del archivo que quedó configurado en GNOME."""
    if modo not in comp.MODOS:
        raise ValueError(modo)
    if pantallas is None:
        pantallas, lienzo = comp.pantallas_actuales()
    if not pantallas:
        raise RuntimeError(tr("No se detectó ninguna pantalla"))
    seleccion = [p.nombre for p in pantallas if p.nombre in set(seleccion)]
    if not seleccion:
        raise ValueError(tr("No se eligió ninguna pantalla"))

    copia = _copiar_original(ruta)
    estado = leer_estado()
    por_pantalla = dict(estado.get("pantallas", {}))

    # Una sola pantalla en el sistema: fondo normal, sin componer (mejor calidad).
    if len(pantallas) == 1:
        gnome.aplicar(copia, gnome.MODO_A_GNOME[modo])
        estado = {"pantallas": {pantallas[0].nombre: {"imagen": copia, "modo": modo}},
                  "compuesto": copia, "lienzo": [lienzo.width(), lienzo.height()]}
        _guardar_estado(estado)
        _limpiar(estado)
        log.info("Fondo aplicado", {"imagen": ruta, "pantallas": seleccion, "modo": modo})
        return copia

    actual, opciones_actuales, color = gnome.fondo_actual()
    es_nuestro = actual is not None and actual == estado.get("compuesto")
    previo = None
    if es_nuestro and estado.get("lienzo") == [lienzo.width(), lienzo.height()]:
        previo = QImage(actual)

    asign = {}
    # pantallas elegidas
    grupo = None
    if extendida and len(seleccion) > 1:
        grupo = QRect()
        for p in pantallas:
            if p.nombre in seleccion:
                grupo = grupo.united(p.rect)
    for p in pantallas:
        if p.nombre in seleccion:
            if grupo is not None:
                asign[p.nombre] = ("grupo", (copia, modo, grupo))
                por_pantalla[p.nombre] = {"imagen": copia, "modo": modo,
                                          "grupo": [grupo.x(), grupo.y(), grupo.width(), grupo.height()]}
            else:
                asign[p.nombre] = ("imagen", (copia, modo))
                por_pantalla[p.nombre] = {"imagen": copia, "modo": modo}
        elif previo is not None and not previo.isNull():
            asign[p.nombre] = ("previo", None)
        elif p.nombre in por_pantalla and os.path.isfile(por_pantalla[p.nombre].get("imagen", "")):
            e = por_pantalla[p.nombre]
            if e.get("grupo"):
                g = QRect(*e["grupo"])
                asign[p.nombre] = ("grupo", (e["imagen"], e["modo"], g))
            else:
                asign[p.nombre] = ("imagen", (e["imagen"], e["modo"]))
        elif actual:
            # 3. el fondo que había, pintado como lo pintaba GNOME
            base = _copiar_original(actual) if not actual.startswith(DIR_FONDOS) else actual
            if opciones_actuales == "spanned":
                asign[p.nombre] = ("grupo", (base, "estirar", lienzo))
                por_pantalla[p.nombre] = {"imagen": base, "modo": "estirar",
                                          "grupo": [0, 0, lienzo.width(), lienzo.height()]}
            else:
                m = gnome.GNOME_A_MODO.get(opciones_actuales, "rellenar")
                asign[p.nombre] = ("imagen", (base, m))
                por_pantalla[p.nombre] = {"imagen": base, "modo": m}

    imagen = comp.componer(lienzo, pantallas, asign, previo=previo, color=color, cargar=_cargar)
    os.makedirs(DIR_FONDOS, exist_ok=True)
    # nombre nuevo cada vez: con el mismo nombre GNOME no recarga la imagen
    destino = os.path.join(DIR_FONDOS, f"compuesto-{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 10**9:09d}.jpg")
    if not imagen.save(destino, "JPG", 95):
        raise RuntimeError(tr("No se pudo guardar {destino}", destino=destino))
    gnome.aplicar(destino, "spanned")

    vigentes = {p.nombre for p in pantallas}
    estado = {"compuesto": destino, "lienzo": [lienzo.width(), lienzo.height()],
              "pantallas": {k: v for k, v in por_pantalla.items() if k in vigentes}}
    _guardar_estado(estado)
    _limpiar(estado)
    log.info("Fondo aplicado", {"imagen": ruta, "pantallas": seleccion, "modo": modo,
                                "extendida": bool(grupo), "lienzo": estado["lienzo"]})
    return destino
