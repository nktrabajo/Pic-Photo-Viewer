"""JPEG incrustados en las fotos RAW, para no decodificar el RAW entero.

Decodificar un CR3 de 24 MP con el plugin `kimg_raw` (LibRaw) tarda ~2,2 s, y se
hacía igual para una miniatura de 96 px: en una carpeta de 1000 fotos la tira
tardaba minutos en llenarse (medido 2026-11-08 con las fotos del usuario).

Las cámaras guardan dentro del RAW uno o varios JPEG ya revelados (una
miniatura, una vista previa y a veces uno del tamaño completo). Leer y
decodificar uno de esos tarda centésimas. Acá se encuentran sin dependencias
nuevas, leyendo solo las cabeceras y los bytes del JPEG elegido:

- **CR3** (contenedor ISO BMFF): THMB (160×120) dentro del uuid 85c0b687… de
  `moov`, PRVW (1620×1080) en el uuid eaf42b5e…, y el JPEG completo, que es la
  muestra de la 1.ª pista (`trak` → `co64`/`stco` + `stsz`). Orientación: CMT1
  (un TIFF con la etiqueta 0x0112).
- **TIFF** (CR2, NEF, ARW, DNG, PEF, SRW, RW2…): todos los IFD (cadena, SubIFDs,
  0x201/0x202, tiras con compresión JPEG, 0x2E JpgFromRaw de Panasonic).
  Orientación: 0x0112 del IFD0.
- **RAF** (Fujifilm): el JPEG cuya posición dice la cabecera; su propia EXIF
  trae la orientación.

Cada candidato se valida leyendo sus marcadores (SOF baseline/progresivo): así
se descartan los JPEG sin pérdida que guardan los datos crudos (Qt no los lee).
Si no hay nada usable se devuelve None y el visor sigue con el RAW completo.
"""
import os
import struct

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QTransform

EXTENSIONES = {"cr3", "cr2", "crw", "nef", "nrw", "arw", "srf", "sr2", "dng", "pef", "srw",
               "rw2", "raf", "orf", "erf", "kdc", "3fr", "iiq", "mos", "mrw", "x3f"}

_UUID_CANON = bytes.fromhex("85c0b687820f11e08111f4ce462b6a48")
_UUID_PRVW = bytes.fromhex("eaf42b5e1c984b88b9fbb7dc406e4d16")
_CABECERA_JPEG = 128 * 1024   # alcanza para pasar la EXIF (APP1 ≤ 64 KB) y llegar al SOF


def es_raw(ruta):
    return os.path.splitext(ruta)[1][1:].lower() in EXTENSIONES


# ---------------------------------------------------------------- búsqueda
def candidatos(ruta):
    """[(desplazamiento, largo)], orientación EXIF (1..8) o None si la da el JPEG."""
    with open(ruta, "rb") as f:
        inicio = f.read(16)
        f.seek(0, os.SEEK_END)
        total = f.tell()
        if inicio[4:12] == b"ftypcrx ":
            return _cr3(f, total)
        if inicio.startswith(b"FUJIFILMCCD-RAW"):
            f.seek(84)
            desp, largo = struct.unpack(">II", f.read(8))
            return [(desp, largo)], None
        if inicio[:2] in (b"II", b"MM"):
            return _tiff(f, 0, total)
    return [], None


def _cajas(f, ini, fin):
    """Cajas ISO BMFF entre ini y fin: (tipo, inicio_datos, fin_caja)."""
    i = ini
    while i + 8 <= fin:
        f.seek(i)
        cab = f.read(16)
        if len(cab) < 8:
            return
        tam, tipo = struct.unpack(">I4s", cab[:8])
        h = 8
        if tam == 1:
            tam = struct.unpack(">Q", cab[8:16])[0]
            h = 16
        elif tam == 0:
            tam = fin - i
        if tam < h:
            return
        yield tipo, i + h, min(i + tam, fin)
        i += tam


def _hijo(f, ini, fin, nombre):
    for tipo, d, e in _cajas(f, ini, fin):
        if tipo == nombre:
            return d, e
    return None


def _cr3(f, total):
    cands, orient = [], None
    for tipo, d, e in _cajas(f, 0, total):
        if tipo == b"moov":
            primera_pista = True
            for t2, d2, e2 in _cajas(f, d, e):
                if t2 == b"uuid":
                    f.seek(d2)
                    if f.read(16) == _UUID_CANON:
                        for t3, d3, e3 in _cajas(f, d2 + 16, e2):
                            if t3 == b"THMB":
                                cands += _jpeg_en(f, d3, e3)
                            elif t3 == b"CMT1":
                                f.seek(d3)
                                orient = _orientacion_tiff(f.read(min(e3 - d3, 65536)))
                elif t2 == b"trak" and primera_pista:
                    primera_pista = False
                    cands += _muestra_pista(f, d2, e2)
        elif tipo == b"uuid":
            f.seek(d)
            if f.read(16) == _UUID_PRVW:
                # 8 bytes sin documentar entre el uuid y la caja PRVW
                for t2, d2, e2 in _cajas(f, d + 24, e):
                    if t2 == b"PRVW":
                        cands += _jpeg_en(f, d2, e2)
    return cands, orient


