"""Logger estándar ITCorp (plantilla de ESTANDAR-ITCorp.md §14.2).

- Directorio: ~/Logs/
- Un archivo POR EJECUCIÓN: PicPhotoViewer-YYYY-MM-DD_HH-MM-SS.txt
- Línea: [YYYY-MM-DD HH:MM:SS] [LEVEL] Mensaje | {"contexto":"json"}
- El archivo se crea recién al PRIMER log: abrir una foto y cerrarla no deja
  archivo. Solo se registran acciones (fondo aplicado, rotación, papelera,
  actualización) y errores, así que la carpeta no se llena de logs vacíos.

Un visor de escritorio se abre muchas veces al día; por eso se conservan solo los
últimos MAX_ARCHIVOS logs de este programa (se poda al crear uno nuevo).
"""
import glob
import json
import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.expanduser("~"), "Logs")
PREFIJO = "PicPhotoViewer"
MAX_ARCHIVOS = 50

_logger = None


class Logger:
    def __init__(self, prefijo=PREFIJO, consola=False):
        self.prefijo = prefijo
        self.consola = consola
        self._path = None

    def _archivo(self):
        if self._path is None:
            os.makedirs(LOG_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self._path = os.path.join(LOG_DIR, f"{self.prefijo}-{ts}.txt")
            self._podar()
        return self._path

    def _podar(self):
        try:
            viejos = sorted(glob.glob(os.path.join(LOG_DIR, f"{self.prefijo}-*.txt")))
            for p in viejos[:-(MAX_ARCHIVOS - 1)] if len(viejos) >= MAX_ARCHIVOS else []:
                os.remove(p)
        except OSError:
            pass

    def _log(self, nivel, mensaje, contexto=None):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linea = f"[{ts}] [{nivel}] {mensaje}"
        if contexto is not None:
            linea += " | " + json.dumps(contexto, ensure_ascii=False, default=str)
        try:
            with open(self._archivo(), "a", encoding="utf-8") as f:
                f.write(linea + "\n")
        except OSError:
            pass  # un log que no se puede escribir nunca tumba el visor
        if self.consola:
            print(linea)

    def info(self, mensaje, contexto=None):
        self._log("INFO", mensaje, contexto)

    def warning(self, mensaje, contexto=None):
        self._log("WARNING", mensaje, contexto)

    def error(self, mensaje, contexto=None):
        self._log("ERROR", mensaje, contexto)


def get_logger(consola=False):
    global _logger
    if _logger is None:
        _logger = Logger(consola=consola)
    return _logger
