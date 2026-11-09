#!/usr/bin/env python3
"""Dibuja el ícono de PicPhotoViewer con PIL, sin recursos externos.

    python3 -I tools/dibujar_icono.py

Escribe assets/picphotoviewer.png (1024×1024; de ahí construir_deb.sh saca los
tamaños del tema hicolor) y assets/vista-previa-social.png (1280×640).

Diseño elegido por el usuario (2026-11-08, v0.2.0): el propio visor —una foto
sobre fondo oscuro con la tira de miniaturas debajo— con un pingüino al estilo de
Tux en el paisaje. Reemplaza al ícono anterior, que se parecía demasiado al logo
de Picasa (marca de Google). Se dibuja a 4x y se reduce (antialias).
"""
import math
import sys

from PIL import Image, ImageDraw, ImageFilter

SS = 4


def degradado(w, h, arriba, abajo):
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(arriba[i] + (abajo[i] - arriba[i]) * t) for i in range(3)) + (255,)
        for x in range(w):
            px[x, y] = c
    return img


def degradado_rapido(w, h, arriba, abajo):
    col = degradado(1, h, arriba, abajo)
    return col.resize((w, h))


def paisaje(w, h, sol=True, tux=False):
    """Cielo + sol + dos montañas + lago: la «foto» genérica."""
    img = degradado_rapido(w, h, (86, 170, 245), (190, 228, 255))
    d = ImageDraw.Draw(img)
    if sol:
        r = h * 0.11
        cx, cy = w * 0.72, h * 0.27
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 205, 60))
    d.polygon([(-w * 0.05, h * 0.78), (w * 0.33, h * 0.36), (w * 0.62, h * 0.78)], fill=(52, 128, 88))
    d.polygon([(w * 0.33, h * 0.36), (w * 0.26, h * 0.46), (w * 0.31, h * 0.44),
               (w * 0.35, h * 0.48), (w * 0.40, h * 0.45)], fill=(240, 248, 255))
    d.polygon([(w * 0.30, h * 0.80), (w * 0.68, h * 0.44), (w * 1.08, h * 0.80)], fill=(34, 98, 72))
    d.rectangle([0, h * 0.76, w, h], fill=(64, 140, 210))
    d.rectangle([0, h * 0.76, w, h * 0.785], fill=(120, 185, 235))
    if tux:  # orilla de arena en primer plano con el pingüino parado
        d.ellipse([-w * 0.25, h * 0.80, w * 0.62, h * 1.35], fill=(236, 214, 160))
        pinguino(d, w * 0.25, h * 0.93, h * 0.62)
    return img


def pinguino(d, cx, base, h):
    """Pingüino al estilo de Tux, dibujado con formas simples (no es el dibujo de Larry Ewing)."""
    negro, blanco, naranja = (22, 22, 26), (250, 250, 250), (246, 168, 28)
    w = h * 0.66
    # aletas
    d.ellipse([cx - w * 0.62, base - h * 0.62, cx - w * 0.22, base - h * 0.12], fill=negro)
    d.ellipse([cx + w * 0.22, base - h * 0.62, cx + w * 0.62, base - h * 0.12], fill=negro)
    # cuerpo y cabeza
    d.ellipse([cx - w / 2, base - h * 0.78, cx + w / 2, base - h * 0.02], fill=negro)
    rc = h * 0.25
    d.ellipse([cx - rc, base - h - h * 0.0, cx + rc, base - h + 2 * rc], fill=negro)
    # panza
    d.ellipse([cx - w * 0.34, base - h * 0.58, cx + w * 0.34, base - h * 0.05], fill=blanco)
    # ojos
    oy = base - h * 0.84
    for s in (-1, 1):
        ox = cx + s * h * 0.085
        d.ellipse([ox - h * 0.065, oy - h * 0.085, ox + h * 0.065, oy + h * 0.085], fill=blanco)
        px = ox + s * h * 0.018
        d.ellipse([px - h * 0.03, oy - h * 0.025, px + h * 0.03, oy + h * 0.045], fill=negro)
    # pico
    d.polygon([(cx - h * 0.12, base - h * 0.73), (cx + h * 0.12, base - h * 0.73), (cx, base - h * 0.63)], fill=naranja)
    d.ellipse([cx - h * 0.12, base - h * 0.78, cx + h * 0.12, base - h * 0.69], fill=naranja)
    # patas
    for s in (-1, 1):
        fx = cx + s * w * 0.24
        d.ellipse([fx - w * 0.26, base - h * 0.07, fx + w * 0.26, base + h * 0.05], fill=naranja)


