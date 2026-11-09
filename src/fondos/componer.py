"""Arma la imagen única que GNOME reparte entre las pantallas ('spanned').

Funciones puras sobre QImage/QPainter: no tocan gsettings ni la pantalla, así
que se prueban píxel por píxel en `tools/pruebas/prueba_fondos.py`.
"""
from dataclasses import dataclass

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter

from core.idioma import N

MODOS = ["rellenar", "ajustar", "centrar", "estirar", "mosaico"]
# N(): se traducen al mostrarlos (fondos/dialogo.py)
NOMBRES_MODO = {"rellenar": N("Rellenar"), "ajustar": N("Ajustar"), "centrar": N("Centrar"),
                "estirar": N("Estirar"), "mosaico": N("Mosaico")}


@dataclass
class Pantalla:
    nombre: str          # conector: HDMI-1-0, eDP-1… (estable entre sesiones)
    rect: QRect          # en coordenadas del lienzo (origen 0,0 = esquina del escritorio)
    principal: bool = False
    modelo: str = ""

    @property
    def descripcion(self):
        return f"{self.rect.width()} × {self.rect.height()}"


def pantallas_actuales():
    """Las pantallas según Qt, con el origen llevado a la esquina del escritorio
    virtual (en X11 coincide con lo que usa mutter para 'spanned')."""
    from PySide6.QtGui import QGuiApplication
    screens = QGuiApplication.screens()
    if not screens:
        return [], QRect()
    virtual = screens[0].virtualGeometry()
    # en X11 el escritorio siempre arranca en 0,0; se incluye para no correr nada
    virtual = virtual.united(QRect(0, 0, 1, 1))
    prim = QGuiApplication.primaryScreen()
    out = []
    for s in screens:
        g = s.geometry().translated(-virtual.x(), -virtual.y())
        out.append(Pantalla(s.name(), g, s is prim, (s.manufacturer() + " " + s.model()).strip()))
    out.sort(key=lambda p: (p.rect.x(), p.rect.y()))
    lienzo = QRect(0, 0, virtual.width(), virtual.height())
    return out, lienzo


def rect_destino(img_w, img_h, area, modo):
    """Dónde cae la imagen dentro de `area` según el modo (QRectF)."""
    aw, ah = area.width(), area.height()
    if modo == "estirar":
        return QRectF(area)
    if modo == "centrar":
        w, h = img_w, img_h
    else:
        esc = (max if modo == "rellenar" else min)(aw / img_w, ah / img_h)
        w, h = img_w * esc, img_h * esc
    return QRectF(area.x() + (aw - w) / 2, area.y() + (ah - h) / 2, w, h)


def pintar(painter, img, area, modo, recorte=None):
    """Pinta `img` en `area` con `modo`, recortado a `recorte` (default: area)."""
    painter.save()
    painter.setClipRect(recorte if recorte is not None else area)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    if modo == "mosaico":
        for y in range(area.y(), area.y() + area.height(), max(1, img.height())):
            for x in range(area.x(), area.x() + area.width(), max(1, img.width())):
                painter.drawImage(x, y, img)
    else:
        painter.drawImage(rect_destino(img.width(), img.height(), area, modo), img,
                          QRectF(img.rect()))
    painter.restore()


def componer(lienzo, pantallas, asignaciones, previo=None, color="#000000", cargar=None):
    """Devuelve el QImage del tamaño del lienzo.

    asignaciones: {nombre_pantalla: ("imagen"|"previo"|"grupo", datos)}
      ("imagen", (ruta, modo))           la imagen ocupa esa pantalla sola
      ("grupo",  (ruta, modo, QRect))    parte de una imagen extendida sobre QRect
      ("previo", None)                   se copian los píxeles de `previo`
    `cargar(ruta) -> QImage` se inyecta para cachear y para las pruebas.
    """
    if cargar is None:
        cargar = QImage
    salida = QImage(lienzo.size(), QImage.Format.Format_RGB32)
    salida.fill(QColor(color) if QColor.isValidColor(color) else QColor("black"))
    cache = {}

    def img(ruta):
        if ruta not in cache:
            cache[ruta] = cargar(ruta)
        return cache[ruta]

    p = QPainter(salida)
    try:
        for pant in pantallas:
            tipo, datos = asignaciones.get(pant.nombre, ("vacio", None))
            if tipo == "previo" and previo is not None and not previo.isNull():
                p.drawImage(pant.rect, previo, pant.rect)
            elif tipo == "imagen":
                ruta, modo = datos
                i = img(ruta)
                if not i.isNull():
                    pintar(p, i, pant.rect, modo)
            elif tipo == "grupo":
                ruta, modo, area = datos
                i = img(ruta)
                if not i.isNull():
                    pintar(p, i, area, modo, recorte=pant.rect)
    finally:
        p.end()
    return salida
