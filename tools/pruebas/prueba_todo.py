#!/usr/bin/python3 -I
"""Suite de PicPhotoViewer. Sin pantalla real (QT_QPA_PLATFORM=offscreen), sin
tocar el escritorio del usuario: gsettings se reemplaza por un diccionario,
HOME/XDG apuntan a un directorio temporal, GitHub es un http.server local y el
tema de GDM es una COPIA dentro de una raíz falsa (PPV_RAIZ).

    python3 -I tools/pruebas/prueba_todo.py

Regla de la casa: cada bloque se validó saboteando el código que cubre y
viendo que falla (ver «Cómo se verificó» en CLAUDE.md).
"""
import hashlib
import http.server
import os
import shutil
import subprocess
import sys
import tempfile
import threading

RAIZ_PROY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TMP = tempfile.mkdtemp(prefix="ppv-prueba-")
os.environ.update(HOME=TMP, XDG_DATA_HOME=TMP + "/datos", XDG_CONFIG_HOME=TMP + "/config",
                  XDG_CACHE_HOME=TMP + "/cache", QT_QPA_PLATFORM="offscreen")
sys.path.insert(0, os.path.join(RAIZ_PROY, "src"))

from PySide6.QtCore import QRect  # noqa: E402
from PySide6.QtGui import QColor, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])

OK = FALLAS = 0


def check(nombre, cond, detalle=""):
    global OK, FALLAS
    if cond:
        OK += 1
    else:
        FALLAS += 1
        print(f"  FALLA: {nombre} {detalle}")


def imagen(ruta, w, h, color):
    img = QImage(w, h, QImage.Format.Format_RGB32)
    img.fill(QColor(color))
    img.save(ruta)
    return ruta


def color_en(img, x, y):
    return QColor(img.pixel(x, y)).name()


def parecido(c1, c2, tol=12):
    a, b = QColor(c1), QColor(c2)
    return all(abs(x - y) <= tol for x, y in zip(a.getRgb()[:3], b.getRgb()[:3]))


# ---------------------------------------------------------------- imágenes
print("imágenes y orden")
from visor import imagenes  # noqa: E402

fotos = os.path.join(TMP, "fotos")
os.makedirs(fotos)
for n in ["img10.jpg", "img2.jpg", "IMG1.png", "notas.txt", ".oculta.jpg", "b.webp"]:
    if n.endswith(".txt"):
        open(os.path.join(fotos, n), "w").write("x")
    else:
        imagen(os.path.join(fotos, n), 40, 30, "red")
nombres = [os.path.basename(r) for r in imagenes.listar_carpeta(fotos)]
check("orden natural y filtro", nombres == ["b.webp", "IMG1.png", "img2.jpg", "img10.jpg"], nombres)
tam = imagenes.dimensiones(os.path.join(fotos, "img2.jpg"))
check("dimensiones", tam is not None and (tam.width(), tam.height()) == (40, 30))
img, err = imagenes.cargar(os.path.join(fotos, "img2.jpg"))
check("cargar", not img.isNull() and img.width() == 40, err)

# ---------------------------------------------------------------- estrellas
print("estrellas (.picasa.ini)")
from visor import estrellas  # noqa: E402

ini = os.path.join(fotos, ".picasa.ini")
with open(ini, "w", encoding="utf-8") as f:
    f.write("[Picasa]\nname=Vacaciones\n[img10.jpg]\nrotate=rotate(1)\nfaces=rect64(abc),ff\n")
r10 = os.path.join(fotos, "img10.jpg")
check("sin estrella al inicio", not estrellas.tiene_estrella(r10))
estrellas.poner_estrella(r10, True)
estrellas.poner_estrella(os.path.join(fotos, "img2.jpg"), True)
check("estrella puesta", estrellas.tiene_estrella(r10))
check("estrellas de carpeta", estrellas.estrellas_de_carpeta(fotos) == {"img10.jpg", "img2.jpg"})
texto = open(ini, encoding="utf-8").read()
check("conserva claves de Picasa", "rotate=rotate(1)" in texto and "name=Vacaciones" in texto
      and "faces=rect64(abc),ff" in texto, texto)
