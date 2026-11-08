#!/usr/bin/python3 -I
"""assets/icono-original.png → assets/picphotoviewer.png (1024×1024, limpio).

El original (aportado por el usuario el 2026-11-08) no es cuadrado y trae
píxeles sueltos semitransparentes alrededor del círculo, restos del recorte del
fondo (21.984 fuera de la elipse del logo, alfa hasta 185). Se borra todo lo que cae fuera de la
elipse del logo con un borde suavizado de 1,5 px y se centra en un cuadrado con
un margen del 3 %. Los tamaños por resolución los arma construir_deb.sh.
"""
import os
import numpy as np
from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
im = Image.open(os.path.join(RAIZ, "assets", "icono-original.png")).convert("RGBA")
a = np.array(im).astype(np.float32)
alfa = a[:, :, 3].copy()
ys, xs = np.nonzero(alfa > 200)
x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
yy, xx = np.mgrid[0:alfa.shape[0], 0:alfa.shape[1]]
# distancia normalizada a la elipse, en píxeles aproximados
d = (np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) - 1) * min(rx, ry)
sueltos = int(((d > 2) & (alfa > 0)).sum())
mascara = np.clip(1.5 - d, 0, 1.5) / 1.5
a[:, :, 3] = alfa * mascara
limpio = Image.fromarray(a.astype(np.uint8), "RGBA").crop((int(x0) - 2, int(y0) - 2, int(x1) + 3, int(y1) + 3))
lado = int(max(limpio.size) / 0.94)
lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
lienzo.paste(limpio, ((lado - limpio.width) // 2, (lado - limpio.height) // 2), limpio)
lienzo.resize((1024, 1024), Image.LANCZOS).save(os.path.join(RAIZ, "assets", "picphotoviewer.png"), optimize=True)
quedan = int(((d > 2) & (a[:, :, 3] > 0)).sum())
print(f"píxeles sueltos fuera del logo: {sueltos} → {quedan}; salida 1024×1024")
