"""Menú contextual de Nautilus para PicPhotoViewer (nautilus-python, API 4.0).

Se instala en /usr/share/nautilus-python/extensions/. Nautilus lo carga al
arrancar: después de instalar el .deb hay que cerrar Nautilus (`nautilus -q`)
o cerrar sesión.

Idioma (3.10 del CLAUDE.md): corre dentro de Nautilus, con otro sys.path, así
que NO importa core/; repite acá la misma regla que src/core/idioma.py
(config `idioma` auto|es|en, y en auto LANGUAGE, LC_ALL, LC_MESSAGES, LANG).
"""
import configparser
import os
import subprocess

from gi.repository import GObject, Nautilus

PROGRAMA = "/usr/bin/picphotoviewer"

EN = {
    "Abrir con PicPhotoViewer": "Open with PicPhotoViewer",
    "Poner como fondo de escritorio…": "Set as desktop background…",
    "Poner como fondo de inicio de sesión": "Set as login screen background",
}


def _idioma():
    pref = os.environ.get("PPV_IDIOMA")
    if pref is None:
        cp = configparser.ConfigParser()
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        try:
            cp.read(os.path.join(base, "picphotoviewer", "config.ini"), encoding="utf-8")
        except (configparser.Error, OSError):
            pass
        pref = cp.get("general", "idioma", fallback="auto")
    pref = pref.strip().lower()
    if pref in ("es", "en"):
        return pref
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        valor = (os.environ.get(var) or "").strip()
        if var == "LANGUAGE":
            valor = valor.split(":")[0].strip()
        if valor:
            return "es" if valor.lower().startswith("es") else "en"
    return "en"


def tr(texto):
    return EN.get(texto, texto) if _idioma() == "en" else texto


def _ruta_local(f):
    if f.get_uri_scheme() != "file" or f.is_directory():
        return None
    loc = f.get_location()
    return loc.get_path() if loc else None


def _lanzar(*args):
    subprocess.Popen([PROGRAMA, *args], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class PicPhotoViewerMenu(GObject.GObject, Nautilus.MenuProvider):
    def get_file_items(self, *args):
        files = args[-1]  # API 3.0 pasaba (window, files); la 4.0 solo (files)
        if len(files) != 1:
            return []
        f = files[0]
        if not (f.get_mime_type() or "").startswith("image/"):
            return []
        ruta = _ruta_local(f)
        if not ruta:
            return []

        items = []
        abrir = Nautilus.MenuItem(name="PicPhotoViewer::abrir", label=tr("Abrir con PicPhotoViewer"),
                                  icon="picphotoviewer")
        abrir.connect("activate", lambda *_: _lanzar(ruta))
        items.append(abrir)

        fondo = Nautilus.MenuItem(name="PicPhotoViewer::fondo", label=tr("Poner como fondo de escritorio…"),
                                  icon="preferences-desktop-wallpaper")
        fondo.connect("activate", lambda *_: _lanzar("--fondo", ruta))
        items.append(fondo)

        gdm = Nautilus.MenuItem(name="PicPhotoViewer::gdm", label=tr("Poner como fondo de inicio de sesión"),
                                icon="system-lock-screen")
        gdm.connect("activate", lambda *_: _lanzar("--fondo-gdm", ruta))
        items.append(gdm)
        return items
