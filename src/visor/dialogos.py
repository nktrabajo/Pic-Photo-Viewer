"""Diálogos chicos del visor: propiedades, atajos, acerca de."""
import os
from datetime import datetime

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLabel, QMessageBox,
                               QVBoxLayout)

from core import config
from core import idioma
from core.idioma import N, tr
from visor import imagenes

# N(): se traducen al pintarlos (ventana._pintar_ayuda), no al importar
ATAJOS = [
    (N("← / →, Re Pág / Av Pág"), N("Foto anterior / siguiente")),
    (N("Inicio / Fin"), N("Primera / última foto")),
    (N("Rueda del ratón"), N("Acercar / alejar donde está el puntero")),
    ("+ / −", N("Acercar / alejar")),
    (N("1  o  0"), N("Tamaño real (1:1) / ajustar a la pantalla")),
    (N("Doble clic"), N("Alternar tamaño real y ajustado")),
    (N("Arrastrar"), N("Moverse por la foto ampliada")),
    (N("F5  o  Ctrl+Espacio"), N("Presentación")),
    (N("Ctrl+R / Ctrl+Mayús+R"), N("Rotar a la derecha / izquierda")),
    (N("Ctrl+8  o  S"), N("Poner o quitar estrella")),
    ("Ctrl+C", N("Copiar la imagen")),
    ("Ctrl+P", N("Imprimir")),
    ("Ctrl+E", N("Abrir con el editor")),
    (N("Supr"), N("Mover a la papelera")),
    (N("Alt+Intro"), N("Propiedades")),
    (N("Esc  o  clic fuera de la foto"), N("Cerrar")),
]

_EXIF = {
    0x010F: N("Fabricante"), 0x0110: N("Cámara"), 0x9003: N("Fecha de la toma"), 0x829A: N("Exposición"),
    0x829D: N("Apertura (f)"), 0x8827: "ISO", 0x920A: N("Distancia focal (mm)"), 0xA434: N("Lente"),
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
            out.append((tr(nombre), str(v).strip("\x00 ")))
    except Exception:
        pass
    return out


def propiedades(parent, ruta):
    d = QDialog(parent)
    d.setWindowTitle(tr("Propiedades"))
    form = QFormLayout()
    st = os.stat(ruta)
    tam = imagenes.dimensiones(ruta)
    filas = [
        (tr("Nombre"), os.path.basename(ruta)),
        (tr("Carpeta"), os.path.dirname(ruta)),
        (tr("Tamaño"), f"{_bytes(st.st_size)} ({st.st_size:,} bytes)".replace(
            ",", "," if idioma.actual() == "en" else ".")),
        (tr("Dimensiones"), tr("{ancho} × {alto} píxeles", ancho=tam.width(), alto=tam.height()) if tam else "—"),
        (tr("Modificado"), datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")),
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
        parent, tr("Acerca de PicPhotoViewer"),
        tr("<h3>PicPhotoViewer {version}</h3>"
           "<p>Visor de fotos para Linux al estilo del clásico visor de Picasa: "
           "se abre sobre el escritorio, con la tira de fotos de la carpeta abajo.</p>"
           "<p>Proyecto independiente, sin relación con Google. "
           "<a href='https://github.com/nktrabajo/Pic-Photo-Viewer'>github.com/nktrabajo/Pic-Photo-Viewer</a></p>",
           version=config.version()))
