"""Punto de entrada de PicPhotoViewer.

    picphotoviewer [imagen|carpeta]      abre el visor
    picphotoviewer --fondo IMAGEN        ventana de pantallas para el fondo de escritorio
    picphotoviewer --fondo-gdm IMAGEN    fondo de la pantalla de inicio de sesión
    picphotoviewer --restaurar-gdm       devuelve el fondo de inicio de sesión original
    picphotoviewer --version

Las opciones --fondo* son las que usa el menú contextual de Nautilus.
"""
import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import config  # noqa: E402
from core.idioma import tr  # noqa: E402
from core.logger import get_logger  # noqa: E402


def _notificar(titulo, texto):
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "-a", "PicPhotoViewer", "-i", "picphotoviewer", titulo, texto])


def _app():
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication
    QApplication.setApplicationName("PicPhotoViewer")
    QApplication.setDesktopFileName("picphotoviewer")
    app = QApplication(sys.argv[:1])
    _traducir_qt(app)
    icono = QIcon.fromTheme("picphotoviewer")
    if icono.isNull():  # corriendo desde el código, sin instalar
        dev = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "picphotoviewer.png")
        if os.path.isfile(dev):
            icono = QIcon(dev)
    app.setWindowIcon(icono)
    return app


def _traducir_qt(app):
    """Los botones estándar de Qt («Close», «OK», el diálogo de imprimir…) en el
    mismo idioma que el resto (3.10). Las traducciones de Qt vienen en
    qt6-translations-l10n; si no está instalado quedan en inglés, sin error."""
    from core import idioma
    if idioma.actual() != "es":
        return
    from PySide6.QtCore import QLibraryInfo, QTranslator
    t = QTranslator(app)
    if t.load("qtbase_es", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(t)
        app._traductor_qt = t  # que no lo recoja el recolector


def _primera_imagen(ruta):
    from visor import imagenes
    if os.path.isdir(ruta):
        lista = imagenes.listar_carpeta(ruta)
        return lista[0] if lista else None
    return ruta


def main(argv=None):
    ap = argparse.ArgumentParser(prog="picphotoviewer", description=tr("Visor de fotos estilo Picasa"))
    ap.add_argument("ruta", nargs="?", metavar=tr("ruta"), help=tr("imagen o carpeta"))
    ap.add_argument("--fondo", metavar=tr("IMAGEN"),
                    help=tr("elegir en qué pantallas va la imagen como fondo de escritorio"))
    ap.add_argument("--fondo-gdm", metavar=tr("IMAGEN"),
                    help=tr("poner la imagen como fondo de la pantalla de inicio de sesión"))
    ap.add_argument("--restaurar-gdm", action="store_true",
                    help=tr("devolver el fondo original de la pantalla de inicio de sesión"))
    ap.add_argument("--predeterminado", action="store_true",
                    help=tr("usar PicPhotoViewer como visor de imágenes predeterminado (sin ventana)"))
    ap.add_argument("--version", action="store_true", help=tr("mostrar la versión y salir"))
    a = ap.parse_args(argv)
    log = get_logger()

    if a.version:
        print(config.version())
        return 0

    if a.predeterminado:
        from visor import acciones
        try:
            acciones.hacer_predeterminado()
        except acciones.ErrorAccion as e:
            print(tr("No se pudo: {error}", error=e), file=sys.stderr)
            return 1
        print(tr("PicPhotoViewer es ahora el visor de imágenes predeterminado."))
        return 0

    app = _app()
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    if a.fondo:
        from fondos.dialogo import elegir_y_aplicar
        try:
            if elegir_y_aplicar(os.path.abspath(a.fondo)):
                _notificar(tr("Fondo de escritorio aplicado"), os.path.basename(a.fondo))
        except Exception as e:
            log.error("No se pudo aplicar el fondo", {"imagen": a.fondo, "error": repr(e)})
            QMessageBox.critical(None, "PicPhotoViewer", tr("No se pudo aplicar el fondo:\n{error}", error=e))
            return 1
        return 0

    if a.fondo_gdm or a.restaurar_gdm:
        from fondos import gdm
        try:
            if a.restaurar_gdm:
                gdm.restaurar()
                _notificar(tr("Fondo de inicio de sesión"), tr("Se restauró el fondo original de GNOME"))
            else:
                gdm.aplicar(os.path.abspath(a.fondo_gdm))
                _notificar(tr("Fondo de inicio de sesión aplicado"),
                           tr("Se verá al cerrar sesión o al reiniciar"))
        except gdm.ErrorGdm as e:
            if str(e) == "cancelado":
                return 1
            log.error("No se pudo cambiar el fondo de GDM", {"error": str(e)})
            QMessageBox.critical(None, "PicPhotoViewer",
                                 tr("No se pudo cambiar el fondo de inicio de sesión:\n{error}", error=e))
            return 1
        return 0

    ruta = a.ruta
    if ruta:
        ruta = _primera_imagen(os.path.abspath(ruta))
    if not ruta:
        from visor.imagenes import extensiones_soportadas
        patrones = " ".join(f"*.{e} *.{e.upper()}" for e in sorted(extensiones_soportadas()))
        filtro = tr("Imágenes ({patrones})", patrones=patrones)
        ruta, _ = QFileDialog.getOpenFileName(None, tr("Abrir imagen"), os.path.expanduser("~/Pictures"), filtro)
        if not ruta:
            return 0
    if not os.path.isfile(ruta):
        QMessageBox.warning(None, "PicPhotoViewer", tr("No existe el archivo:\n{ruta}", ruta=ruta))
        return 1

    from visor.ventana import Visor
    v = Visor(ruta)
    v.mostrar()
    from PySide6.QtCore import QTimer

    from PySide6.QtWidgets import QApplication

    def _buscar():
        try:
            if not v.isVisible():
                return
            if QApplication.activeModalWidget() is not None:
                QTimer.singleShot(5000, _buscar)  # no encimar dos preguntas
                return
            v.buscar_actualizaciones(manual=False)
        except RuntimeError:  # la ventana ya se cerró y Qt la destruyó
            pass

    def _predeterminado():
        try:
            if v.isVisible():
                v.preguntar_predeterminado()
        except RuntimeError:
            pass
    QTimer.singleShot(700, _predeterminado)
    QTimer.singleShot(3000, _buscar)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
