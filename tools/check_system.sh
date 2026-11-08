#!/usr/bin/env bash
# check_system.sh — diagnóstico SOLO LECTURA de PicPhotoViewer en este equipo.
# No cambia nada: no toca gsettings, ni el tema de GDM, ni instala.
ok()   { printf '  \033[32m✔\033[0m %s\n' "$*"; }
mal()  { printf '  \033[31m✘\033[0m %s\n' "$*"; }
info() { printf '    %s\n' "$*"; }

echo "Instalación"
if dpkg -s picphotoviewer >/dev/null 2>&1; then ok "paquete $(dpkg-query -W -f='${Version}' picphotoviewer)"; else mal "paquete no instalado"; fi
for b in python3 exiftran gresource glib-compile-resources pkexec xdg-mime gsettings; do
  command -v "$b" >/dev/null && ok "$b" || mal "falta $b"
done
python3 -c "import PySide6, PIL" 2>/dev/null && ok "PySide6 + PIL" || mal "faltan PySide6 o PIL"
[ -f /usr/share/nautilus-python/extensions/picphotoviewer-nautilus.py ] && ok "extensión de Nautilus" || mal "sin extensión de Nautilus"
python3 -c "import gi; gi.require_version('Nautilus','4.0')" 2>/dev/null && ok "python3-nautilus 4.0" || mal "sin python3-nautilus (no habrá menú contextual)"

echo "Escritorio"
info "sesión: ${XDG_SESSION_TYPE:-?}  escritorio: ${XDG_CURRENT_DESKTOP:-?}  $(gnome-shell --version 2>/dev/null)"
info "fondo: $(gsettings get org.gnome.desktop.background picture-uri 2>/dev/null)  ($(gsettings get org.gnome.desktop.background picture-options 2>/dev/null))"
command -v xrandr >/dev/null && xrandr --listmonitors 2>/dev/null | sed 's/^/    /'
info "visor predeterminado para JPEG: $(xdg-mime query default image/jpeg 2>/dev/null)"

echo "GDM"
T=/usr/share/gnome-shell/gnome-shell-theme.gresource
if [ -f "$T" ]; then
  if gresource extract "$T" /org/gnome/shell/theme/gnome-shell-dark.css 2>/dev/null | grep -q 'PicPhotoViewer:inicio'; then
    ok "tema con el fondo de PicPhotoViewer"
  else
    info "tema de fábrica (sin fondo propio)"
  fi
  [ -f /var/lib/picphotoviewer/gnome-shell-theme.gresource.original ] && info "copia del original: /var/lib/picphotoviewer/" || true
else
  mal "no existe $T (¿no es GNOME?)"
fi

echo "Logs: $(ls "$HOME"/Logs/PicPhotoViewer-*.txt 2>/dev/null | wc -l) archivos en ~/Logs"
