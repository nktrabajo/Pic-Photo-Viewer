"""Idioma de la interfaz: español o inglés (decidido 2026-11-08, ver CLAUDE.md 3.10).

Sin Qt Linguist ni gettext: no se compila nada. El texto fuente es el español
tal cual está en el código; `EN` da la traducción al inglés. Uso:

    tr("Abrir carpeta")
    tr("{i} de {n}", i=3, n=12)      # placeholders: se formatea DESPUÉS de traducir

Nunca f-strings dentro de tr(): el texto tiene que ser un literal para que la
prueba estática (tools/pruebas/prueba_todo.py) encuentre su entrada en EN.
Los textos que se definen a nivel de módulo (antes de saber el idioma) se
marcan con N("...") y se traducen al usarlos con tr(variable).

Qué idioma: config `idioma` = auto | es | en (también PPV_IDIOMA). En auto se
miran LANGUAGE (su primer elemento), LC_ALL, LC_MESSAGES y LANG, en ese orden;
la primera que tenga valor decide: «es…» → español, cualquier otra → inglés.
Si falta una traducción se muestra el español: nunca se rompe.

Los mensajes de log NO se traducen: quedan en español a propósito.
"""
import os

from core import config

_actual = None  # caché: el idioma no cambia mientras corre el programa


def N(texto):
    """Marca un literal para traducir más tarde (no traduce)."""
    return texto


def detectar(entorno=None, preferido=None):
    """'es' o 'en'. `entorno` y `preferido` solo para las pruebas."""
    env = os.environ if entorno is None else entorno
    pref = (config.get("idioma") if preferido is None else preferido).strip().lower()
    if pref in ("es", "en"):
        return pref
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        valor = (env.get(var) or "").strip()
        if var == "LANGUAGE":
            valor = valor.split(":")[0].strip()
        if valor:
            return "es" if valor.lower().startswith("es") else "en"
    return "en"


def actual():
    global _actual
    if _actual is None:
        _actual = detectar()
    return _actual


def fijar(idioma=None):
    """Fuerza 'es'/'en' (None = volver a detectar). Para las pruebas."""
    global _actual
    _actual = idioma


def tr(texto, **fmt):
    traducido = EN.get(texto, texto) if actual() == "en" else texto
    if not fmt:
        return traducido
    try:
        return traducido.format(**fmt)
    except (KeyError, IndexError, ValueError):
        # traducción con un {campo} mal escrito: mejor el español que romper
        return texto.format(**fmt)


