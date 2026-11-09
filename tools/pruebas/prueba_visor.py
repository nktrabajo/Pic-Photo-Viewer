#!/usr/bin/python3 -I
"""Prueba de interacción del visor (offscreen): botones, teclado, arrastre,
miniaturas, presentación, papelera y cerrar con clic fuera de la foto.

    python3 -I tools/pruebas/prueba_visor.py

Sin argumentos se corre dos veces, en español y en inglés (PPV_IDIOMA), cada
una en su propio proceso (el idioma se decide una vez por proceso).
"""
import sys, os, tempfile, shutil, subprocess
if len(sys.argv) == 1:
    total = 0
    for lang in ("es", "en"):
        print(f"--- idioma {lang}", flush=True)
        r = subprocess.run([sys.executable, "-I", os.path.abspath(__file__), lang],
                           env=dict(os.environ, PPV_IDIOMA=lang))
        total |= r.returncode
    print("TODO OK" if total == 0 else "HAY FALLAS")
    sys.exit(1 if total else 0)
IDIOMA = sys.argv[1]
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "src"))
S = tempfile.mkdtemp(prefix="ppv-visor-")
from PIL import Image
os.makedirs(S + "/f2")
os.makedirs(S + "/home")  # sin HOME existente no hay papelera (ni Qt ni gio pueden crearla)
for i in range(1, 13):
    Image.new("RGB", (4000, 3000) if i % 3 == 0 else (1024, 768), (i * 20, 90, 160)).save(f"{S}/f2/{i}.jpg")
os.environ.update(QT_QPA_PLATFORM="offscreen", HOME=S+"/home", XDG_DATA_HOME=S+"/home/.local/share")
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt, QPoint, QPointF, QTimer
from PySide6.QtGui import QWheelEvent
app=QApplication([])
# un aviso modal colgaría la prueba: se registra en vez de mostrarse
from PySide6.QtWidgets import QMessageBox
avisos = []
QMessageBox.warning = staticmethod(lambda *a, **k: avisos.append(a[2] if len(a) > 2 else a))
QMessageBox.critical = QMessageBox.warning
from visor.ventana import Visor
from visor import estrellas
v=Visor(S+'/f2/3.jpg'); v.resize(1600,900); v.show(); v._aparicion=1
res=[]
def ok(n,c): res.append((n,bool(c)))
def esperar(ms=600):
    QTest.qWait(ms)
def boton(i):
    v._ubicar_botones(); c=v._por_id[i].rect.center().toPoint()
    QTest.mouseClick(v, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, c)
import time; t0=time.time()
while v.img is None and time.time()-t0<5: QTest.qWait(20)
ok("carga", v.img is not None and v.indice==2)
# idioma: los textos visibles salen en el elegido y caben
from core import idioma
from PySide6.QtGui import QFont, QFontMetrics
ok(f"idioma {IDIOMA}", idioma.actual() == IDIOMA)
esperado = {"es": ("Abrir con editor", "Abrir carpeta"), "en": ("Open in editor", "Show in folder")}[IDIOMA]
ok("textos de la barra", (v._por_id["editor"].texto, v._por_id["carpeta"].texto) == esperado)
v._ubicar_botones()
f = QFont(v.font()); f.setPixelSize(12); fm = QFontMetrics(f)
ok("el texto cabe en su botón", all(fm.horizontalAdvance(v._por_id[i].texto) + 12 <= v._por_id[i].rect.width()
                                    for i in ("editor", "carpeta")))
barra = [v._por_id[i].rect for i in ("zoom_mas", "zoom_menos", "zoom_1", "editor", "anterior", "play",
                                     "siguiente", "carpeta", "rot_izq", "rot_der", "estrella", "menu")]
ok("botones sin encimarse", all(a.right() <= b.left() + 0.01 for a, b in zip(barra, barra[1:])))
boton("siguiente"); esperar(); ok("siguiente", os.path.basename(v.ruta)=="4.jpg")
QTest.keyClick(v, Qt.Key.Key_Left); esperar(); ok("flecha izq", os.path.basename(v.ruta)=="3.jpg")
QTest.keyClick(v, Qt.Key.Key_End); esperar(); ok("fin", v.indice==len(v.lista)-1)
QTest.keyClick(v, Qt.Key.Key_Home); esperar(); ok("inicio", v.indice==0)
# foto grande para zoom: buscar una 4000x3000
for i,r in enumerate(v.lista):
    from visor.imagenes import dimensiones
    if dimensiones(r).width()==4000: v.ir_a(i); break
esperar(1200)
z0=v.zoom_actual(); boton("zoom_mas"); esperar(); ok("zoom +", v.zoom_actual()>z0*1.2)
boton("zoom_1"); esperar(); ok("1:1", abs(v.zoom_actual()-1)<1e-6)
c=v._area_foto().center().toPoint()
QTest.mousePress(v, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, c)
QTest.mouseMove(v, c+QPoint(200,100)); QTest.mouseRelease(v, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, c+QPoint(200,100))
ok("arrastre mueve", v.centro.x()>100 and v.isVisible())
QTest.keyClick(v, Qt.Key.Key_0); esperar(); ok("0 = ajustar", v.zoom is None and v.centro==QPointF(0,0))
boton("zoom_menos"); esperar(); ok("no aleja más allá de ajustada", v.zoom is None)
boton("estrella"); ok("estrella", estrellas.tiene_estrella(v.ruta))
boton("estrella"); ok("quitar estrella", not estrellas.tiene_estrella(v.ruta))
# clic en tile vecino
v._ubicar_botones(); pos=[r for i,r in v._posiciones_tira() if i==v.indice+1][0].center().toPoint()
idx=v.indice; QTest.mouseClick(v, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos); esperar()
ok("clic en miniatura", v.indice==idx+1)
boton("play"); ok("presentación", v.presentando and v._timer_pres.isActive())
QTest.keyClick(v, Qt.Key.Key_Escape); ok("esc sale de presentación", not v.presentando and v.isVisible())
n=len(v.lista); r=v.ruta; QTest.keyClick(v, Qt.Key.Key_Delete); esperar()
ok("papelera", len(v.lista)==n-1 and not os.path.exists(r))
QTest.keyClick(v, Qt.Key.Key_F1); ok("ayuda", v._mostrar_ayuda)
QTest.keyClick(v, Qt.Key.Key_Escape); ok("esc cierra ayuda", not v._mostrar_ayuda and v.isVisible())
QTest.mouseClick(v, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(10,300)); esperar(100)
try: cerrada = not v.isVisible()
except RuntimeError: cerrada = True  # WA_DeleteOnClose ya la destruyó
ok("clic fuera cierra", cerrada)
ok("sin avisos de error", not avisos)
for a in avisos: print("AVISO:", a)
for n,c in res: print(("OK   " if c else "FALLA"), n)
print(sum(c for _,c in res), "de", len(res))
shutil.rmtree(S, ignore_errors=True)
sys.exit(0 if all(c for _,c in res) else 1)