def mascara_redondeada(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    return m


def sombra(lienzo, caja, radio, desenfoque, opacidad=110, desplaz=(0, 0), angulo=0):
    w, h = lienzo.size
    s = Image.new("L", (w, h), 0)
    x0, y0, x1, y1 = caja
    capa = Image.new("L", (int(x1 - x0), int(y1 - y0)), 0)
    ImageDraw.Draw(capa).rounded_rectangle([0, 0, capa.width - 1, capa.height - 1], radio, fill=opacidad)
    if angulo:
        capa = capa.rotate(angulo, resample=Image.BICUBIC, expand=True)
    cx, cy = (x0 + x1) / 2 + desplaz[0], (y0 + y1) / 2 + desplaz[1]
    s.paste(capa, (int(cx - capa.width / 2), int(cy - capa.height / 2)), capa)
    s = s.filter(ImageFilter.GaussianBlur(desenfoque))
    negro = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    negro.putalpha(s)
    lienzo.alpha_composite(negro)


def tarjeta(w, h, marco, radio, contenido, base=(255, 255, 255)):
    """Foto con borde blanco (polaroid-ish), RGBA."""
    t = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(t).rounded_rectangle([0, 0, w - 1, h - 1], radio, fill=base + (255,))
    iw, ih = w - 2 * marco, h - 2 * marco
    foto = contenido(iw, ih)
    t.paste(foto, (marco, marco), mascara_redondeada(iw, ih, max(1, radio // 2)))
    return t


def pegar_rotada(lienzo, img, centro, angulo):
    r = img.rotate(angulo, resample=Image.BICUBIC, expand=True)
    lienzo.alpha_composite(r, (int(centro[0] - r.width / 2), int(centro[1] - r.height / 2)))


# --- el ícono: la foto sobre el escritorio con la tira debajo (el propio visor) --
def icono(S):
    lienzo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    m = S * 0.06
    caja = (m, m, S - m, S - m)
    sombra(lienzo, caja, int(S * 0.2), S * 0.02, 110, (0, S * 0.015))
    fondo = degradado_rapido(int(S - 2 * m), int(S - 2 * m), (52, 60, 78), (22, 26, 36))
    lienzo.paste(fondo, (int(m), int(m)), mascara_redondeada(fondo.width, fondo.height, int(S * 0.2)))
    d = ImageDraw.Draw(lienzo)
    # foto principal
    fw, fh = int(S * 0.62), int(S * 0.44)
    fx, fy = int((S - fw) / 2), int(S * 0.18)
    sombra(lienzo, (fx, fy, fx + fw, fy + fh), int(S * 0.02), S * 0.02, 160, (0, S * 0.012))
    foto = tarjeta(fw, fh, int(S * 0.018), int(S * 0.025), lambda a, b: paisaje(a, b, tux=True))
    lienzo.alpha_composite(foto, (fx, fy))
    # tira de miniaturas
    n, tw, th, sep = 4, int(S * 0.11), int(S * 0.08), int(S * 0.025)
    total = n * tw + (n - 1) * sep
    x = (S - total) / 2
    y = S * 0.70
    colores = [((255, 170, 90), (230, 90, 120)), None, ((120, 210, 160), (40, 120, 110)),
               ((200, 170, 255), (110, 90, 200))]
    for i in range(n):
        caja_t = [x, y, x + tw, y + th]
        if colores[i] is None:  # la miniatura actual: la misma foto, resaltada
            d.rounded_rectangle([x - S * 0.012, y - S * 0.012, x + tw + S * 0.012, y + th + S * 0.012],
                                int(S * 0.02), fill=(255, 255, 255))
            mini = paisaje(tw, th)
        else:
            mini = degradado_rapido(tw, th, *colores[i])
        lienzo.paste(mini, (int(x), int(y)), mascara_redondeada(tw, th, int(S * 0.012)))
        x += tw + sep
    return lienzo




def dibujar(tam=1024):
    return icono(tam * SS).resize((tam, tam), Image.LANCZOS)


def vista_previa_social(icono_img, salida):
    """1280×640 para la «Social preview» del repo (se sube a mano en Settings)."""
    from PIL import ImageFont
    W, H = 1280, 640
    img = degradado_rapido(W, H, (40, 46, 62), (16, 19, 27))
    img.alpha_composite(icono_img.resize((400, 400), Image.LANCZOS), (90, 120))
    d = ImageDraw.Draw(img)

    def fuente(tam, negrita=False):
        for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if negrita else ""),):
            try:
                return ImageFont.truetype(f, tam)
            except OSError:
                pass
        return ImageFont.load_default()

    d.text((560, 220), "PicPhotoViewer", font=fuente(72, True), fill=(245, 247, 250))
    d.text((562, 320), "A photo viewer that opens over", font=fuente(34), fill=(185, 194, 210))
    d.text((562, 365), "your desktop, Picasa style.", font=fuente(34), fill=(185, 194, 210))
    d.text((562, 440), "Debian · GNOME · .deb / APT", font=fuente(26), fill=(120, 170, 240))
    img.convert("RGB").save(salida)


if __name__ == "__main__":
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    grande = dibujar(1024)
    grande.save(os.path.join(raiz, "assets", "picphotoviewer.png"), optimize=True)
    vista_previa_social(grande, os.path.join(raiz, "assets", "vista-previa-social.png"))
    print("assets/picphotoviewer.png y assets/vista-previa-social.png")
