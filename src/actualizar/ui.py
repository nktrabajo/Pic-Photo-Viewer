"""El aviso «Hay una versión nueva, ¿actualizar?» y la descarga, sin trabar el visor."""
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QMessageBox, QProgressDialog

from actualizar import github
from core import config
from core.idioma import tr


class _Hilo(QThread):
    listo = Signal(object)
    progreso = Signal(int)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.listo.emit(("ok", self.fn(self.progreso.emit)))
        except Exception as e:
            self.listo.emit(("error", str(e)))


class Buscador(QObject):
    def __init__(self, ventana, manual=False):
        super().__init__(ventana)
        self.ventana = ventana
        self.manual = manual
        self._hilo = None

    def empezar(self):
        if not self.manual and not github.toca_buscar():
            return
        if self.manual:
            config.set("version_ignorada", "")
        self._hilo = _Hilo(lambda _p: github.buscar())
        self._hilo.listo.connect(self._resultado)
        self._hilo.start()

    def _resultado(self, res):
        tipo, info = res
        if tipo == "error" or info is None:
            if self.manual:
                QMessageBox.information(self.ventana, tr("Actualizaciones"),
                                        tr("Tienes la versión más reciente ({version}).",
                                           version=config.version()))
            return
        caja = QMessageBox(self.ventana)
        caja.setWindowTitle(tr("Actualización disponible"))
        caja.setIcon(QMessageBox.Icon.Information)
        caja.setText(tr("<b>Hay una versión nueva de PicPhotoViewer: {nueva}</b><br>"
                        "Tienes la {version}. ¿Deseas actualizar?",
                        nueva=info["version"], version=config.version()))
        if info["notas"]:
            caja.setDetailedText(info["notas"])
        b_si = caja.addButton(tr("Actualizar"), QMessageBox.ButtonRole.AcceptRole)
        caja.addButton(tr("Ahora no"), QMessageBox.ButtonRole.RejectRole)
        b_nunca = caja.addButton(tr("No avisar de esta versión"), QMessageBox.ButtonRole.DestructiveRole)
        caja.exec()
        if caja.clickedButton() is b_nunca:
            config.set("version_ignorada", info["version"])
        elif caja.clickedButton() is b_si:
            self._descargar(info)

    def _descargar(self, info):
        prog = QProgressDialog(tr("Descargando la actualización…"), None, 0, 100, self.ventana)
        prog.setWindowTitle("PicPhotoViewer")
        prog.setMinimumDuration(0)
        prog.setValue(0)
        self._hilo = _Hilo(lambda p: github.descargar_y_verificar(info, p))
        self._hilo.progreso.connect(prog.setValue)

        def listo(res):
            prog.close()
            tipo, dato = res
            if tipo == "error":
                QMessageBox.warning(self.ventana, tr("Actualización"), tr("No se pudo descargar:\n{error}", error=dato))
                return
            try:
                github.instalar(dato)
            except RuntimeError as e:
                if str(e) != "cancelado":
                    QMessageBox.warning(self.ventana, tr("Actualización"), tr("No se pudo instalar:\n{error}", error=e))
                return
            QMessageBox.information(self.ventana, tr("Actualización"),
                                    tr("PicPhotoViewer {version} quedó instalado.\n"
                                       "Se usará la próxima vez que abras una foto.",
                                       version=info["version"]))
        self._hilo.listo.connect(listo)
        self._hilo.start()