estrellas.poner_estrella(os.path.join(fotos, "img2.jpg"), False)
texto = open(ini, encoding="utf-8").read()
check("quitar estrella borra la sección vacía", "[img2.jpg]" not in texto, texto)
check("quitar no toca las demás", estrellas.tiene_estrella(r10))
os.chmod(fotos, 0o555)
try:
    estrellas.poner_estrella(os.path.join(fotos, "b.webp"), True)
    check("carpeta sin permiso lanza OSError", os.geteuid() == 0)
except OSError:
    check("carpeta sin permiso lanza OSError", True)
finally:
    os.chmod(fotos, 0o755)

# ---------------------------------------------------------------- composición
print("composición del fondo extendido")
from fondos import componer as comp  # noqa: E402

P = comp.Pantalla
# la disposición REAL de la máquina de dev (xrandr, 2026-11-08)
PANT = [P("DP-1-0", QRect(0, 0, 1080, 1920)), P("HDMI-1-0", QRect(1080, 375, 1920, 1080), True),
        P("eDP-1", QRect(3000, 375, 1920, 1080)), P("DVI-I-3-2", QRect(4920, 72, 1080, 1920))]
LIENZO = QRect(0, 0, 6000, 1920)
rojo = imagen(os.path.join(TMP, "rojo.png"), 400, 300, "#ff0000")
verde = imagen(os.path.join(TMP, "verde.png"), 300, 400, "#00ff00")
out = comp.componer(LIENZO, PANT, {"HDMI-1-0": ("imagen", (rojo, "rellenar"))})
check("tamaño del lienzo", (out.width(), out.height()) == (6000, 1920))
check("pantalla elegida pintada", color_en(out, 2040, 915) == "#ff0000")
check("rellenar cubre las esquinas", color_en(out, 1081, 376) == "#ff0000" and color_en(out, 2998, 1453) == "#ff0000")
check("pantalla no elegida intacta", color_en(out, 500, 900) == "#000000")
check("no se sale de su pantalla", color_en(out, 3001, 900) == "#000000")
out = comp.componer(LIENZO, PANT, {"eDP-1": ("imagen", (verde, "ajustar"))})
check("ajustar deja bandas", color_en(out, 3001, 900) == "#000000" and color_en(out, 3960, 900) == "#00ff00")
previo = comp.componer(LIENZO, PANT, {"DP-1-0": ("imagen", (verde, "estirar"))})
out = comp.componer(LIENZO, PANT, {"DP-1-0": ("previo", None), "HDMI-1-0": ("imagen", (rojo, "rellenar"))},
                    previo=previo)
check("previo copia los píxeles", color_en(out, 500, 1900) == "#00ff00" and color_en(out, 2040, 915) == "#ff0000")
grupo = QRect(1080, 375, 3840, 1080)
bandas = imagen(os.path.join(TMP, "bandas.png"), 200, 100, "#0000ff")
bi = QImage(bandas)
for x in range(100, 200):
    for y in range(100):
        bi.setPixel(x, y, QColor("#ffff00").rgb())
bi.save(bandas)
out = comp.componer(LIENZO, PANT, {"HDMI-1-0": ("grupo", (bandas, "estirar", grupo)),
                                   "eDP-1": ("grupo", (bandas, "estirar", grupo))})
check("extendida: mitad izquierda en HDMI", color_en(out, 2000, 900) == "#0000ff")
check("extendida: mitad derecha en eDP", color_en(out, 3500, 900) == "#ffff00")
r = comp.rect_destino(400, 300, QRect(0, 0, 1080, 1920), "centrar")
check("centrar no escala", (round(r.width()), round(r.x())) == (400, 340))

# ---------------------------------------------------------------- aplicar (gsettings falso)
print("aplicar fondo con gsettings falso")
from fondos import aplicar as ap, gnome  # noqa: E402

GS = {"org.gnome.desktop.background picture-uri": "'file://%s'" % imagen(os.path.join(TMP, "azul.png"), 160, 90, "#0000ff"),
      "org.gnome.desktop.background picture-uri-dark": "''",
      "org.gnome.desktop.background picture-options": "'zoom'",
      "org.gnome.desktop.background primary-color": "'#123456'",
      "org.gnome.desktop.interface color-scheme": "'default'"}


