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
    app.setWindowIcon(QIcon.fromTheme("picphotoviewer"))
    return app


def _primera_imagen(ruta):
    from visor import imagenes
    if os.path.isdir(ruta):
        lista = imagenes.listar_carpeta(ruta)
        return lista[0] if lista else None
    return ruta


def main(argv=None):
    ap = argparse.ArgumentParser(prog="picphotoviewer", description="Visor de fotos estilo Picasa")
    ap.add_argument("ruta", nargs="?", help="imagen o carpeta")
    ap.add_argument("--fondo", metavar="IMAGEN")
    ap.add_argument("--fondo-gdm", metavar="IMAGEN")
    ap.add_argument("--restaurar-gdm", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args(argv)
    log = get_logger()

    if a.version:
        print(config.version())
        return 0

    app = _app()
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    if a.fondo:
        from fondos.dialogo import elegir_y_aplicar
        try:
            if elegir_y_aplicar(os.path.abspath(a.fondo)):
                _notificar("Fondo de escritorio aplicado", os.path.basename(a.fondo))
        except Exception as e:
            log.error("No se pudo aplicar el fondo", {"imagen": a.fondo, "error": repr(e)})
            QMessageBox.critical(None, "PicPhotoViewer", f"No se pudo aplicar el fondo:\n{e}")
            return 1
        return 0

    if a.fondo_gdm or a.restaurar_gdm:
        from fondos import gdm
        try:
            if a.restaurar_gdm:
                gdm.restaurar()
                _notificar("Fondo de inicio de sesión", "Se restauró el fondo original de GNOME")
            else:
                gdm.aplicar(os.path.abspath(a.fondo_gdm))
                _notificar("Fondo de inicio de sesión aplicado",
                           "Se verá al cerrar sesión o al reiniciar")
        except gdm.ErrorGdm as e:
            if str(e) == "cancelado":
                return 1
            log.error("No se pudo cambiar el fondo de GDM", {"error": str(e)})
            QMessageBox.critical(None, "PicPhotoViewer",
                                 f"No se pudo cambiar el fondo de inicio de sesión:\n{e}")
            return 1
        return 0

    ruta = a.ruta
    if ruta:
        ruta = _primera_imagen(os.path.abspath(ruta))
    if not ruta:
        from visor.imagenes import extensiones_soportadas
        filtro = "Imágenes (" + " ".join(f"*.{e} *.{e.upper()}" for e in sorted(extensiones_soportadas())) + ")"
        ruta, _ = QFileDialog.getOpenFileName(None, "Abrir imagen", os.path.expanduser("~/Pictures"), filtro)
        if not ruta:
            return 0
    if not os.path.isfile(ruta):
        QMessageBox.warning(None, "PicPhotoViewer", f"No existe el archivo:\n{ruta}")
        return 1

    from visor.ventana import Visor
    v = Visor(ruta)
    v.mostrar()
    from PySide6.QtCore import QTimer

    def _buscar():
        try:
            if v.isVisible():
                v.buscar_actualizaciones(manual=False)
        except RuntimeError:  # la ventana ya se cerró y Qt la destruyó
            pass
    QTimer.singleShot(3000, _buscar)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