EN = {
    # ---------------------------------------------------------------- main.py
    "Visor de fotos estilo Picasa": "Picasa-style photo viewer",
    "ruta": "path",
    "imagen o carpeta": "image or folder",
    "IMAGEN": "IMAGE",
    "elegir en qué pantallas va la imagen como fondo de escritorio":
        "choose which screens get the image as desktop background",
    "poner la imagen como fondo de la pantalla de inicio de sesión":
        "set the image as login screen background",
    "devolver el fondo original de la pantalla de inicio de sesión":
        "restore the original login screen background",
    "usar PicPhotoViewer como visor de imágenes predeterminado (sin ventana)":
        "make PicPhotoViewer the default image viewer (no window)",
    "mostrar la versión y salir": "show the version and exit",
    "No se pudo: {error}": "Could not do it: {error}",
    "PicPhotoViewer es ahora el visor de imágenes predeterminado.":
        "PicPhotoViewer is now the default image viewer.",
    "Fondo de escritorio aplicado": "Desktop background set",
    "No se pudo aplicar el fondo:\n{error}": "Could not set the background:\n{error}",
    "Fondo de inicio de sesión": "Login screen background",
    "Se restauró el fondo original de GNOME": "The original GNOME background was restored",
    "Fondo de inicio de sesión aplicado": "Login screen background set",
    "Se verá al cerrar sesión o al reiniciar": "You will see it when you log out or restart",
    "No se pudo cambiar el fondo de inicio de sesión:\n{error}":
        "Could not change the login screen background:\n{error}",
    "Imágenes ({patrones})": "Images ({patrones})",
    "Abrir imagen": "Open image",
    "No existe el archivo:\n{ruta}": "File not found:\n{ruta}",

    # ---------------------------------------------------------------- visor/ventana.py
    "No se pudo abrir la imagen": "Could not open the image",
    "Acercar (+)": "Zoom in (+)",
    "Alejar (−)": "Zoom out (−)",
    "Tamaño real (1)": "Actual size (1)",
    "Abrir con editor": "Open in editor",
    "Abrir con el editor de imágenes (Ctrl+E)": "Open in the image editor (Ctrl+E)",
    "Anterior (←)": "Previous (←)",
    "Presentación (F5)": "Slideshow (F5)",
    "Siguiente (→)": "Next (→)",
    "Abrir carpeta": "Show in folder",
    "Mostrar la foto en su carpeta": "Show the photo in its folder",
    "Rotar a la izquierda (Ctrl+Mayús+R)": "Rotate left (Ctrl+Shift+R)",
    "Rotar a la derecha (Ctrl+R)": "Rotate right (Ctrl+R)",
    "Estrella (Ctrl+8)": "Star (Ctrl+8)",
    "Más opciones": "More options",
    "Cerrar (Esc)": "Close (Esc)",
    "Atajos de teclado": "Keyboard shortcuts",
    "Cargando…": "Loading…",
    "{i} de {n}": "{i} of {n}",
    "Presentación — Esc o clic para salir": "Slideshow — Esc or click to exit",
    "Abriendo en {editor}…": "Opening in {editor}…",
    "Abriendo con la aplicación del sistema…": "Opening with the system application…",
    "No se pudo completar la acción:\n{error}": "Could not complete the action:\n{error}",
    "No hay permiso para modificar este archivo.": "You don't have permission to modify this file.",
    "No se pudo guardar la estrella en .picasa.ini:\n{error}":
        "Could not save the star in .picasa.ini:\n{error}",
    "Imagen copiada": "Image copied",
    "«{nombre}» se envió a la papelera": "“{nombre}” was moved to the Trash",
    "El ayudante de GDM no está instalado (se instala con el .deb).":
        "The GDM helper is not installed (it comes with the .deb package).",
    "Fondo de inicio de sesión aplicado: se verá al cerrar sesión o reiniciar":
        "Login screen background set: you will see it when you log out or restart",
    "Fondo de inicio de sesión original restaurado": "Original login screen background restored",
    "PicPhotoViewer es ahora el visor de imágenes predeterminado":
        "PicPhotoViewer is now the default image viewer",
    "<b>¿Abrir las imágenes con PicPhotoViewer?</b><br>"
    "Al hacer doble clic en una foto se abrirá con este visor.":
        "<b>Open images with PicPhotoViewer?</b><br>"
        "Double-clicking a photo will open it in this viewer.",
    "Sí, usar PicPhotoViewer": "Yes, use PicPhotoViewer",
    "Ahora no": "Not now",
    "No volver a preguntar": "Don't ask again",
    "Copiar imagen": "Copy image",
    "Imprimir…": "Print…",
    "Poner como fondo de escritorio…": "Set as desktop background…",
    "Poner como fondo de inicio de sesión": "Set as login screen background",
    "Restaurar el fondo de inicio de sesión original": "Restore the original login screen background",
    "Mostrar en la carpeta": "Show in folder",
    "Propiedades": "Properties",
    "Mover a la papelera": "Move to Trash",
    "Usar como visor de imágenes predeterminado": "Make default image viewer",
    "Buscar actualizaciones": "Check for updates",
    "Acerca de PicPhotoViewer": "About PicPhotoViewer",

    # ---------------------------------------------------------------- visor/dialogos.py
    "← / →, Re Pág / Av Pág": "← / →, Page Up / Page Down",
    "Foto anterior / siguiente": "Previous / next photo",
    "Inicio / Fin": "Home / End",
    "Primera / última foto": "First / last photo",
    "Rueda del ratón": "Mouse wheel",
    "Acercar / alejar donde está el puntero": "Zoom in / out at the pointer",
    "Acercar / alejar": "Zoom in / out",
    "1  o  0": "1  or  0",
    "Tamaño real (1:1) / ajustar a la pantalla": "Actual size (1:1) / fit to screen",
    "Doble clic": "Double-click",
    "Alternar tamaño real y ajustado": "Toggle actual size and fit",
    "Arrastrar": "Drag",
    "Moverse por la foto ampliada": "Pan around the zoomed photo",
    "F5  o  Ctrl+Espacio": "F5  or  Ctrl+Space",
    "Presentación": "Slideshow",
    "Ctrl+R / Ctrl+Mayús+R": "Ctrl+R / Ctrl+Shift+R",
    "Rotar a la derecha / izquierda": "Rotate right / left",
    "Ctrl+8  o  S": "Ctrl+8  or  S",
    "Poner o quitar estrella": "Add or remove star",
    "Copiar la imagen": "Copy the image",
    "Imprimir": "Print",
    "Abrir con el editor": "Open in the editor",
    "Supr": "Delete",
    "Alt+Intro": "Alt+Enter",
    "Esc  o  clic fuera de la foto": "Esc  or  click outside the photo",
    "Cerrar": "Close",
    "Fabricante": "Make",
    "Cámara": "Camera",
    "Fecha de la toma": "Date taken",
    "Exposición": "Exposure",
    "Apertura (f)": "Aperture (f)",
    "Distancia focal (mm)": "Focal length (mm)",
    "Lente": "Lens",
    "Nombre": "Name",
    "Carpeta": "Folder",
    "Tamaño": "Size",
    "Dimensiones": "Dimensions",
    "{ancho} × {alto} píxeles": "{ancho} × {alto} pixels",
    "Modificado": "Modified",
    "<h3>PicPhotoViewer {version}</h3>"
    "<p>Visor de fotos para Linux al estilo del clásico visor de Picasa: "
    "se abre sobre el escritorio, con la tira de fotos de la carpeta abajo.</p>"
    "<p>Proyecto independiente, sin relación con Google. "
    "<a href='https://github.com/nktrabajo/Pic-Photo-Viewer'>github.com/nktrabajo/Pic-Photo-Viewer</a></p>":
        "<h3>PicPhotoViewer {version}</h3>"
        "<p>Photo viewer for Linux in the style of the classic Picasa viewer: "
        "it opens over your desktop, with the folder's photo strip below.</p>"
        "<p>Independent project, not affiliated with Google. "
        "<a href='https://github.com/nktrabajo/Pic-Photo-Viewer'>github.com/nktrabajo/Pic-Photo-Viewer</a></p>",

    # ---------------------------------------------------------------- fondos/
    "Rellenar": "Fill",
    "Ajustar": "Fit",
    "Centrar": "Center",
    "Estirar": "Stretch",
    "Mosaico": "Tile",
    "  ·  principal": "  ·  primary",
    "Elige en qué pantallas va esta imagen. Clic en una pantalla para marcarla o desmarcarla.":
        "Choose which screens get this image. Click a screen to select or deselect it.",
    "Una sola imagen extendida sobre las pantallas elegidas":
        "One image spanned across the selected screens",
    "Todas": "All",
    "Ninguna": "None",
    "Aplicar": "Apply",
    "Cancelar": "Cancel",
    "Ajuste:": "Fit:",
    "Fondo de escritorio": "Desktop background",
    "Poner como fondo de escritorio": "Set as desktop background",
    "No se detectó ninguna pantalla": "No screen was detected",
    "No se eligió ninguna pantalla": "No screen was selected",
    "No se pudo guardar {destino}": "Could not save {destino}",
    "gsettings {args} falló": "gsettings {args} failed",
    "el ayudante falló": "the helper failed",

    # ---------------------------------------------------------------- actualizar/
    "Actualizaciones": "Updates",
    "Tienes la versión más reciente ({version}).": "You have the latest version ({version}).",
    "Actualización disponible": "Update available",
    "<b>Hay una versión nueva de PicPhotoViewer: {nueva}</b><br>"
    "Tienes la {version}. ¿Deseas actualizar?":
        "<b>A new version of PicPhotoViewer is available: {nueva}</b><br>"
        "You have {version}. Do you want to update?",
    "Actualizar": "Update",
    "No avisar de esta versión": "Skip this version",
    "Descargando la actualización…": "Downloading the update…",
    "Actualización": "Update",
    "No se pudo descargar:\n{error}": "Could not download:\n{error}",
    "No se pudo instalar:\n{error}": "Could not install:\n{error}",
    "PicPhotoViewer {version} quedó instalado.\n"
    "Se usará la próxima vez que abras una foto.":
        "PicPhotoViewer {version} is installed.\n"
        "It will be used the next time you open a photo.",
    "El .sha256 de la release no tiene un hash válido": "The release's .sha256 file has no valid hash",
    "El SHA256 del .deb no coincide con el publicado: no se instala":
        "The .deb's SHA256 does not match the published one: not installing",
    "la instalación falló": "the installation failed",

    # ---------------------------------------------------------------- visor/acciones.py
    "Falta el programa «exiftran» (sudo apt install exiftran).":
        "The “exiftran” program is missing (sudo apt install exiftran).",
    "exiftran falló: {error}": "exiftran failed: {error}",
    "No se rotan imágenes animadas.": "Animated images can't be rotated.",
    "Las fotos RAW no se rotan desde el visor: rótala en tu revelador (darktable, RawTherapee…).":
        "RAW photos can't be rotated from the viewer: rotate it in your raw developer (darktable, RawTherapee…).",
    "No se pudo mandar a la papelera: {error}": "Could not move to the Trash: {error}",
    "xdg-mime falló": "xdg-mime failed",
}
