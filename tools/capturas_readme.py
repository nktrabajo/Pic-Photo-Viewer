#!/usr/bin/env python3
"""Genera las capturas y el GIF del README sin pantalla (QT_QPA_PLATFORM=offscreen).

    python3 -I tools/capturas_readme.py FOTOS_DIR FONDO_ESCRITORIO SALIDA_DIR [en|es]

FOTOS_DIR: unas cuantas fotos JPEG (se copian a un temporal; no se tocan).
FONDO_ESCRITORIO: la imagen que hace de escritorio detrás del visor.
Salida: visor.png, ayuda.png, pantallas.png, demo.gif

El visor se pinta encima del «escritorio» igual que lo compone mutter con la
ventana translúcida; la barra superior de GNOME se dibuja a mano. Corre con un
HOME temporal: no deja logs ni config del usuario.
"""
import os
import shutil
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOTOS, FONDO, SALIDA = (os.path.abspath(a) for a in sys.argv[1:4])
IDIOMA = sys.argv[4] if len(sys.argv) > 4 else "en"

TMP = tempfile.mkdtemp(prefix="ppv-capturas-")
os.environ["HOME"] = os.path.join(TMP, "home")
os.makedirs(os.environ["HOME"])
for v in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
    os.environ.pop(v, None)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PPV_IDIOMA"] = IDIOMA
sys.path.insert(0, os.path.join(RAIZ, "src"))

from PySide6.QtCore import QPointF, QRect, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
from fondos import componer as comp, dialogo  # noqa: E402
from visor.ventana import Visor  # noqa: E402

W, H = 1600, 900
BARRA = 28
os.makedirs(SALIDA, exist_ok=True)
carpeta = os.path.join(TMP, "Pictures")
os.makedirs(carpeta)
nombres = []
for i, f in enumerate(sorted(x for x in os.listdir(FOTOS) if x.lower().endswith((".jpg", ".jpeg")))):
    destino = os.path.join(carpeta, f"IMG_{2041 + i}.jpg")
    shutil.copy(os.path.join(FOTOS, f), destino)
    nombres.append(destino)


def escritorio():
    img = QImage(FONDO).scaled(W, H, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                               Qt.TransformationMode.SmoothTransformation)
    img = img.copy((img.width() - W) // 2, (img.height() - H) // 2, W, H)
    img = img.convertToFormat(QImage.Format.Format_ARGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(0, 0, W, BARRA, QColor(0, 0, 0))
    f = QFont()
    f.setPixelSize(13)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor(235, 235, 235))
    p.drawText(QRect(0, 0, W, BARRA), Qt.AlignmentFlag.AlignCenter, "Mon 9 Nov  10:24")
    p.setBrush(QColor(235, 235, 235))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(14, 9, 34, 10, 5, 5)
    for k in range(3):
        p.drawEllipse(QPointF(W - 60 + k * 18, BARRA / 2), 4, 4)
    p.end()
    return img


ESCRITORIO = escritorio()


def componer(visor):
    out = QImage(ESCRITORIO)
    p = QPainter(out)
    p.drawPixmap(0, BARRA, visor.grab())
    p.end()
    return out


# --- capturas fijas -----------------------------------------------------------
v = Visor(nombres[0])
v.resize(W, H - BARRA)
v.show()
v._aparicion = 1.0

cuadros = []
TIEMPO = 80  # ms entre cuadros del GIF
guion = {  # ms → acción (los cuadros se toman en tiempo real: las animaciones del visor corren solas)
    1200: lambda: v.navegar(+1),
    2400: lambda: v.navegar(+1),
    3600: lambda: v.fijar_zoom(v.zoom_ajustado() * 2.6, ancla=QPointF(v.width() * 0.42, v.height() * 0.40)),
    5000: lambda: v.zoom_ajustar(),
    5800: lambda: v.alternar_estrella(),
    6800: lambda: v.navegar(+1),
    7900: lambda: v.navegar(+1),
}
FIN = 9000


def fijas():
    v.ir_a(1)
    QTimer.singleShot(900, fijas_2)


def fijas_2():
    componer(v).save(os.path.join(SALIDA, "visor.png"))
    v._mostrar_ayuda = True
    v.update()
    componer(v).save(os.path.join(SALIDA, "ayuda.png"))
    v._mostrar_ayuda = False
    pantallas()
    # GIF: empieza con el escritorio solo y la foto apareciendo
    v.ir_a(0)
    v._aparicion = 0.0
    QTimer.singleShot(900, gif_inicio)


def pantallas():
    P = comp.Pantalla
    pant = [P("DP-1", QRect(0, 0, 1080, 1920)), P("HDMI-1", QRect(1080, 375, 1920, 1080), True),
            P("eDP-1", QRect(3000, 375, 1920, 1080)), P("DP-2", QRect(4920, 72, 1080, 1920))]
    comp.pantallas_actuales = lambda: (pant, QRect(0, 0, 6000, 1920))
    from visor.imagenes import cargar
    previas = {}
    for p_, f in zip(pant, (nombres[4], ESCRITORIO_RUTA, nombres[6], nombres[8])):
        previas[p_.nombre], _ = cargar(f, maximo=dialogo._tam(700))
    dialogo._previas_actuales = lambda p, l: previas
    d = dialogo.DialogoFondo(nombres[1])
    d.diagrama.seleccion = {"HDMI-1", "DP-2"}
    d._actualizar()
    d.show()
    app.processEvents()
    d.grab().save(os.path.join(SALIDA, "pantallas.png"))
    d.close()


ESCRITORIO_RUTA = os.path.join(TMP, "escritorio.png")
ESCRITORIO.save(ESCRITORIO_RUTA)

t0 = [0]


def gif_inicio():
    t0[0] = 0
    v._anim_aparicion.setStartValue(0.0)
    QTimer.singleShot(500, v._anim_aparicion.start)
    tic()


def tic():
    ms = t0[0]
    for clave in sorted(k for k in guion if k <= ms):  # los tiempos no tienen que caer justo en un cuadro
        guion.pop(clave)()
    cuadros.append(componer(v).scaled(960, 540, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation))
    t0[0] += TIEMPO
    if t0[0] <= FIN:
        QTimer.singleShot(TIEMPO, tic)
    else:
        guardar_gif()
        app.quit()


def guardar_gif():
    from PIL import Image
    marcos = []
    for c in cuadros:
        c = c.convertToFormat(QImage.Format.Format_RGB888)
        im = Image.frombytes("RGB", (c.width(), c.height()), bytes(c.constBits())[:c.sizeInBytes()],
                             "raw", "RGB", c.bytesPerLine())
        marcos.append(im.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
    marcos[0].save(os.path.join(SALIDA, "demo.gif"), save_all=True, append_images=marcos[1:],
                   duration=TIEMPO, loop=0, optimize=True)


QTimer.singleShot(900, fijas)
try:
    app.exec()
finally:
    shutil.rmtree(TMP, ignore_errors=True)
print("Listo:", SALIDA)
