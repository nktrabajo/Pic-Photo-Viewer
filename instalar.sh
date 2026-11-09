#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# instalar.sh — instala (o actualiza) PicPhotoViewer desde la última Release de
# GitHub. Uso:
#
#   curl -fsSL https://raw.githubusercontent.com/nktrabajo/Pic-Photo-Viewer/main/instalar.sh | bash
#
# Baja el .deb y su .sha256 a un directorio temporal LOCAL (apt corre como root
# y no puede leer, por ejemplo, un montaje SSHFS), verifica el hash, instala con
# apt (resuelve dependencias) y reinicia Nautilus para que cargue el menú.
# Desde la 0.2.0 el paquete trae el repositorio APT propio
# (/etc/apt/sources.list.d/picphotoviewer.sources): lo que sigue llega con
# `apt upgrade`.
#
# Mensajes en español si el idioma del sistema es español; si no, en inglés.
# ---------------------------------------------------------------------------
set -euo pipefail
REPO="nktrabajo/Pic-Photo-Viewer"
API="https://api.github.com/repos/$REPO/releases/latest"

case "${LANGUAGE:-${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}}" in es*) ES=1 ;; *) ES=0 ;; esac
m() { if [ "$ES" = 1 ]; then echo "$1"; else echo "$2"; fi; }   # m "español" "english"

bajar() {  # bajar URL DESTINO
  if command -v curl >/dev/null; then curl -fsSL -o "$2" "$1"
  elif command -v wget >/dev/null; then wget -q -O "$2" "$1"
  else m "Falta curl o wget." "curl or wget is required."; exit 1; fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
chmod 755 "$TMP"   # apt baja privilegios a _apt y tiene que poder leer el .deb

m "Buscando la última versión de PicPhotoViewer…" "Looking for the latest PicPhotoViewer release…"
bajar "$API" "$TMP/release.json"
DEB_URL="$(grep -o '"browser_download_url": *"[^"]*picphotoviewer_[^"]*_all\.deb"' "$TMP/release.json" | head -1 | sed 's/.*"\(https[^"]*\)"/\1/')"
[ -n "$DEB_URL" ] || { m "La última release no tiene un .deb de PicPhotoViewer." "The latest release has no PicPhotoViewer .deb."; exit 1; }
DEB="$TMP/$(basename "$DEB_URL")"

m "Descargando $(basename "$DEB")…" "Downloading $(basename "$DEB")…"
bajar "$DEB_URL" "$DEB"
bajar "$DEB_URL.sha256" "$DEB.sha256"
(cd "$TMP" && sha256sum -c "$(basename "$DEB").sha256") || { m "El SHA256 no coincide: no se instala." "SHA256 mismatch: not installing."; exit 1; }
chmod 644 "$DEB"

sudo apt-get install -y "$DEB"
nautilus -q 2>/dev/null || true

# Asociar las imágenes: es por usuario (~/.config/mimeapps.list), por eso lo
# hace este script —que corre como el usuario— y no el .deb, que corre como root.
# Con `curl … | bash` la entrada estándar es el script: se pregunta por la terminal.
echo
RESP="s"
if [ -r /dev/tty ]; then
  # sin terminal: no asociar sin preguntar
  read -r -p "$(m "¿Abrir las imágenes con PicPhotoViewer al hacer doble clic? [S/n] " "Open images with PicPhotoViewer on double-click? [Y/n] ")" RESP </dev/tty || RESP="n"
fi
if [[ ! "$RESP" =~ ^[nN] ]]; then
  picphotoviewer --predeterminado || m "No se pudo asociar; se puede hacer después desde el menú ▼ del visor." "Could not set it as default; you can do it later from the viewer's ▼ menu."
else
  m "No se asociaron. El visor lo va a ofrecer la primera vez que lo abras." "Not set as default. The viewer will offer it the first time you open it."
fi
echo
m "Listo. Clic derecho en una foto → «Abrir con PicPhotoViewer»." "Done. Right-click a photo → “Open With PicPhotoViewer”."
m "Las próximas versiones llegan con «sudo apt upgrade»." "Future versions arrive with “sudo apt upgrade”."
