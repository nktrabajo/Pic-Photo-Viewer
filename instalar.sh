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
# ---------------------------------------------------------------------------
set -euo pipefail
REPO="nktrabajo/Pic-Photo-Viewer"
API="https://api.github.com/repos/$REPO/releases/latest"

bajar() {  # bajar URL DESTINO
  if command -v curl >/dev/null; then curl -fsSL -o "$2" "$1"
  elif command -v wget >/dev/null; then wget -q -O "$2" "$1"
  else echo "Falta curl o wget"; exit 1; fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
chmod 755 "$TMP"   # apt baja privilegios a _apt y tiene que poder leer el .deb

echo "Buscando la última versión de PicPhotoViewer…"
bajar "$API" "$TMP/release.json"
DEB_URL="$(grep -o '"browser_download_url": *"[^"]*picphotoviewer_[^"]*_all\.deb"' "$TMP/release.json" | head -1 | sed 's/.*"\(https[^"]*\)"/\1/')"
[ -n "$DEB_URL" ] || { echo "La última release no tiene un .deb de PicPhotoViewer."; exit 1; }
DEB="$TMP/$(basename "$DEB_URL")"

echo "Descargando $(basename "$DEB")…"
bajar "$DEB_URL" "$DEB"
bajar "$DEB_URL.sha256" "$DEB.sha256"
(cd "$TMP" && sha256sum -c "$(basename "$DEB").sha256") || { echo "El SHA256 no coincide: no se instala."; exit 1; }
chmod 644 "$DEB"

sudo apt-get install -y "$DEB"
nautilus -q 2>/dev/null || true
echo
echo "Listo. Clic derecho en una foto → «Abrir con PicPhotoViewer»."
echo "Para usarlo con doble clic: menú ▼ del visor → «Usar como visor de imágenes predeterminado»."
