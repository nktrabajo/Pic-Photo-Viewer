"""Ventana «Poner como fondo de escritorio»: diagrama de las pantallas con su
posición y orientación reales; clic para elegir una o varias."""
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QVBoxLayout, QWidget)

from core.idioma import tr
from fondos import aplicar as ap
from fondos import componer as comp
from visor.imagenes import cargar

ACENTO = QColor("#3d8ee6")


class Diagrama(QWidget):
    cambio = Signal()

    def __init__(self, pantallas, lienzo, miniatura, previas, parent=None):
        super().__init__(parent)
        self.pantallas = pantallas
        self.lienzo = lienzo
        self.miniatura = miniatura          # QImage reducido de la foto elegida
        self.previas = previas              # {nombre: QImage} lo que muestra hoy cada pantalla
        self.seleccion = set()
        self.modo = "rellenar"
        self.extendida = False
        self.setMinimumSize(640, 300)
        self.setMouseTracking(True)
        self._hover = None
        self._rects = {}

    # -- geometría del dibujo
    def _calcular(self):
        margen = 24
        aw, ah = self.width() - 2 * margen, self.height() - 2 * margen
        # se escala sobre el rectángulo que ENCIERRA las pantallas, no el lienzo
        caja = QRectF()
        for p in self.pantallas:
            caja = caja.united(QRectF(p.rect))
        esc = min(aw / caja.width(), ah / caja.height())
        ox = margen + (aw - caja.width() * esc) / 2 - caja.x() * esc
        oy = margen + (ah - caja.height() * esc) / 2 - caja.y() * esc
        self._esc, self._ox, self._oy = esc, ox, oy
        self._rects = {}
        for p in self.pantallas:
            r = p.rect
            self._rects[p.nombre] = QRectF(ox + r.x() * esc, oy + r.y() * esc,
                                           r.width() * esc, r.height() * esc).adjusted(3, 3, -3, -3)

    def _grupo_vista(self):
        caja = QRectF()
        for n in self.seleccion:
            caja = caja.united(self._rects[n].adjusted(-3, -3, 3, 3))
        return caja

    def paintEvent(self, _):
        self._calcular()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        grupo = self._grupo_vista() if (self.extendida and len(self.seleccion) > 1) else None
        for i, pant in enumerate(self.pantallas, 1):
            r = self._rects[pant.nombre]
            sel = pant.nombre in self.seleccion
            camino = QPainterPath()
            camino.addRoundedRect(r, 6, 6)
            p.save()
            p.setClipPath(camino)
            p.fillRect(r, QColor("#1b1b1d"))
            if sel and not self.miniatura.isNull():
                area = grupo if grupo is not None else r
                p.drawImage(comp.rect_destino(self.miniatura.width(), self.miniatura.height(),
                                              area.toRect(), self.modo if self.modo != "mosaico" else "rellenar"),
                            self.miniatura)
            elif pant.nombre in self.previas and not self.previas[pant.nombre].isNull():
                p.setOpacity(0.55)
                p.drawImage(r, self.previas[pant.nombre])
                p.setOpacity(1)
            p.restore()
            # borde
            if sel:
                p.setPen(QPen(ACENTO, 4))
            elif self._hover == pant.nombre:
                p.setPen(QPen(QColor("#9aa0a6"), 2))
            else:
                p.setPen(QPen(QColor("#5f6368"), 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r, 6, 6)
            # número y datos
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ACENTO if sel else QColor(0, 0, 0, 170))
            c = QPointF(r.center().x(), r.center().y() - 10)
            p.drawEllipse(c, 18, 18)
            f = QFont(self.font())
            f.setBold(True)
            f.setPointSize(13)
            p.setFont(f)
            p.setPen(QColor("white"))
            p.drawText(QRectF(c.x() - 18, c.y() - 18, 36, 36), Qt.AlignmentFlag.AlignCenter, str(i))
            f.setBold(False)
            f.setPointSize(9)
            p.setFont(f)
            texto = f"{pant.nombre}\n{pant.descripcion}" + (tr("  ·  principal") if pant.principal else "")
            caja = QRectF(r.x() + 4, c.y() + 20, r.width() - 8, 40)
            p.setPen(QColor(0, 0, 0, 200))
            p.drawText(caja.translated(1, 1), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, texto)
            p.setPen(QColor("white"))
            p.drawText(caja, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, texto)
            if sel:  # palomita
                p.setBrush(ACENTO)
                p.setPen(Qt.PenStyle.NoPen)
                cc = QPointF(r.right() - 16, r.top() + 16)
                p.drawEllipse(cc, 11, 11)
                p.setPen(QPen(QColor("white"), 2.5))
                p.drawPolyline([cc + QPointF(-5, 0), cc + QPointF(-1, 4), cc + QPointF(5, -4)])
        p.end()

    def _en(self, pos):
        for n, r in self._rects.items():
            if r.contains(QPointF(pos)):
                return n
        return None

    def mouseMoveEvent(self, e):
        h = self._en(e.position())
        if h != self._hover:
            self._hover = h
            self.setCursor(Qt.CursorShape.PointingHandCursor if h else Qt.CursorShape.ArrowCursor)
            self.update()

    def mousePressEvent(self, e):
        n = self._en(e.position())
        if n:
            self.seleccion ^= {n}
            self.update()
            self.cambio.emit()