def gs_falso(*args):
    if args[0] == "get":
        return GS[f"{args[1]} {args[2]}"]
    GS[f"{args[1]} {args[2]}"] = "'%s'" % args[3]
    return ""


gnome._gsettings = gs_falso
salida = ap.aplicar(rojo, ["HDMI-1-0"], "rellenar", pantallas=PANT, lienzo=LIENZO)
check("opciones spanned", GS["org.gnome.desktop.background picture-options"] == "'spanned'")
check("uri y uri-dark iguales", GS["org.gnome.desktop.background picture-uri"] == GS["org.gnome.desktop.background picture-uri-dark"])
img = QImage(salida)
check("compuesto del tamaño del escritorio", (img.width(), img.height()) == (6000, 1920))
check("elegida en rojo (1ª vez)", parecido(color_en(img, 2040, 915), "#ff0000"))
check("las demás con el fondo que había", parecido(color_en(img, 500, 900), "#0000ff") and parecido(color_en(img, 5400, 900), "#0000ff"))
# se esconde la copia de la foto roja: solo copiando los píxeles del compuesto
# anterior («previo») puede la HDMI seguir roja
copia_roja = ap.leer_estado()["pantallas"]["HDMI-1-0"]["imagen"]
os.rename(copia_roja, TMP + "/oculta")
salida2 = ap.aplicar(verde, ["DP-1-0", "DVI-I-3-2"], "rellenar", pantallas=PANT, lienzo=LIENZO)
os.rename(TMP + "/oculta", copia_roja)
img = QImage(salida2)
check("2ª vez: nuevas en verde", parecido(color_en(img, 500, 900), "#00ff00") and parecido(color_en(img, 5400, 900), "#00ff00"))
check("2ª vez: HDMI conserva el rojo", parecido(color_en(img, 2040, 915), "#ff0000"))
check("2ª vez: eDP conserva el azul", parecido(color_en(img, 3960, 900), "#0000ff"))
check("compuesto viejo borrado", not os.path.exists(salida) and os.path.exists(salida2))
estado = ap.leer_estado()
check("estado con las 4 pantallas", set(estado["pantallas"]) == {p.nombre for p in PANT}, estado)
# cambia la disposición: el lienzo nuevo ya no sirve como «previo», se repinta del estado
PANT2 = [P("HDMI-1-0", QRect(0, 0, 1920, 1080), True), P("eDP-1", QRect(1920, 0, 1920, 1080))]
salida3 = ap.aplicar(verde, ["eDP-1"], "rellenar", pantallas=PANT2, lienzo=QRect(0, 0, 3840, 1080))
img = QImage(salida3)
check("otra disposición: HDMI sigue roja", parecido(color_en(img, 960, 540), "#ff0000"))
check("otra disposición: eDP verde", parecido(color_en(img, 2880, 540), "#00ff00"))
# una sola pantalla: fondo normal, sin componer
ap.aplicar(rojo, ["eDP-1"], "ajustar", pantallas=[PANT2[1]], lienzo=QRect(0, 0, 1920, 1080))
check("una pantalla: modo de GNOME directo", GS["org.gnome.desktop.background picture-options"] == "'scaled'")
check("fondo xml de GNOME", gnome.primera_imagen_xml("/no/existe.xml") is None)

# ---------------------------------------------------------------- rotar
print("rotar")
from visor import acciones  # noqa: E402
from core import config  # noqa: E402

png = imagen(os.path.join(TMP, "rot.png"), 50, 20, "#336699")
acciones.rotar(png, 90)
q = QImage(png)
check("PNG rotado 90", (q.width(), q.height()) == (20, 50))
if shutil.which("exiftran"):
    jpg = imagen(os.path.join(TMP, "rot.jpg"), 64, 32, "#336699")
    acciones.rotar(jpg, -90)
    t = imagenes.dimensiones(jpg)
    check("JPEG rotado con exiftran", (t.width(), t.height()) == (32, 64))
else:
    print("  (exiftran no instalado: la rotación de JPEG no se probó)")

