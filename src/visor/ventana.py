"""La ventana del visor: superposición a pantalla completa sobre el escritorio.

Comportamiento tomado del visor de Picasa (captura de referencia del usuario,
2026-11-08): fondo oscuro translúcido que deja ver el escritorio, la foto
centrada, el nombre con sus dimensiones debajo, la tira de fotos de la carpeta
a lo ancho, y la barra de botones al pie; X redonda en la esquina superior
derecha; clic fuera de la foto cierra.

Todo se pinta en un solo QWidget (paintEvent) con zonas de clic propias: así
la translucidez y el estilo quedan iguales en cualquier tema de GTK/Qt.
"""
import os
import shutil
import subprocess

from PySide6.QtCore import (QEasingCurve, QPointF, QRectF, QSize, Qt, QTimer,
                            QVariantAnimation)
from PySide6.QtGui import (QColor, QCursor, QFont, QFontMetrics, QGuiApplication, QImage,
                           QKeySequence, QPainter, QPainterPath, QPen, QShortcut)
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QToolTip, QWidget

from core import config
from core.idioma import tr
from core.logger import get_logger
from visor import acciones, dialogos, dibujo, estrellas, imagenes
from visor.cargador import Cargador
from visor.dibujo import Boton

log = get_logger()

PASO_ZOOM = 1.25
ZOOM_MAX = 32.0
ALTO_TIRA = 46
LADO_TILE = 40
PASO_TILE = 44
ALTO_BARRA = 24


