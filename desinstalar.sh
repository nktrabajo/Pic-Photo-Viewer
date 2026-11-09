#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# desinstalar.sh — quita PicPhotoViewer del equipo. Uso:
#
#   curl -fsSL https://raw.githubusercontent.com/nktrabajo/Pic-Photo-Viewer/main/desinstalar.sh | bash
#   ./desinstalar.sh --todo        # además borra los datos personales sin preguntar
#
# Qué hace:
#   1. `apt purge picphotoviewer` (se lleva también el repositorio APT que trae el
#      paquete: /etc/apt/sources.list.d/picphotoviewer.sources). El prerm del paquete DEVUELVE el tema original de
#      GDM (si se había puesto un fondo de inicio de sesión) y el postrm borra
#      /var/lib/picphotoviewer.
#   2. Si el fondo de escritorio actual es uno que armó PicPhotoViewer, lo copia a
#      ~/.local/share/backgrounds/ y apunta GNOME ahí: así el escritorio NO queda
#      en gris al borrar los datos del programa.
#   3. Pregunta si borrar los datos personales (preferencias, fondos compuestos,
#      caché). No toca las estrellas (.picasa.ini de cada carpeta): son de Picasa
#      también y siguen sirviendo.
#   4. Quita de ~/.config/mimeapps.list las asociaciones a PicPhotoViewer: las
#      imágenes vuelven a abrirse con el visor de antes.
# ---------------------------------------------------------------------------
set -euo pipefail
case "${LANGUAGE:-${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}}" in es*) ES=1 ;; *) ES=0 ;; esac
m() { if [ "$ES" = 1 ]; then echo "$1"; else echo "$2"; fi; }   # m "español" "english"
TODO=0
[ "${1:-}" = "--todo" ] && TODO=1

DATOS="${XDG_DATA_HOME:-$HOME/.local/share}/picphotoviewer"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/picphotoviewer"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/picphotoviewer"

# 1. el paquete
if dpkg -s picphotoviewer >/dev/null 2>&1; then
  m "Desinstalando el paquete (se restaura el fondo de inicio de sesión original si se cambió)…" "Removing the package (the original login screen background is restored if it was changed)…"
  sudo apt-get purge -y picphotoviewer
else
  m "El paquete picphotoviewer no está instalado." "The picphotoviewer package is not installed."
fi

# 2. rescatar el fondo de escritorio si es nuestro
if command -v gsettings >/dev/null; then
  URI="$(gsettings get org.gnome.desktop.background picture-uri 2>/dev/null | tr -d "'")"
  RUTA="$(python3 -c 'import sys,urllib.parse as u; p=u.urlparse(sys.argv[1]); print(u.unquote(p.path) if p.scheme=="file" else "")' "$URI" 2>/dev/null || true)"
  if [ -n "$RUTA" ] && [ -f "$RUTA" ] && [[ "$RUTA" == "$DATOS"/* ]]; then
    DEST="${XDG_DATA_HOME:-$HOME/.local/share}/backgrounds"
    mkdir -p "$DEST"
    cp -f "$RUTA" "$DEST/"
    NUEVA="file://$(python3 -c 'import sys,urllib.parse as u; print(u.quote(sys.argv[1]))' "$DEST/$(basename "$RUTA")")"
    gsettings set org.gnome.desktop.background picture-uri "$NUEVA"
    gsettings set org.gnome.desktop.background picture-uri-dark "$NUEVA"
    m "Tu fondo de escritorio actual se conservó en $DEST/." "Your current desktop background was kept in $DEST/."
  fi
fi

# 2b. quitar la asociación de imágenes (si no, quedan apuntando a un programa que
#     ya no existe; GNOME lo ignora, pero se deja limpio)
MIMEAPPS="${XDG_CONFIG_HOME:-$HOME/.config}/mimeapps.list"
if [ -f "$MIMEAPPS" ] && grep -q '=picphotoviewer\.desktop;*$' "$MIMEAPPS"; then
  sed -i '/=picphotoviewer\.desktop;*$/d' "$MIMEAPPS"
  m "Las imágenes vuelven a abrirse con el visor que tenías antes." "Images open again with your previous viewer."
fi

# 3. datos personales
HAY=0
for d in "$DATOS" "$CONFIG" "$CACHE"; do [ -e "$d" ] && HAY=1; done
if [ "$HAY" = 1 ]; then
  if [ "$TODO" = 0 ]; then
    # con `curl … | bash` la entrada estándar es el script: se pregunta por la terminal
    RESP="n"
    if [ -r /dev/tty ]; then
      read -r -p "$(m "¿Borrar también tus preferencias y fondos guardados de PicPhotoViewer? [s/N] " "Also delete your PicPhotoViewer preferences and saved backgrounds? [y/N] ")" RESP </dev/tty || RESP="n"
    fi
    [[ "$RESP" =~ ^[sSyY] ]] && TODO=1
  fi
  if [ "$TODO" = 1 ]; then
    rm -rf "$DATOS" "$CONFIG" "$CACHE"
    m "Datos personales borrados." "Personal data deleted."
  else
    m "Se conservaron tus datos en $DATOS y $CONFIG." "Your data was kept in $DATOS and $CONFIG."
  fi
fi

nautilus -q 2>/dev/null || true
m "PicPhotoViewer quedó desinstalado." "PicPhotoViewer has been uninstalled."
