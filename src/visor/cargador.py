"""Carga de imágenes y miniaturas en hilos, para que la ventana nunca se trabe.

Se trabaja con QImage (seguro entre hilos), nunca con QPixmap fuera del hilo
de la UI. Los resultados vuelven por señal al hilo principal.
"""
from collections import OrderedDict

from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, Signal
from PySide6.QtGui import QImage

from visor import imagenes

LADO_MINI = 96


class _Puente(QObject):
    imagen = Signal(str, QImage, str)   # ruta, imagen, error
    mini = Signal(str, QImage)


class _Tarea(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.setAutoDelete(True)

    def run(self):
        try:
            self.fn()
        except RuntimeError:
            # la ventana se cerró con tareas en cola: el puente ya no existe
            pass


def _mini_cuadrada(ruta):
    img, _ = imagenes.cargar(ruta, maximo=QSize(LADO_MINI * 2, LADO_MINI * 2))
    if img.isNull():
        return img
    img = img.scaled(LADO_MINI, LADO_MINI, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                     Qt.TransformationMode.SmoothTransformation)
    x = (img.width() - LADO_MINI) // 2
    y = (img.height() - LADO_MINI) // 2
    return img.copy(x, y, LADO_MINI, LADO_MINI)


class Cargador(QObject):
    """Caché LRU de imágenes completas (pocas, pesan) y de miniaturas (muchas)."""
    imagen_lista = Signal(str, QImage, str)
    mini_lista = Signal(str)

    MAX_IMAGENES = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(4)
        self._pool_minis = QThreadPool(self)
        self._pool_minis.setMaxThreadCount(2)
        self._puente = _Puente()
        self._puente.imagen.connect(self._recibir_imagen)
        self._puente.mini.connect(self._recibir_mini)
        self._imagenes = OrderedDict()
        self._minis = {}
        self._pendientes = set()
        self._minis_pendientes = set()

    # -- imágenes completas
    def imagen(self, ruta):
        if ruta in self._imagenes:
            self._imagenes.move_to_end(ruta)
            return self._imagenes[ruta]
        return None

    def pedir(self, ruta, prioridad=0):
        if ruta in self._imagenes or ruta in self._pendientes:
            return
        self._pendientes.add(ruta)
        puente = self._puente

        def trabajo():
            img, err = imagenes.cargar(ruta)
            puente.imagen.emit(ruta, img, err)
        self._pool.start(_Tarea(trabajo), prioridad)

    def olvidar(self, ruta):
        self._imagenes.pop(ruta, None)
        self._minis.pop(ruta, None)

    def _recibir_imagen(self, ruta, img, err):
        self._pendientes.discard(ruta)
        if not img.isNull():
            self._imagenes[ruta] = img
            while len(self._imagenes) > self.MAX_IMAGENES:
                self._imagenes.popitem(last=False)
        self.imagen_lista.emit(ruta, img, err)

    # -- miniaturas
    def mini(self, ruta):
        m = self._minis.get(ruta)
        if m is None and ruta not in self._minis_pendientes:
            self._minis_pendientes.add(ruta)
            puente = self._puente
            self._pool_minis.start(_Tarea(lambda: puente.mini.emit(ruta, _mini_cuadrada(ruta))))
        return m

    def _recibir_mini(self, ruta, img):
        self._minis_pendientes.discard(ruta)
        self._minis[ruta] = img
        self.mini_lista.emit(ruta)

    def cancelar_minis(self):
        self._pool_minis.clear()
        self._minis_pendientes.clear()