class Visor(QWidget):
    def __init__(self, ruta_inicial, lista=None):
        super().__init__()
        self.setWindowTitle("PicPhotoViewer")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.opacidad = max(0.0, min(1.0, config.get_float("opacidad_fondo")))
        self.cargador = Cargador(self)
        self.cargador.imagen_lista.connect(self._imagen_cargada)
        self.cargador.mini_lista.connect(lambda _r: self.update(self._rect_tira().toRect()))

        ruta_inicial = os.path.abspath(ruta_inicial)
        self.lista = lista or imagenes.listar_carpeta(os.path.dirname(ruta_inicial))
        if ruta_inicial not in self.lista:
            self.lista.insert(0, ruta_inicial)
        self.indice = self.lista.index(ruta_inicial)
        self.con_estrella = estrellas.estrellas_de_carpeta(os.path.dirname(ruta_inicial))

        self.img = None            # QImage completa de la foto actual
        self.error = ""
        self.zoom = None           # None = ajustada a la pantalla
        self.centro = QPointF(0, 0)  # desplazamiento de la foto respecto del centro del área
        self._escalada = None      # (zoom, QImage) caché de la foto reducida
        self._arrastre = None
        self._movio = False
        self._hover = None
        self._presionado = None
        self.botones = []
        self.mensaje = ""
        self.tira_desplazada = None  # float: índice en el centro de la tira

        self.presentando = False
        self._timer_pres = QTimer(self, interval=int(config.get_float("segundos_presentacion") * 1000))
        self._timer_pres.timeout.connect(lambda: self.navegar(+1, ciclico=True))
        self._fundido_anterior = None
        self._anim_fundido = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=450)
        self._anim_fundido.valueChanged.connect(lambda _v: self.update())
        self._anim_fundido.finished.connect(self._fin_fundido)

        self._aparicion = 0.0
        self._anim_aparicion = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=200)
        self._anim_aparicion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_aparicion.valueChanged.connect(self._set_aparicion)

        self._anim_zoom = QVariantAnimation(self, duration=140)
        self._anim_zoom.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_zoom.valueChanged.connect(self._paso_zoom)
        self._anim_zoom.finished.connect(lambda: self.update())

        self._timer_mensaje = QTimer(self, singleShot=True, interval=2600)
        self._timer_mensaje.timeout.connect(self._borrar_mensaje)
        self._mostrar_ayuda = False

        self._crear_botones()
        self._atajos()
        self._cargar_actual()

    # ------------------------------------------------------------ arranque
    def mostrar(self):
        pantalla = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        self.setGeometry(pantalla.geometry())
        self.showFullScreen()
        self.activateWindow()
        self.raise_()
        self._anim_aparicion.start()

    def _set_aparicion(self, v):
        self._aparicion = v
        self.update()

    # ------------------------------------------------------------ datos actuales
    @property
    def ruta(self):
        return self.lista[self.indice] if self.lista else None

    def _cargar_actual(self):
        self.img = self.cargador.imagen(self.ruta)
        self.error = ""
        self.zoom = None
        self.centro = QPointF(0, 0)
        self._escalada = None
        if self.img is None:
            self.cargador.pedir(self.ruta, prioridad=10)
        # precargar vecinas
        for d in (1, -1):
            j = self.indice + d
            if 0 <= j < len(self.lista):
                self.cargador.pedir(self.lista[j])
        self._actualizar_botones()
        self.update()

    def _imagen_cargada(self, ruta, img, err):
        if ruta != self.ruta:
            return
        if img.isNull():
            self.error = err or tr("No se pudo abrir la imagen")
            log.warning("No se pudo abrir una imagen", {"archivo": ruta, "error": self.error})
        self.img = None if img.isNull() else img
        self._escalada = None
        self._actualizar_botones()
        self.update()

    # ------------------------------------------------------------ geometría
    def _rect_barra(self):
        return QRectF(0, self.height() - ALTO_BARRA - 10, self.width(), ALTO_BARRA)

    def _rect_tira(self):
        b = self._rect_barra()
        return QRectF(0, b.top() - 8 - ALTO_TIRA, self.width(), ALTO_TIRA)

    def _rect_titulo(self):
        t = self._rect_tira()
        return QRectF(0, t.top() - 24, self.width(), 22)

    def _area_foto(self):
        if self.presentando:
            return QRectF(self.rect())
        abajo = self._rect_titulo().top() - 6
        return QRectF(50, 36, self.width() - 100, max(50, abajo - 36))

    def _tam_foto(self):
        if self.img is None:
            return QSize(0, 0)
        return self.img.size()

    def zoom_ajustado(self):
        t = self._tam_foto()
        a = self._area_foto()
        if t.isEmpty():
            return 1.0
        # como Picasa: las fotos chicas no se agrandan
        return min(1.0, a.width() / t.width(), a.height() / t.height())

    def zoom_actual(self):
        return self.zoom if self.zoom is not None else self.zoom_ajustado()

    def _rect_foto(self, zoom=None):
        z = zoom if zoom is not None else self.zoom_actual()
        t = self._tam_foto()
        a = self._area_foto()
        w, h = t.width() * z, t.height() * z
        c = a.center() + self.centro
        return QRectF(c.x() - w / 2, c.y() - h / 2, w, h)

    def _limitar_centro(self):
        """La foto ampliada no se puede arrastrar más allá de sus bordes."""
        t = self._tam_foto()
        a = self._area_foto()
        z = self.zoom_actual()
        w, h = t.width() * z, t.height() * z
        mx = max(0.0, (w - a.width()) / 2)
        my = max(0.0, (h - a.height()) / 2)
        self.centro = QPointF(max(-mx, min(mx, self.centro.x())), max(-my, min(my, self.centro.y())))

    # ------------------------------------------------------------ botones
    def _crear_botones(self):
        B = Boton
        self.botones = [
            B("zoom_mas", texto="+", ayuda=tr("Acercar (+)")),
            B("zoom_menos", texto="−", ayuda=tr("Alejar (−)")),
            B("zoom_1", texto="1:1", ayuda=tr("Tamaño real (1)")),
            B("editor", texto=tr("Abrir con editor"), ayuda=tr("Abrir con el editor de imágenes (Ctrl+E)")),
            B("anterior", tipo="flecha_izq", ayuda=tr("Anterior (←)")),
            B("play", tipo="play", ayuda=tr("Presentación (F5)")),
            B("siguiente", tipo="flecha_der", ayuda=tr("Siguiente (→)")),
            B("carpeta", texto=tr("Abrir carpeta"), ayuda=tr("Mostrar la foto en su carpeta")),
            B("rot_izq", texto="↺", ayuda=tr("Rotar a la izquierda (Ctrl+Mayús+R)")),
            B("rot_der", texto="↻", ayuda=tr("Rotar a la derecha (Ctrl+R)")),
            B("estrella", ayuda=tr("Estrella (Ctrl+8)")),
            B("menu", ayuda=tr("Más opciones")),
            B("cerrar", tipo="cerrar", ayuda=tr("Cerrar (Esc)")),
            B("ayuda", tipo="ayuda", ayuda=tr("Atajos de teclado")),
        ]
        self._por_id = {b.id: b for b in self.botones}

    def _ubicar_botones(self):
        barra = self._rect_barra()
        h = barra.height() - 2
        y = barra.top() + 1
        cx = self.width() / 2
        # bloque central: flechas + play
        anchos = {"zoom_mas": 22, "zoom_menos": 22, "zoom_1": 28, "editor": 118,
                  "carpeta": 104, "rot_izq": 26, "rot_der": 26, "estrella": 30, "menu": 30}
        # las píldoras con texto se miden: el texto cambia con el idioma (3.10)
        f = QFont(self.font())
        f.setPixelSize(12)  # el mismo tamaño con que las pinta dibujo.pildora
        fm = QFontMetrics(f)
        for ident in ("editor", "carpeta"):
            anchos[ident] = max(anchos[ident], fm.horizontalAdvance(self._por_id[ident].texto) + 24)
        play_r = 17
        flecha_w, flecha_h = 26, 22
        P = self._por_id
        P["play"].rect = QRectF(cx - play_r, barra.center().y() - play_r, play_r * 2, play_r * 2)
        P["anterior"].rect = QRectF(cx - play_r - 2 - flecha_w, barra.center().y() - flecha_h / 2, flecha_w, flecha_h)
        P["siguiente"].rect = QRectF(cx + play_r + 2, barra.center().y() - flecha_h / 2, flecha_w, flecha_h)
        # izquierda del bloque central (de derecha a izquierda)
        x = P["anterior"].rect.left() - 14
        for ident, sep in (("editor", 12), ("zoom_1", 3), ("zoom_menos", 3), ("zoom_mas", 0)):
            w = anchos[ident]
            P[ident].rect = QRectF(x - w, y, w, h)
            x -= w + sep
        # derecha
        x = P["siguiente"].rect.right() + 14
        for ident, sep in (("carpeta", 12), ("rot_izq", 3), ("rot_der", 12), ("estrella", 12), ("menu", 0)):
            w = anchos[ident]
            P[ident].rect = QRectF(x, y, w, h)
            x += w + sep
        P["cerrar"].rect = QRectF(self.width() - 56, 0, 56, 56)
        P["ayuda"].rect = QRectF(self.width() - 26, 60, 20, 20)

    def _actualizar_botones(self):
        P = self._por_id
        hay = self.img is not None
        P["estrella"].activo = self.ruta is not None and os.path.basename(self.ruta) in self.con_estrella
        P["play"].activo = self.presentando
        P["anterior"].habilitado = self.indice > 0
        P["siguiente"].habilitado = self.indice < len(self.lista) - 1
        for i in ("zoom_mas", "zoom_menos", "zoom_1", "rot_izq", "rot_der"):
            P[i].habilitado = hay

    def _boton_en(self, pos):
        if self.presentando:
            return None
        for b in self.botones:
            if b.tipo == "cerrar":
                # cuarto de círculo en la esquina
                d = QPointF(self.width(), 0) - QPointF(pos)
                if (d.x() ** 2 + d.y() ** 2) ** 0.5 <= 56:
                    return b
            elif b.rect.contains(QPointF(pos)):
                return b
        return None

    # ------------------------------------------------------------ pintura
    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        a = self._aparicion
        if self.presentando:
            p.fillRect(self.rect(), QColor(0, 0, 0))
        else:
            p.fillRect(self.rect(), QColor(14, 14, 16, int(255 * self.opacidad * a)))
        p.setOpacity(a)
        self._pintar_foto(p, a)
        if not self.presentando:
            self._pintar_titulo(p)
            self._pintar_tira(p)
            self._ubicar_botones()
            self._pintar_botones(p)
            self._pintar_cerrar(p)
        if self.mensaje:
            self._pintar_mensaje(p)
        if self._mostrar_ayuda:
            self._pintar_ayuda(p)
        p.end()

    def _imagen_para(self, zoom):
        """Para zoom < 1 se pinta desde una copia reducida (cacheada) en vez de
        reducir la foto entera en cada repintado."""
        if zoom >= 0.999 or self._anim_zoom.state() == QVariantAnimation.State.Running:
            return self.img, 1.0
        if self._escalada is None or abs(self._escalada[0] - zoom) > 1e-6:
            w = max(1, round(self.img.width() * zoom))
            h = max(1, round(self.img.height() * zoom))
            self._escalada = (zoom, self.img.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                    Qt.TransformationMode.SmoothTransformation))
        return self._escalada[1], zoom

    def _pintar_foto(self, p, aparicion):
        if self.img is None:
            p.setPen(QColor(220, 220, 220))
            f = QFont(self.font())
            f.setPixelSize(15)
            p.setFont(f)
            texto = self.error or tr("Cargando…")
            p.drawText(self._area_foto(), Qt.AlignmentFlag.AlignCenter, texto)
            return
        z = self.zoom_actual()
        destino = self._rect_foto(z)
        if aparicion < 1:  # aparece creciendo desde el 85 %
            esc = 0.85 + 0.15 * aparicion
            c = destino.center()
            destino = QRectF(c.x() - destino.width() * esc / 2, c.y() - destino.height() * esc / 2,
                             destino.width() * esc, destino.height() * esc)
        if not self.presentando:
            # sombra suave
            for i, al in ((10, 18), (6, 28), (3, 40)):
                p.fillRect(destino.adjusted(-i + 3, -i + 5, i + 3, i + 5), QColor(0, 0, 0, al))
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,
                        self._anim_zoom.state() != QVariantAnimation.State.Running)
        fuente, esc_fuente = self._imagen_para(z)
        visible = destino.intersected(QRectF(self.rect()))
        if visible.isEmpty():
            return
        # solo la parte visible de la fuente (importa con zoom grande)
        sx = (visible.left() - destino.left()) / destino.width() * fuente.width()
        sy = (visible.top() - destino.top()) / destino.height() * fuente.height()
        sw = visible.width() / destino.width() * fuente.width()
        sh = visible.height() / destino.height() * fuente.height()
        if self._fundido_anterior is not None:
            t = self._anim_fundido.currentValue() or 0.0
            ant_img, ant_rect = self._fundido_anterior
            p.save()
            p.setOpacity(1 - t)
            p.drawImage(ant_rect, ant_img)
            p.restore()
            p.save()
            p.setOpacity(t)
            p.drawImage(visible, fuente, QRectF(sx, sy, sw, sh))
            p.restore()
        else:
            p.drawImage(visible, fuente, QRectF(sx, sy, sw, sh))

    def _pintar_titulo(self, p):
        if not self.ruta:
            return
        nombre = os.path.basename(self.ruta)
        if self.img is not None:
            texto = f"{nombre} ({self.img.width()} x {self.img.height()})"
        else:
            texto = nombre
        if self.zoom is not None:
            texto += f"  ·  {round(self.zoom_actual() * 100)} %"
        f = QFont(self.font())
        f.setPixelSize(13)
        f.setBold(True)
        p.setFont(f)
        r = self._rect_titulo()
        dibujo.texto_con_sombra(p, r, Qt.AlignmentFlag.AlignCenter, texto)
        if self._por_id["estrella"].activo:
            ancho = p.fontMetrics().horizontalAdvance(texto)
            dibujo.estrella(p, QPointF(r.center().x() + ancho / 2 + 14, r.center().y()), 7, QColor("#f4c430"))
        f.setBold(False)
        f.setPixelSize(11)
        p.setFont(f)
        dibujo.texto_con_sombra(p, r.adjusted(0, 0, -16, 0), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                                tr("{i} de {n}", i=self.indice + 1, n=len(self.lista)), QColor(200, 200, 200))

    def _posiciones_tira(self):
        """[(indice, QRectF)] de las miniaturas visibles. La actual queda al
        centro, como en Picasa, y un poco más grande."""
        t = self._rect_tira()
        centro = self.tira_desplazada if self.tira_desplazada is not None else self.indice
        cx = t.center().x()
        n = int(t.width() / PASO_TILE / 2) + 2
        out = []
        for i in range(max(0, int(centro) - n), min(len(self.lista), int(centro) + n + 1)):
            x = cx + (i - centro) * PASO_TILE
            lado = LADO_TILE + (6 if i == self.indice else 0)
            r = QRectF(x - lado / 2, t.center().y() - lado / 2, lado, lado)
            if r.right() >= 0 and r.left() <= self.width():
                out.append((i, r))
        return out

    def _pintar_tira(self, p):
        t = self._rect_tira()
        p.fillRect(t, QColor(0, 0, 0, 110))
        actual = None
        for i, r in self._posiciones_tira():
            ruta = self.lista[i]
            m = self.cargador.mini(ruta)
            if i == self.indice:
                actual = r
                continue
            p.save()
            p.setOpacity(p.opacity() * (0.78 if self._hover != ("tile", i) else 1.0))
            if m is not None and not m.isNull():
                p.drawImage(r, m)
            else:
                p.fillRect(r, QColor(60, 60, 60))
            p.restore()
        if actual is not None:
            m = self.cargador.mini(self.ruta)
            p.fillRect(actual.adjusted(-2, -2, 2, 2), QColor("white"))
            if m is not None and not m.isNull():
                p.drawImage(actual, m)
            else:
                p.fillRect(actual, QColor(60, 60, 60))

    def _pintar_botones(self, p):
        for b in self.botones:
            if b.tipo in ("cerrar", "ayuda"):
                continue
            dibujo.dibujar(p, b, self._hover == ("boton", b.id), self._presionado == b.id)

    def _pintar_cerrar(self, p):
        b = self._por_id["cerrar"]
        hover = self._hover == ("boton", "cerrar")
        camino = QPainterPath()
        camino.moveTo(self.width(), 0)
        camino.arcTo(QRectF(self.width() - 56, -56, 112, 112), 180, 90)
        camino.closeSubpath()
        p.fillPath(camino, QColor(200, 40, 40, 230) if hover else QColor(20, 20, 20, 220))
        dibujo.icono(p, "cerrar", QRectF(self.width() - 34, 4, 30, 30), QColor("white"))
        # «?» de ayuda
        a = self._por_id["ayuda"].rect
        p.setPen(QPen(QColor(220, 220, 220), 1.4))
        p.setBrush(QColor(30, 30, 30, 200) if self._hover != ("boton", "ayuda") else QColor(80, 80, 80, 230))
        p.drawEllipse(a)
        f = QFont(self.font())
        f.setPixelSize(12)
        f.setBold(True)
        p.setFont(f)
        p.drawText(a, Qt.AlignmentFlag.AlignCenter, "?")

    def _pintar_mensaje(self, p):
        f = QFont(self.font())
        f.setPixelSize(14)
        p.setFont(f)
        ancho = p.fontMetrics().horizontalAdvance(self.mensaje) + 40
        r = QRectF((self.width() - ancho) / 2, 40, ancho, 34)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 20, 20, 225))
        p.drawRoundedRect(r, 8, 8)
        p.setPen(QColor("white"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.mensaje)

    def _pintar_ayuda(self, p):
        f = QFont(self.font())
        f.setPixelSize(13)
        p.setFont(f)
        alto_fila = 22
        atajos = [(tr(t), tr(q)) for t, q in dialogos.ATAJOS]
        # columnas medidas: el ancho del texto cambia con el idioma (3.10)
        fm = p.fontMetrics()
        col1 = max(220, max(fm.horizontalAdvance(t) for t, _ in atajos) + 20)
        col2 = max(300, max(fm.horizontalAdvance(q) for _, q in atajos) + 10)
        r = QRectF(0, 0, 30 + col1 + col2 + 10, 40 + alto_fila * len(atajos))
        r.moveCenter(QPointF(self.width() / 2, self.height() / 2 - 40))
        p.setPen(QPen(QColor(90, 90, 90), 1))
        p.setBrush(QColor(18, 18, 20, 240))
        p.drawRoundedRect(r, 10, 10)
        y = r.top() + 20
        for tecla, que in atajos:
            p.setPen(QColor("#9fc7ff"))
            p.drawText(QRectF(r.left() + 20, y, col1, alto_fila), Qt.AlignmentFlag.AlignVCenter, tecla)
            p.setPen(QColor("white"))
            p.drawText(QRectF(r.left() + 30 + col1, y, col2, alto_fila), Qt.AlignmentFlag.AlignVCenter, que)
            y += alto_fila

    # ------------------------------------------------------------ mensajes
    def avisar(self, texto):
        self.mensaje = texto
        self._timer_mensaje.start()
        self.update()

    def _borrar_mensaje(self):
        self.mensaje = ""
        self.update()

    # ------------------------------------------------------------ navegación
    def navegar(self, delta, ciclico=False):
        if not self.lista:
            return
        j = self.indice + delta
        if ciclico:
            j %= len(self.lista)
        j = max(0, min(len(self.lista) - 1, j))
        self.ir_a(j)

    def ir_a(self, j):
        if j == self.indice or not (0 <= j < len(self.lista)):
            return
        if self.presentando and self.img is not None:
            self._fundido_anterior = (self._imagen_para(self.zoom_actual())[0], self._rect_foto())
            self._anim_fundido.start()
        self.indice = j
        self.tira_desplazada = None
        self._cargar_actual()

    def _fin_fundido(self):
        self._fundido_anterior = None
        self.update()

    # ------------------------------------------------------------ zoom
    def fijar_zoom(self, nuevo, ancla=None, animar=True):
        if self.img is None:
            return
        ajust = self.zoom_ajustado()
        viejo = self.zoom_actual()
        # como en Picasa: no se aleja más allá de «ajustada a la pantalla»
        nuevo = max(ajust, min(ZOOM_MAX, nuevo))
        if abs(nuevo - viejo) < 1e-9:
            return
        a = self._area_foto()
        if ancla is None:
            ancla = a.center()
        # mantener quieto el punto de la foto que está bajo el ancla
        rel = (QPointF(ancla) - (a.center() + self.centro)) / viejo
        destino_centro = QPointF(ancla) - a.center() - rel * nuevo
        if abs(nuevo - ajust) < 1e-9:
            nuevo_modo = None
            destino_centro = QPointF(0, 0)
        else:
            nuevo_modo = nuevo
        if animar:
            self._anim_desde = (viejo, QPointF(self.centro))
            self._anim_hasta = (nuevo, destino_centro, nuevo_modo)
            self._anim_zoom.stop()
            self._anim_zoom.setStartValue(0.0)
            self._anim_zoom.setEndValue(1.0)
            self._anim_zoom.start()
        else:
            self.zoom = nuevo_modo
            self.centro = destino_centro
            self._limitar_centro()
            self.update()

    def _paso_zoom(self, t):
        (z0, c0), (z1, c1, modo) = self._anim_desde, self._anim_hasta
        z = z0 + (z1 - z0) * t
        self.zoom = z if t < 1 else modo
        self.centro = c0 + (c1 - c0) * t
        if t >= 1:
            self._limitar_centro()
        self.update()

    def zoom_1_1(self, ancla=None):
        if self.zoom is not None and abs(self.zoom_actual() - 1.0) < 1e-6:
            self.fijar_zoom(self.zoom_ajustado(), ancla)
        else:
            self.fijar_zoom(1.0, ancla)

    def zoom_ajustar(self):
        self.fijar_zoom(self.zoom_ajustado())

    # ------------------------------------------------------------ presentación
    def alternar_presentacion(self):
        self.presentando = not self.presentando
        if self.presentando:
            self.zoom = None
            self.centro = QPointF(0, 0)
            self._escalada = None
            self._timer_pres.start()
            self.setCursor(Qt.CursorShape.BlankCursor)
            self.avisar(tr("Presentación — Esc o clic para salir"))
        else:
            self._timer_pres.stop()
            self.zoom = None
            self._escalada = None
            self.unsetCursor()
        self._actualizar_botones()
        self.update()

    # ------------------------------------------------------------ acciones
    def accion(self, ident):
        r = self.ruta
        try:
            if ident == "zoom_mas":
                self.fijar_zoom(self.zoom_actual() * PASO_ZOOM)
            elif ident == "zoom_menos":
                self.fijar_zoom(self.zoom_actual() / PASO_ZOOM)
            elif ident == "zoom_1":
                self.zoom_1_1()
            elif ident == "anterior":
                self.navegar(-1)
            elif ident == "siguiente":
                self.navegar(+1)
            elif ident == "play":
                self.alternar_presentacion()
            elif ident == "editor":
                ed = acciones.abrir_con_editor(r)
                self.avisar(tr("Abriendo en {editor}…", editor=ed) if ed else tr("Abriendo con la aplicación del sistema…"))
            elif ident == "carpeta":
                acciones.mostrar_en_carpeta(r)
                self.showMinimized()
            elif ident in ("rot_izq", "rot_der"):
                self.rotar(90 if ident == "rot_der" else -90)
            elif ident == "estrella":
                self.alternar_estrella()
            elif ident == "menu":
                b = self._por_id["menu"].rect
                self.menu(self.mapToGlobal(QPointF(b.left(), b.top()).toPoint()), arriba=True)
            elif ident == "cerrar":
                self.close()
            elif ident == "ayuda":
                self._mostrar_ayuda = not self._mostrar_ayuda
                self.update()
        except acciones.ErrorAccion as e:
            QMessageBox.warning(self, "PicPhotoViewer", str(e))
        except Exception as e:
            log.error("Falló una acción", {"accion": ident, "archivo": r, "error": repr(e)})
            QMessageBox.warning(self, "PicPhotoViewer", tr("No se pudo completar la acción:\n{error}", error=e))

    def rotar(self, grados):
        r = self.ruta
        if r is None or self.img is None:
            return
        if not os.access(r, os.W_OK):
            raise acciones.ErrorAccion(tr("No hay permiso para modificar este archivo."))
        acciones.rotar(r, grados)
        self.cargador.olvidar(r)
        self._cargar_actual()

    def alternar_estrella(self):
        r = self.ruta
        nombre = os.path.basename(r)
        valor = nombre not in self.con_estrella
        try:
            estrellas.poner_estrella(r, valor)
        except OSError as e:
            raise acciones.ErrorAccion(tr("No se pudo guardar la estrella en .picasa.ini:\n{error}", error=e))
        (self.con_estrella.add if valor else self.con_estrella.discard)(nombre)
        self._actualizar_botones()
        self.update()

    def copiar(self):
        r = self.ruta
        # xclip queda vivo en segundo plano sirviendo el portapapeles: así la
        # imagen se puede pegar aunque se cierre el visor (GNOME no trae gestor
        # de portapapeles que la conserve).
        if shutil.which("xclip") and os.environ.get("XDG_SESSION_TYPE") != "wayland" and self.img is not None:
            import tempfile
            fd, tmp = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            self.img.save(tmp, "PNG")
            subprocess.Popen(f"xclip -selection clipboard -t image/png -i {_q(tmp)}; rm -f {_q(tmp)}",
                             shell=True, start_new_session=True)
        elif shutil.which("wl-copy") and os.environ.get("XDG_SESSION_TYPE") == "wayland":
            with open(r, "rb") as f:
                subprocess.Popen(["wl-copy", "--type", "image/png" if r.lower().endswith(".png") else "image/jpeg"],
                                 stdin=f, start_new_session=True)
        elif self.img is not None:
            QApplication.clipboard().setImage(self.img)
        self.avisar(tr("Imagen copiada"))

    def imprimir(self):
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        if self.img is None:
            return
        impresora = QPrinter(QPrinter.PrinterMode.HighResolution)
        dlg = QPrintDialog(impresora, self)
        if dlg.exec() != QPrintDialog.DialogCode.Accepted:
            return
        p = QPainter(impresora)
        area = QRectF(impresora.pageRect(QPrinter.Unit.DevicePixel))
        area.moveTo(0, 0)
        tam = QSize(self.img.size())
        tam.scale(area.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio)
        destino = QRectF(0, 0, tam.width(), tam.height())
        destino.moveCenter(area.center())
        p.drawImage(destino, self.img)
        p.end()
        log.info("Imagen impresa", {"archivo": self.ruta})

    def papelera(self):
        r = self.ruta
        acciones.mandar_a_papelera(r)
        self.cargador.olvidar(r)
        del self.lista[self.indice]
        if not self.lista:
            self.close()
            return
        self.indice = min(self.indice, len(self.lista) - 1)
        self._cargar_actual()
        self.avisar(tr("«{nombre}» se envió a la papelera", nombre=os.path.basename(r)))

    def fondo_escritorio(self):
        from fondos.dialogo import elegir_y_aplicar
        if elegir_y_aplicar(self.ruta, self):
            self.avisar(tr("Fondo de escritorio aplicado"))

    def fondo_gdm(self):
        from fondos import gdm
        if not gdm.disponible():
            raise acciones.ErrorAccion(tr("El ayudante de GDM no está instalado (se instala con el .deb)."))
        self.setCursor(Qt.CursorShape.WaitCursor)
        try:
            gdm.aplicar(self.ruta)
        except gdm.ErrorGdm as e:
            if str(e) != "cancelado":
                raise acciones.ErrorAccion(tr("No se pudo cambiar el fondo de inicio de sesión:\n{error}", error=e))
            return
        finally:
            self.unsetCursor()
        self.avisar(tr("Fondo de inicio de sesión aplicado: se verá al cerrar sesión o reiniciar"))

    def restaurar_gdm(self):
        from fondos import gdm
        try:
            gdm.restaurar()
        except gdm.ErrorGdm as e:
            if str(e) != "cancelado":
                raise acciones.ErrorAccion(str(e))
            return
        self.avisar(tr("Fondo de inicio de sesión original restaurado"))

    def hacer_predeterminado(self):
        acciones.hacer_predeterminado()
        self.avisar(tr("PicPhotoViewer es ahora el visor de imágenes predeterminado"))

    def preguntar_predeterminado(self):
        """Primera vez que se abre (o 7 días después de «Ahora no»)."""
        import time
        if not acciones.debe_preguntar_predeterminado():
            return
        config.set("ultima_pregunta_predeterminado", int(time.time()))
        caja = QMessageBox(self)
        caja.setWindowTitle("PicPhotoViewer")
        caja.setIcon(QMessageBox.Icon.Question)
        caja.setText(tr("<b>¿Abrir las imágenes con PicPhotoViewer?</b><br>"
                        "Al hacer doble clic en una foto se abrirá con este visor."))
        b_si = caja.addButton(tr("Sí, usar PicPhotoViewer"), QMessageBox.ButtonRole.AcceptRole)
        caja.addButton(tr("Ahora no"), QMessageBox.ButtonRole.RejectRole)
        b_nunca = caja.addButton(tr("No volver a preguntar"), QMessageBox.ButtonRole.DestructiveRole)
        caja.setDefaultButton(b_si)
        caja.exec()
        if caja.clickedButton() is b_si:
            self._seguro(self.hacer_predeterminado)
        elif caja.clickedButton() is b_nunca:
            config.set("preguntar_predeterminado", "no")

    def menu(self, pos, arriba=False):
        m = QMenu(self)
        m.setStyleSheet(_ESTILO_MENU)
        hay = self.img is not None

        def item(texto, fn, atajo=None, habilitado=True):
            a = m.addAction(texto)
            if atajo:
                a.setShortcut(QKeySequence(atajo))
            a.setEnabled(habilitado)
            a.triggered.connect(lambda: self._seguro(fn))
            return a

        item(tr("Copiar imagen"), self.copiar, "Ctrl+C", hay)
        item(tr("Imprimir…"), self.imprimir, "Ctrl+P", hay)
        m.addSeparator()
        item(tr("Poner como fondo de escritorio…"), self.fondo_escritorio, habilitado=hay)
        item(tr("Poner como fondo de inicio de sesión"), self.fondo_gdm, habilitado=hay)
        item(tr("Restaurar el fondo de inicio de sesión original"), self.restaurar_gdm)
        m.addSeparator()
        item(tr("Abrir con editor"), lambda: self.accion("editor"), "Ctrl+E")
        item(tr("Mostrar en la carpeta"), lambda: self.accion("carpeta"))
        item(tr("Propiedades"), lambda: dialogos.propiedades(self, self.ruta), "Alt+Return")
        item(tr("Mover a la papelera"), self.papelera, "Delete")
        m.addSeparator()
        if not acciones.es_predeterminado():
            item(tr("Usar como visor de imágenes predeterminado"), self.hacer_predeterminado)
        item(tr("Buscar actualizaciones"), lambda: self.buscar_actualizaciones(manual=True))
        item(tr("Acerca de PicPhotoViewer"), lambda: dialogos.acerca_de(self))
        if arriba:
            pos = pos - QPointF(0, m.sizeHint().height()).toPoint()
        m.exec(pos)

    def _seguro(self, fn):
        try:
            fn()
        except acciones.ErrorAccion as e:
            QMessageBox.warning(self, "PicPhotoViewer", str(e))
        except Exception as e:
            log.error("Falló una acción del menú", {"archivo": self.ruta, "error": repr(e)})
            QMessageBox.warning(self, "PicPhotoViewer", tr("No se pudo completar la acción:\n{error}", error=e))

    # ------------------------------------------------------------ actualizaciones
    def buscar_actualizaciones(self, manual=False):
        from actualizar.ui import Buscador
        self._buscador = Buscador(self, manual)
        self._buscador.empezar()

    # ------------------------------------------------------------ teclado
    def _atajos(self):
        def atajo(secuencias, fn):
            for s in secuencias:
                QShortcut(QKeySequence(s), self, activated=lambda f=fn: self._seguro(f))

        atajo(["Right", "PgDown", "Space"], lambda: self.navegar(+1))
        atajo(["Left", "PgUp", "Backspace"], lambda: self.navegar(-1))
        atajo(["Home"], lambda: self.ir_a(0))
        atajo(["End"], lambda: self.ir_a(len(self.lista) - 1))
        atajo(["+", "=", "Ctrl++", "Ctrl+="], lambda: self.accion("zoom_mas"))
        atajo(["-", "Ctrl+-"], lambda: self.accion("zoom_menos"))
        atajo(["1"], self.zoom_1_1)
        atajo(["0"], self.zoom_ajustar)
        atajo(["F5", "Ctrl+Space"], self.alternar_presentacion)
        atajo(["Ctrl+R"], lambda: self.rotar(90))
        atajo(["Ctrl+Shift+R"], lambda: self.rotar(-90))
        atajo(["Ctrl+8", "S"], self.alternar_estrella)
        atajo(["Ctrl+C"], self.copiar)
        atajo(["Ctrl+P"], self.imprimir)
        atajo(["Ctrl+E"], lambda: self.accion("editor"))
        atajo(["Delete"], self.papelera)
        atajo(["Alt+Return", "Alt+Enter"], lambda: dialogos.propiedades(self, self.ruta))
        atajo(["F1", "?"], lambda: self.accion("ayuda"))
        atajo(["Menu", "Shift+F10"], lambda: self.menu(QCursor.pos()))
        atajo(["Ctrl+Q", "Ctrl+W"], self.close)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            if self._mostrar_ayuda:
                self._mostrar_ayuda = False
                self.update()
            elif self.presentando:
                self.alternar_presentacion()
            else:
                self.close()
            return
        super().keyPressEvent(e)

    # ------------------------------------------------------------ ratón
    def _que_hay(self, pos):
        b = self._boton_en(pos)
        if b:
            return ("boton", b.id)
        if not self.presentando and self._rect_tira().contains(QPointF(pos)):
            for i, r in self._posiciones_tira():
                if r.contains(QPointF(pos)):
                    return ("tile", i)
            return ("tira", None)
        if self.img is not None and self._rect_foto().contains(QPointF(pos)):
            return ("foto", None)
        if not self.presentando and (self._rect_barra().contains(QPointF(pos))
                                     or self._rect_titulo().contains(QPointF(pos))):
            return ("barra", None)
        return ("fondo", None)

    def mousePressEvent(self, e):
        if self._mostrar_ayuda:
            self._mostrar_ayuda = False
            self.update()
            return
        if self.presentando:
            if e.button() == Qt.MouseButton.LeftButton:
                self.alternar_presentacion()
            return
        que = self._que_hay(e.position())
        self._movio = False
        if e.button() == Qt.MouseButton.RightButton:
            if que[0] in ("foto", "fondo"):
                self.menu(e.globalPosition().toPoint())
            return
        if e.button() != Qt.MouseButton.LeftButton:
            return
        if que[0] == "boton":
            b = self._por_id[que[1]]
            if b.habilitado:
                self._presionado = b.id
                self.update()
            return
        self._arrastre = (e.position(), QPointF(self.centro), que)
        if que[0] == "foto" and self._se_puede_mover():
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _se_puede_mover(self):
        r = self._rect_foto()
        a = self._area_foto()
        return r.width() > a.width() + 0.5 or r.height() > a.height() + 0.5

    def mouseMoveEvent(self, e):
        pos = e.position()
        if self._arrastre is not None:
            inicio, centro0, que = self._arrastre
            d = pos - inicio
            if abs(d.x()) + abs(d.y()) > 3:
                self._movio = True
            if que[0] == "foto" and self._se_puede_mover():
                self.centro = centro0 + d
                self._limitar_centro()
                self.update()
            return
        que = self._que_hay(pos)
        if que != self._hover:
            self._hover = que
            if que[0] == "boton":
                QToolTip.showText(e.globalPosition().toPoint(), self._por_id[que[1]].ayuda, self)
            elif que[0] == "tile":
                QToolTip.showText(e.globalPosition().toPoint(), os.path.basename(self.lista[que[1]]), self)
            else:
                QToolTip.hideText()
            if que[0] in ("boton", "tile"):
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            elif que[0] == "foto" and self._se_puede_mover():
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            elif not self.presentando:
                self.unsetCursor()
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        que = self._que_hay(e.position())
        if self._presionado is not None:
            ident = self._presionado
            self._presionado = None
            self.update()
            if que == ("boton", ident):
                self.accion(ident)
            return
        if self._arrastre is None:
            return
        _, _, inicio = self._arrastre
        self._arrastre = None
        if que[0] == "foto" and self._se_puede_mover():
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        if self._movio:
            return
        if inicio[0] == "tile" and que == inicio:
            self.ir_a(que[1])
        elif inicio[0] == "fondo" and que[0] == "fondo":
            self.close()  # clic fuera de la foto: cerrar, como Picasa

    def mouseDoubleClickEvent(self, e):
        if self._que_hay(e.position())[0] == "foto":
            self.zoom_1_1(e.position())

    def wheelEvent(self, e):
        if self.presentando:
            return
        delta = e.angleDelta().y() or e.angleDelta().x()
        if not delta:
            return
        que = self._que_hay(e.position())
        if que[0] in ("tira", "tile"):
            self.navegar(-1 if delta > 0 else +1)
        elif que[0] == "barra":
            return
        else:
            factor = PASO_ZOOM ** (delta / 120)
            self.fijar_zoom(self.zoom_actual() * factor, e.position(), animar=abs(delta) >= 120)

    def resizeEvent(self, e):
        self._escalada = None
        super().resizeEvent(e)

    def closeEvent(self, e):
        self.cargador.cancelar_minis()
        super().closeEvent(e)


def _q(s):
    import shlex
    return shlex.quote(s)


_ESTILO_MENU = """
QMenu { background: #2b2b2d; color: #ececec; border: 1px solid #555; padding: 4px; }
QMenu::item { padding: 6px 28px 6px 20px; border-radius: 4px; }
QMenu::item:selected { background: #3d8ee6; color: white; }
QMenu::item:disabled { color: #777; }
QMenu::separator { height: 1px; background: #4a4a4a; margin: 4px 8px; }
"""
