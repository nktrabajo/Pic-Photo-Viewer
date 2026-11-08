"""Menú contextual de Nautilus para PicPhotoViewer (nautilus-python, API 4.0).

Se instala en /usr/share/nautilus-python/extensions/. Nautilus lo carga al
arrancar: después de instalar el .deb hay que cerrar Nautilus (`nautilus -q`)
o cerrar sesión.
"""
import subprocess

from gi.repository import GObject, Nautilus

PROGRAMA = "/usr/bin/picphotoviewer"


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
        abrir = Nautilus.MenuItem(name="PicPhotoViewer::abrir", label="Abrir con PicPhotoViewer",
                                  icon="picphotoviewer")
        abrir.connect("activate", lambda *_: _lanzar(ruta))
        items.append(abrir)

        fondo = Nautilus.MenuItem(name="PicPhotoViewer::fondo", label="Poner como fondo de escritorio…",
                                  icon="preferences-desktop-wallpaper")
        fondo.connect("activate", lambda *_: _lanzar("--fondo", ruta))
        items.append(fondo)

        gdm = Nautilus.MenuItem(name="PicPhotoViewer::gdm", label="Poner como fondo de inicio de sesión",
                                icon="system-lock-screen")
        gdm.connect("activate", lambda *_: _lanzar("--fondo-gdm", ruta))
        items.append(gdm)
        return items