class DialogoFondo(QDialog):
    def __init__(self, ruta, parent=None):
        super().__init__(parent)
        self.ruta = ruta
        self.resultado = None
        self.setWindowTitle(tr("Poner como fondo de escritorio"))
        self.setModal(True)
        self.resize(820, 540)

        self.pantallas, self.lienzo = comp.pantallas_actuales()
        mini, _ = cargar(ruta, maximo=_tam(900))
        previas = _previas_actuales(self.pantallas, self.lienzo)

        cab = QLabel(tr("Elige en qué pantallas va esta imagen. Clic en una pantalla para marcarla o desmarcarla."))
        cab.setWordWrap(True)
        self.diagrama = Diagrama(self.pantallas, self.lienzo, mini, previas)
        prim = [p.nombre for p in self.pantallas if p.principal] or [self.pantallas[0].nombre]
        self.diagrama.seleccion = set(prim)
        self.diagrama.cambio.connect(self._actualizar)

        self.cmb_modo = QComboBox()
        for m in comp.MODOS:
            self.cmb_modo.addItem(tr(comp.NOMBRES_MODO[m]), m)
        self.cmb_modo.currentIndexChanged.connect(self._actualizar)
        self.chk_ext = QCheckBox(tr("Una sola imagen extendida sobre las pantallas elegidas"))
        self.chk_ext.toggled.connect(self._actualizar)

        b_todas = QPushButton(tr("Todas"))
        b_todas.clicked.connect(lambda: self._marcar(True))
        b_ninguna = QPushButton(tr("Ninguna"))
        b_ninguna.clicked.connect(lambda: self._marcar(False))
        self.b_aplicar = QPushButton(tr("Aplicar"))
        self.b_aplicar.setDefault(True)
        self.b_aplicar.clicked.connect(self._aplicar)
        b_cancelar = QPushButton(tr("Cancelar"))
        b_cancelar.clicked.connect(self.reject)

        fila = QHBoxLayout()
        fila.addWidget(QLabel(tr("Ajuste:")))
        fila.addWidget(self.cmb_modo)
        fila.addSpacing(16)
        fila.addWidget(self.chk_ext)
        fila.addStretch()

        botones = QHBoxLayout()
        botones.addWidget(b_todas)
        botones.addWidget(b_ninguna)
        botones.addStretch()
        botones.addWidget(b_cancelar)
        botones.addWidget(self.b_aplicar)

        lay = QVBoxLayout(self)
        lay.addWidget(cab)
        lay.addWidget(self.diagrama, 1)
        lay.addLayout(fila)
        lay.addLayout(botones)
        self._actualizar()

    def _marcar(self, todas):
        self.diagrama.seleccion = {p.nombre for p in self.pantallas} if todas else set()
        self._actualizar()

    def _actualizar(self):
        self.diagrama.modo = self.cmb_modo.currentData()
        self.diagrama.extendida = self.chk_ext.isChecked()
        self.chk_ext.setEnabled(len(self.diagrama.seleccion) > 1)
        self.b_aplicar.setEnabled(bool(self.diagrama.seleccion))
        self.diagrama.update()

    def _aplicar(self):
        try:
            self.setCursor(Qt.CursorShape.WaitCursor)
            self.resultado = ap.aplicar(self.ruta, self.diagrama.seleccion, self.cmb_modo.currentData(),
                                        self.chk_ext.isChecked() and self.chk_ext.isEnabled(),
                                        self.pantallas, self.lienzo)
        except Exception as e:  # se muestra al usuario y queda en el log
            ap.log.error("No se pudo aplicar el fondo", {"imagen": self.ruta, "error": str(e)})
            self.unsetCursor()
            QMessageBox.critical(self, tr("Fondo de escritorio"), tr("No se pudo aplicar el fondo:\n{error}", error=e))
            return
        self.accept()


def _tam(lado):
    from PySide6.QtCore import QSize
    return QSize(lado, lado)


def _previas_actuales(pantallas, lienzo):
    """Lo que muestra hoy cada pantalla, para dibujarlo apagado en el diagrama."""
    from fondos import gnome
    out = {}
    try:
        actual, opciones, _ = gnome.fondo_actual()
        if not actual:
            return out
        img, _ = cargar(actual, maximo=_tam(1600))
        if img.isNull():
            return out
        if opciones == "spanned":
            sx, sy = img.width() / lienzo.width(), img.height() / lienzo.height()
            for p in pantallas:
                r = p.rect
                out[p.nombre] = img.copy(int(r.x() * sx), int(r.y() * sy),
                                         max(1, int(r.width() * sx)), max(1, int(r.height() * sy)))
        else:
            for p in pantallas:
                out[p.nombre] = img
    except Exception:
        pass
    return out


def elegir_y_aplicar(ruta, parent=None):
    """Punto de entrada: con una sola pantalla no hay nada que elegir."""
    pantallas, lienzo = comp.pantallas_actuales()
    if len(pantallas) <= 1:
        return ap.aplicar(ruta, [p.nombre for p in pantallas], "rellenar",
                          pantallas=pantallas, lienzo=lienzo)
    d = DialogoFondo(ruta, parent)
    return d.resultado if d.exec() == QDialog.DialogCode.Accepted else None
