"""Diálogos chicos del visor: propiedades, atajos, acerca de."""
import os
from datetime import datetime

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLabel, QMessageBox,
                               QVBoxLayout)

from core import config
from visor import imagenes

ATAJOS = [
    ("← / →, Re Pág / Av Pág", "Foto anterior / siguiente"),
    ("Inicio / Fin", "Primera / última foto"),
    ("Rueda del ratón", "Acercar / alejar donde está el puntero"),
    ("+ / −", "Acercar / alejar"),
    ("1  o  0", "Tamaño real (1:1) / ajustar a la pantalla"),
    ("Doble clic", "Alternar tamaño real y ajustado"),
    ("Arrastrar", "Moverse por la foto ampliada"),
    ("F5  o  Ctrl+Espacio", "Presentación"),
    ("Ctrl+R / Ctrl+Mayús+R", "Rotar a la derecha / izquierda"),
    ("Ctrl+8  o  S", "Poner o quitar estrella"),
    ("Ctrl+C", "Copiar la imagen"),
    ("Ctrl+P", "Imprimir"),
    ("Ctrl+E", "Abrir con el editor"),
    ("Supr", "Mover a la papelera"),
    ("Alt+Intro", "Propiedades"),
    ("Esc  o  clic fuera de la foto", "Cerrar"),
]

_EXIF = {
    0x010F: "Fabricante", 0x0110: "Cámara", 0x9003: "Fecha de la toma", 0x829A: "Exposición",
    0x829D: "Apertura (f)", 0x8827: "ISO", 0x920A: "Distancia focal (mm)", 0xA434: "Lente",
}


def _bytes(n):
    for u in ("bytes", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f} {u}" if u == "bytes" else f"{n:.1f} {u}"
        n /= 1024


def _exif(ruta):
    out = []
    try:
        from PIL import Image
        with Image.open(ruta) as img:
            ex = img.getexif()
            datos = dict(ex)
            try:
                datos.update(ex.get_ifd(0x8769))  # sub-IFD con exposición, ISO…
            except Exception:
                pass
        for tag, nombre in _EXIF.items():
            v = datos.get(tag)
            if v in (None, ""):
                continue
            if tag == 0x829A and float(v) < 1:
                v = f"1/{round(1 / float(v))} s"
            elif tag in (0x829D, 0x920A):
                v = f"{float(v):g}"
            out.append((nombre, str(v).strip("\x00 ")))
    except Exception:
        pass
    return out


def propiedades(parent, ruta):
    d = QDialog(parent)
    d.setWindowTitle("Propiedades")
    form = QFormLayout()
    st = os.stat(ruta)
    tam = imagenes.dimensiones(ruta)
    filas = [
        ("Nombre", os.path.basename(ruta)),
        ("Carpeta", os.path.dirname(ruta)),
        ("Tamaño", f"{_bytes(st.st_size)} ({st.st_size:,} bytes)".replace(",", ".")),
        ("Dimensiones", f"{tam.width()} × {tam.height()} píxeles" if tam else "—"),
        ("Modificado", datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")),
    ] + _exif(ruta)
    for k, v in filas:
        lbl = QLabel(v)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(lbl.textInteractionFlags() | lbl.textInteractionFlags().TextSelectableByMouse)
        form.addRow(f"<b>{k}</b>", lbl)
    botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    botones.rejected.connect(d.reject)
    lay = QVBoxLayout(d)
    lay.addLayout(form)
    lay.addWidget(botones)
    d.setMinimumWidth(460)
    d.exec()


def acerca_de(parent):
    QMessageBox.about(
        parent, "Acerca de PicPhotoViewer",
        f"<h3>PicPhotoViewer {config.version()}</h3>"
        "<p>Visor de fotos para Linux al estilo del clásico visor de Picasa: "
        "se abre sobre el escritorio, con la tira de fotos de la carpeta abajo.</p>"
        "<p>Proyecto independiente, sin relación con Google. "
        "<a href='https://github.com/nktrabajo/Pic-Photo-Viewer'>github.com/nktrabajo/Pic-Photo-Viewer</a></p>")