# ---------------------------------------------------------------- visor predeterminado
print("visor predeterminado (mimeapps.list aislado)")
os.makedirs(TMP + "/datos/applications", exist_ok=True)
shutil.copy(os.path.join(RAIZ_PROY, "packaging", "picphotoviewer.desktop"), TMP + "/datos/applications/")
os.environ["XDG_CURRENT_DESKTOP"] = "GNOME"
shutil.rmtree(TMP + "/config", ignore_errors=True)  # carpeta de config inexistente: el caso que fallaba
check("no es predeterminado al inicio", not acciones.es_predeterminado())
check("pregunta la primera vez", acciones.debe_preguntar_predeterminado())
acciones.hacer_predeterminado()
check("queda predeterminado", acciones.es_predeterminado())
mime = open(TMP + "/config/mimeapps.list", encoding="utf-8").read()
check("todos los tipos asociados", all(f"{t}=picphotoviewer.desktop" in mime for t in acciones.TIPOS_MIME), mime)
check("ya predeterminado: no pregunta", not acciones.debe_preguntar_predeterminado())
import time as _t
os.remove(TMP + "/config/mimeapps.list")
config.set("ultima_pregunta_predeterminado", int(_t.time()))
check("«Ahora no»: no repite antes de 7 días", not acciones.debe_preguntar_predeterminado())
check("«Ahora no»: repite a los 7 días", acciones.debe_preguntar_predeterminado(ahora=_t.time() + 8 * 86400))
config.set("preguntar_predeterminado", "no")
check("«No volver a preguntar»", not acciones.debe_preguntar_predeterminado(ahora=_t.time() + 99 * 86400))
# desinstalar.sh limpia la asociación sin tocar las de otros programas
acciones.hacer_predeterminado()
with open(TMP + "/config/mimeapps.list", "a", encoding="utf-8") as f:
    f.write("text/plain=org.gnome.TextEditor.desktop\n")
falsos = TMP + "/bin"
os.makedirs(falsos, exist_ok=True)
for n, cuerpo in (("dpkg", "exit 1"), ("nautilus", "exit 0"), ("gsettings", "echo \"''\"")):
    with open(f"{falsos}/{n}", "w") as f:
        f.write(f"#!/bin/sh\n{cuerpo}\n")
    os.chmod(f"{falsos}/{n}", 0o755)
r = subprocess.run(["bash", os.path.join(RAIZ_PROY, "desinstalar.sh"), "--todo"], stdin=subprocess.DEVNULL,
                   capture_output=True, text=True, env=dict(os.environ, PATH=falsos + ":" + os.environ["PATH"]))
mime = open(TMP + "/config/mimeapps.list", encoding="utf-8").read()
check("desinstalar quita la asociación", "picphotoviewer" not in mime and r.returncode == 0, r.stdout + r.stderr)
check("desinstalar respeta las demás", "text/plain=org.gnome.TextEditor.desktop" in mime)

# ---------------------------------------------------------------- actualizaciones
print("actualizaciones desde GitHub (servidor local)")
from actualizar import github  # noqa: E402
config.set("ultima_busqueda", 0)

check("versiones", github.version_tupla("v0.10.0") > github.version_tupla("0.9.9")
      and github.version_tupla("v1.2") == (1, 2, 0))
srv_dir = os.path.join(TMP, "srv")
os.makedirs(srv_dir)
deb = os.path.join(srv_dir, "picphotoviewer_9.9.9_all.deb")
open(deb, "wb").write(os.urandom(200_000))
h = hashlib.sha256(open(deb, "rb").read()).hexdigest()
open(deb + ".sha256", "w").write(f"{h}  picphotoviewer_9.9.9_all.deb\n")
open(os.path.join(srv_dir, "malo.sha256"), "w").write("0" * 64 + "  x\n")


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=srv_dir, **k)

    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
rel = {"tag_name": "v9.9.9", "body": "Notas", "html_url": "x", "assets": [
    {"name": "picphotoviewer_9.9.9_all.deb", "browser_download_url": base + "/picphotoviewer_9.9.9_all.deb"},
    {"name": "picphotoviewer_9.9.9_all.deb.sha256", "browser_download_url": base + "/picphotoviewer_9.9.9_all.deb.sha256"}]}