def _jpeg_en(f, d, e):
    """El JPEG empieza unos bytes después de la cabecera propia de THMB/PRVW."""
    f.seek(d)
    bloque = f.read(min(64, e - d))
    k = bloque.find(b"\xff\xd8\xff")
    return [(d + k, e - d - k)] if k >= 0 else []


def _muestra_pista(f, d, e):
    ruta = [b"mdia", b"minf", b"stbl"]
    for nombre in ruta:
        r = _hijo(f, d, e, nombre)
        if not r:
            return []
        d, e = r
    stsz = _hijo(f, d, e, b"stsz")
    co = _hijo(f, d, e, b"co64") or _hijo(f, d, e, b"stco")
    if not stsz or not co:
        return []
    f.seek(stsz[0])
    _ver, tam, n = struct.unpack(">III", f.read(12))
    if tam == 0 and n:
        tam = struct.unpack(">I", f.read(4))[0]
    f.seek(co[0])
    _ver, n = struct.unpack(">II", f.read(8))
    if not n:
        return []
    es64 = _hijo(f, d, e, b"co64") is not None
    desp = struct.unpack(">Q", f.read(8))[0] if es64 else struct.unpack(">I", f.read(4))[0]
    return [(desp, tam)] if tam else []


# ---------------------------------------------------------------- TIFF
_TAM_TIPO = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8, 13: 4}


def _leer_ifd(leer, base, desp, orden):
    """{etiqueta: (tipo, cantidad, valor_o_desplazamiento_absoluto, bytes_inline)}, siguiente."""
    cab = leer(base + desp, 2)
    if len(cab) < 2:
        return {}, 0
    n = struct.unpack(orden + "H", cab)[0]
    if n == 0 or n > 1000:
        return {}, 0
    datos = leer(base + desp + 2, n * 12 + 4)
    if len(datos) < n * 12 + 4:
        return {}, 0
    ent = {}
    for i in range(n):
        tag, tipo, cant = struct.unpack(orden + "HHI", datos[i * 12:i * 12 + 8])
        crudo = datos[i * 12 + 8:i * 12 + 12]
        ent[tag] = (tipo, cant, crudo)
    sig = struct.unpack(orden + "I", datos[n * 12:n * 12 + 4])[0]
    return ent, sig


