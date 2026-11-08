"""Botones e íconos de la barra inferior, dibujados con QPainter.

Imitan la DISPOSICIÓN y el estilo general del visor de Picasa (píldoras grises
oscuras con texto claro, flechas grandes plateadas con el «play» al centro),
pero cada ícono está dibujado acá: no se usa ningún recurso gráfico de Google.
"""
from dataclasses import dataclass, field

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath,
                           QPen, QPolygonF, QRadialGradient)


@dataclass
class Boton:
    id: str
    rect: QRectF = field(default_factory=QRectF)
    texto: str = ""
    ayuda: str = ""
    tipo: str = "pildora"        # pildora | icono | flecha_izq | flecha_der | play
    activo: bool = False         # estrella marcada, presentación corriendo
    habilitado: bool = True


def pildora(p, b, hover, presionado):
    r = b.rect
    g = QLinearGradient(r.topLeft(), r.bottomLeft())
    if not b.habilitado:
        g.setColorAt(0, QColor(70, 70, 70, 200))
        g.setColorAt(1, QColor(50, 50, 50, 200))
    elif presionado:
        g.setColorAt(0, QColor("#2a2a2a"))
        g.setColorAt(1, QColor("#3c3c3c"))
    elif hover:
        g.setColorAt(0, QColor("#6a6a6a"))
        g.setColorAt(1, QColor("#454545"))
    else:
        g.setColorAt(0, QColor("#565656"))
        g.setColorAt(1, QColor("#363636"))
    p.setPen(QPen(QColor(120, 120, 120, 220), 1))
    p.setBrush(QBrush(g))
    p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 4, 4)
    # brillo superior
    p.setPen(QPen(QColor(255, 255, 255, 40), 1))
    p.drawLine(QPointF(r.left() + 4, r.top() + 1.5), QPointF(r.right() - 4, r.top() + 1.5))
    color = QColor("#f0f0f0") if b.habilitado else QColor("#8a8a8a")
    if b.texto:
        f = QFont(p.font())
        f.setPixelSize(17 if b.texto in ('↺', '↻') else 12)
        p.setFont(f)
        p.setPen(color)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, b.texto)
    else:
        icono(p, b.id, r, color, b.activo)