info = github.interpretar_release(rel, "0.1.0")
check("release nueva detectada", info is not None and info["version"] == "9.9.9")
check("misma versión no avisa", github.interpretar_release(rel, "9.9.9") is None)
check("prerelease no avisa", github.interpretar_release(dict(rel, prerelease=True), "0.1.0") is None)
check("sin .sha256 no avisa", github.interpretar_release(dict(rel, assets=rel["assets"][:1]), "0.1.0") is None)
ruta = github.descargar_y_verificar(info)
check("descarga verificada", open(ruta, "rb").read() == open(deb, "rb").read())
try:
    github.descargar_y_verificar(dict(info, sha256=base + "/malo.sha256"))
    check("SHA256 distinto se rechaza", False)
except RuntimeError:
    check("SHA256 distinto se rechaza", True)
check("toca buscar la 1ª vez", github.toca_buscar())
config.set("ultima_busqueda", 10**10)
check("no busca dos veces el mismo día", not github.toca_buscar())
srv.shutdown()

# ---------------------------------------------------------------- GDM (copia del tema)
print("ayudante de GDM sobre una copia del tema")
ayud = os.path.join(RAIZ_PROY, "packaging", "helper", "picphotoviewer-gdm")
real = "/usr/share/gnome-shell/gnome-shell-theme.gresource"
if os.path.isfile(real) and shutil.which("glib-compile-resources"):
    raiz = os.path.join(TMP, "raiz")
    os.makedirs(raiz + "/usr/share/gnome-shell")
    shutil.copy(real, raiz + "/usr/share/gnome-shell/")
    copia = raiz + "/usr/share/gnome-shell/gnome-shell-theme.gresource"
    env = dict(os.environ, PPV_RAIZ=raiz)

    def gdm(*a):
        return subprocess.run([sys.executable, ayud, *a], env=env, capture_output=True, text=True)

    jpg = os.path.join(TMP, "gdm.jpg")
    QImage(rojo).save(jpg, "JPG")
    check("estado inicial original", gdm("estado").stdout.strip() == "original")
    check("aplicar", gdm("aplicar", jpg).returncode == 0)
    check("estado aplicado", gdm("estado").stdout.strip() == "aplicado")
    lista = subprocess.run(["gresource", "list", real], capture_output=True, text=True).stdout.split()
    iguales = True
    for rr in lista:
        a = subprocess.run(["gresource", "extract", real, rr], capture_output=True).stdout
        b = subprocess.run(["gresource", "extract", copia, rr], capture_output=True).stdout
        if rr.endswith((".css",)) and "pad-osd" not in rr:
            iguales &= b.startswith(a.rstrip(b"\n")) and b"PicPhotoViewer:inicio" in b
        else:
            iguales &= a == b
    check(f"los {len(lista)} recursos: CSS con el bloque, el resto idéntico", iguales)
    gdm("reaplicar")
    css = subprocess.run(["gresource", "extract", copia, "/org/gnome/shell/theme/gnome-shell-dark.css"],
                         capture_output=True).stdout
    check("reaplicar no duplica", css.count(b"PicPhotoViewer:inicio") == 1)
    shutil.copy(real, copia)  # gnome-shell se actualizó
    gdm("reaplicar")
    check("trigger tras actualizar gnome-shell", gdm("estado").stdout.strip() == "aplicado")
    png_falso = os.path.join(TMP, "falso.jpg")
    shutil.copy(rojo, png_falso)
    check("rechaza lo que no es JPEG", gdm("aplicar", png_falso).returncode != 0)
    gdm("restaurar")
    check("restaurar deja el de fábrica", open(copia, "rb").read() == open(real, "rb").read())
    check("restaurar limpia /var/lib", not os.listdir(raiz + "/var/lib/picphotoviewer"))
else:
    print("  (sin tema de gnome-shell en esta máquina: no se probó)")

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{OK} comprobaciones correctas, {FALLAS} fallas")
sys.exit(1 if FALLAS else 0)