def _valores(leer, base, orden, entrada):
    tipo, cant, crudo = entrada
    tam = _TAM_TIPO.get(tipo, 1) * cant
    datos = crudo[:tam] if tam <= 4 else leer(base + struct.unpack(orden + "I", crudo)[0], min(tam, 4096))
    if tipo == 3:
        return list(struct.unpack(orden + "%dH" % (len(datos) // 2), datos[:len(datos) // 2 * 2]))
    if tipo in (4, 13, 9):
        return list(struct.unpack(orden + "%dI" % (len(datos) // 4), datos[:len(datos) // 4 * 4]))
    return []


def _tiff(f, base, total):
    def leer(desp, n):
        f.seek(desp)
        return f.read(n)

    cab = leer(base, 8)
    orden = "<" if cab[:2] == b"II" else ">"
    magia = struct.unpack(orden + "H", cab[2:4])[0]
    if magia not in (42, 0x4F52, 0x5352, 0x55):   # TIFF, ORF (IIRO/MMOR), RW2 (IIU)
        return [], None
    pendientes = [struct.unpack(orden + "I", cab[4:8])[0]]
    vistos, cands, orient = set(), [], None
    primero = True
    while pendientes and len(vistos) < 64:
        desp = pendientes.pop(0)
        if not desp or desp in vistos or desp >= total:
            continue
        vistos.add(desp)
        ent, sig = _leer_ifd(leer, base, desp, orden)
        if primero and 0x0112 in ent:
            v = _valores(leer, base, orden, ent[0x0112])
            orient = v[0] if v and 1 <= v[0] <= 8 else None
        primero = False
        if 0x0201 in ent and 0x0202 in ent:
            o, l = _valores(leer, base, orden, ent[0x0201]), _valores(leer, base, orden, ent[0x0202])
            if o and l:
                cands.append((base + o[0], l[0]))
        if 0x0111 in ent and 0x0117 in ent and 0x0103 in ent:
            comp = _valores(leer, base, orden, ent[0x0103])
            o, l = _valores(leer, base, orden, ent[0x0111]), _valores(leer, base, orden, ent[0x0117])
            if comp and comp[0] in (6, 7) and len(o) == 1 and len(l) == 1:
                cands.append((base + o[0], l[0]))
        if 0x002E in ent:   # Panasonic JpgFromRaw (tipo UNDEFINED)
            _t, cant, crudo = ent[0x002E]
            cands.append((base + struct.unpack(orden + "I", crudo)[0], cant))
        if 0x014A in ent:   # SubIFDs
            pendientes += _valores(leer, base, orden, ent[0x014A])
        pendientes.append(sig)
    return [(o, l) for o, l in cands if 0 < o < total and 0 < l <= total - o], orient


def _orientacion_tiff(datos):
    if len(datos) < 8 or datos[:2] not in (b"II", b"MM"):
        return None
    orden = "<" if datos[:2] == b"II" else ">"
    desp = struct.unpack(orden + "I", datos[4:8])[0]
    if desp + 2 > len(datos):
        return None
    n = struct.unpack(orden + "H", datos[desp:desp + 2])[0]
    for i in range(n):
        p = desp + 2 + i * 12
        if p + 12 > len(datos):
            break
        tag, tipo, _cant = struct.unpack(orden + "HHI", datos[p:p + 8])
        if tag == 0x0112 and tipo == 3:
            v = struct.unpack(orden + "H", datos[p + 8:p + 10])[0]
            return v if 1 <= v <= 8 else None
    return None


# ---------------------------------------------------------------- lectura
# OJO (medido 2026-11-08): NO leer con QImageReader sobre un QBuffer creado desde
# Python. Cada lectura del buffer pasa por el envoltorio de PySide, que toma el
# GIL; con 4 hilos de carga la ventana dejó de pintarse más de 25 s. Por eso la
# cabecera se analiza acá a mano y se decodifica con QImage.fromData.
_SOF_LEGIBLES = {0xC0, 0xC1, 0xC2}   # baseline, extendido, progresivo; C3 = sin pérdida (datos crudos)


def _info_jpeg(datos):
    """(ancho, alto, orientación EXIF o None) leyendo los marcadores, o None si no es
    un JPEG que Qt pueda decodificar."""
    if not datos.startswith(b"\xff\xd8"):
        return None
    i, n, orient = 2, len(datos), None
    while i + 4 <= n:
        if datos[i] != 0xFF:
            return None
        m = datos[i + 1]
        if m == 0xFF:
            i += 1
            continue
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            i += 2
            continue
        largo = struct.unpack(">H", datos[i + 2:i + 4])[0]
        if m == 0xE1 and datos[i + 4:i + 10] == b"Exif\x00\x00":
            orient = _orientacion_tiff(datos[i + 10:i + 2 + largo])
        elif 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
            if m not in _SOF_LEGIBLES or i + 9 > n:
                return None
            alto, ancho = struct.unpack(">HH", datos[i + 5:i + 9])
            return (ancho, alto, orient) if ancho and alto else None
        elif m == 0xDA:
            return None
        i += 2 + largo
    return None


_TRANSFORMACIONES = {  # orientación EXIF → QTransform
    2: QTransform(-1, 0, 0, 1, 0, 0), 3: QTransform().rotate(180), 4: QTransform(1, 0, 0, -1, 0, 0),
    5: QTransform(0, 1, 1, 0, 0, 0), 6: QTransform().rotate(90), 7: QTransform(0, -1, -1, 0, 0, 0),
    8: QTransform().rotate(270),
}


def vista_previa(ruta, maximo=None, lado_real=None):
    """QImage de un JPEG incrustado, orientado, o None.

    maximo (QSize): se elige el JPEG más chico que lo cubra y se reduce.
    Sin maximo (vista completa): el más grande, y solo si su lado mayor llega al
    90 % de `lado_real` (el del RAW): si la cámara guardó solo una vista previa
    chica, mejor el RAW entero que mostrar una foto de 1600 px como si fuera la real.
    """
    try:
        cands, orient = candidatos(ruta)
        if not cands:
            return None
        with open(ruta, "rb") as f:
            medidos = []
            for desp, largo in cands:
                f.seek(desp)
                info = _info_jpeg(f.read(min(largo, _CABECERA_JPEG)))
                if info is not None:
                    medidos.append((max(info[0], info[1]), desp, largo, info))
            if not medidos:
                return None
            medidos.sort()
            if maximo is not None:
                lado = max(maximo.width(), maximo.height())
                # primero los que cubren el tamaño pedido (de menor a mayor), después los demás
                orden = [m for m in medidos if m[0] >= lado] + [m for m in reversed(medidos) if m[0] < lado]
            else:
                orden = list(reversed(medidos))
            img = None
            for lado_m, desp, largo, info in orden:
                if maximo is None and lado_real and lado_m < 0.9 * lado_real:
                    return None
                f.seek(desp)
                img = QImage.fromData(f.read(largo), "JPEG")
                if not img.isNull():
                    break
            if img is None or img.isNull():
                return None
        if orient is None:   # sin orientación del RAW, manda la EXIF del propio JPEG
            orient = info[2]
        if maximo is not None:
            lado = max(maximo.width(), maximo.height())
            if max(img.width(), img.height()) > lado:
                img = img.scaled(lado, lado, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
        if orient in _TRANSFORMACIONES:
            img = img.transformed(_TRANSFORMACIONES[orient], Qt.TransformationMode.SmoothTransformation)
        return img
    except (OSError, struct.error, ValueError):
        return None