def icono(p, ident, r, color, activo=False):
    c = r.center()
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    if ident in ("rot_izq", "rot_der"):
        rad = 5.5
        caja = QRectF(c.x() - rad, c.y() - rad + 0.5, rad * 2, rad * 2)
        camino = QPainterPath()
        if ident == "rot_der":
            camino.arcMoveTo(caja, 120)
            camino.arcTo(caja, 120, -290)
            fin = camino.currentPosition()
            punta = [fin + QPointF(-3.6, -1.8), fin, fin + QPointF(-0.6, -4)]
        else:
            camino.arcMoveTo(caja, 60)
            camino.arcTo(caja, 60, 290)
            fin = camino.currentPosition()
            punta = [fin + QPointF(3.6, -1.8), fin, fin + QPointF(0.6, -4)]
        p.drawPath(camino)
        p.drawPolyline(QPolygonF(punta))
    elif ident == "estrella":
        estrella(p, c, 7.5, QColor("#f4c430") if activo else color, relleno=activo)
    elif ident == "menu":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPolygon(QPolygonF([QPointF(c.x() - 5, c.y() - 2.5), QPointF(c.x() + 5, c.y() - 2.5),
                                 QPointF(c.x(), c.y() + 3.5)]))
    elif ident == "cerrar":
        d = 6
        p.setPen(QPen(color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(c.x() - d, c.y() - d), QPointF(c.x() + d, c.y() + d))
        p.drawLine(QPointF(c.x() + d, c.y() - d), QPointF(c.x() - d, c.y() + d))
    p.restore()


def estrella(p, c, radio, color, relleno=True):
    import math
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = radio if i % 2 == 0 else radio * 0.45
        pts.append(QPointF(c.x() + rr * math.cos(a), c.y() + rr * math.sin(a)))
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(color, 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(color if relleno else Qt.BrushStyle.NoBrush)
    p.drawPolygon(QPolygonF(pts))
    p.restore()


def _plateado(r, hover, presionado):
    g = QLinearGradient(r.topLeft(), r.bottomLeft())
    if presionado:
        g.setColorAt(0, QColor("#9a9a9a"))
        g.setColorAt(1, QColor("#d0d0d0"))
    else:
        alto = 30 if hover else 0
        g.setColorAt(0, QColor(min(255, 236 + alto), min(255, 236 + alto), min(255, 236 + alto)))
        g.setColorAt(0.5, QColor(185 + alto // 2, 185 + alto // 2, 185 + alto // 2))
        g.setColorAt(1, QColor(130 + alto, 130 + alto, 130 + alto))
    return QBrush(g)


def flecha(p, b, hover, presionado, izquierda):
    """Flecha gruesa plateada (anterior / siguiente)."""
    r = b.rect
    w, h = r.width(), r.height()
    cy = r.center().y()
    if izquierda:
        x0, x1 = r.right(), r.left()
    else:
        x0, x1 = r.left(), r.right()
    s = -1 if izquierda else 1
    cuerpo = h * 0.36
    cabeza = w * 0.5
    pts = [QPointF(x0, cy - cuerpo / 2), QPointF(x1 - s * cabeza, cy - cuerpo / 2),
           QPointF(x1 - s * cabeza, cy - h / 2), QPointF(x1, cy),
           QPointF(x1 - s * cabeza, cy + h / 2), QPointF(x1 - s * cabeza, cy + cuerpo / 2),
           QPointF(x0, cy + cuerpo / 2)]
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(40, 40, 40, 220), 1))
    p.setBrush(_plateado(r, hover and b.habilitado, presionado) if b.habilitado else QColor(110, 110, 110, 160))
    p.drawPolygon(QPolygonF(pts))
    p.restore()


def play(p, b, hover, presionado):
    r = b.rect
    c = r.center()
    rad = min(r.width(), r.height()) / 2
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    g = QRadialGradient(c - QPointF(0, rad * 0.4), rad * 1.3)
    alto = 25 if hover else 0
    g.setColorAt(0, QColor(min(255, 250), min(255, 250), min(255, 250)))
    g.setColorAt(0.6, QColor(190 + alto, 190 + alto, 190 + alto))
    g.setColorAt(1, QColor(120 + alto, 120 + alto, 120 + alto))
    p.setPen(QPen(QColor(40, 40, 40, 230), 1.2))
    p.setBrush(QBrush(g) if not presionado else QColor("#a0a0a0"))
    p.drawEllipse(c, rad, rad)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#2b2b2b"))
    if b.activo:  # pausa
        bw, bh = rad * 0.22, rad * 0.8
        p.drawRect(QRectF(c.x() - bw * 1.4, c.y() - bh / 2, bw, bh))
        p.drawRect(QRectF(c.x() + bw * 0.4, c.y() - bh / 2, bw, bh))
    else:
        t = rad * 0.5
        p.drawPolygon(QPolygonF([QPointF(c.x() - t * 0.6, c.y() - t), QPointF(c.x() - t * 0.6, c.y() + t),
                                 QPointF(c.x() + t, c.y())]))
    p.restore()


def dibujar(p, b, hover, presionado):
    if b.tipo == "flecha_izq":
        flecha(p, b, hover, presionado, True)
    elif b.tipo == "flecha_der":
        flecha(p, b, hover, presionado, False)
    elif b.tipo == "play":
        play(p, b, hover, presionado)
    else:
        pildora(p, b, hover, presionado)


def texto_con_sombra(p, rect, flags, texto, color=QColor("white")):
    p.setPen(QColor(0, 0, 0, 200))
    p.drawText(rect.translated(1, 1), flags, texto)
    p.setPen(color)
    p.drawText(rect, flags, texto)
