#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# publicar_apt.sh — agrega el .deb de VERSION al repositorio APT que se sirve
# desde GitHub Pages (rama gh-pages) y lo firma.
#
#   ./tools/publicar_apt.sh                 (lo llama publicar_release.sh)
#   ./tools/publicar_apt.sh --local DIR     arma el sitio en DIR y NO sube nada (pruebas)
#
# Resultado:  https://nktrabajo.github.io/Pic-Photo-Viewer/
#   dists/stable/{Release,InRelease,Release.gpg}
#   dists/stable/main/binary-{all,amd64,arm64,armhf,i386}/Packages(.gz)
#   pool/main/p/picphotoviewer/*.deb       (se conservan las últimas 3 versiones)
#   picphotoviewer-archive-keyring.gpg, picphotoviewer.sources, index.html
#
# El paquete es Architecture: all, pero apt busca binary-<arquitectura del
# equipo>: sin esas carpetas, cada `apt update` mostraría un aviso. Por eso el
# mismo Packages va en todas.
#
# Firma: clave ed25519 SIN contraseña en $GNUPGHOME (por defecto
# ~/.local/share/picphotoviewer-apt-firma, FUERA del repo). Si se pierde, los
# equipos instalados dejan de recibir actualizaciones por apt hasta reinstalar el
# .deb con la clave nueva: RESPALDARLA.
# ---------------------------------------------------------------------------
set -euo pipefail
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$RAIZ/VERSION")"
DEB="$RAIZ/dist/picphotoviewer_${VERSION}_all.deb"
CLAVE="633EF5A6FC400D9514F8C6E1D1B8273177CD5791"
export GNUPGHOME="${GNUPGHOME:-$HOME/.local/share/picphotoviewer-apt-firma}"
ARQS="all amd64 arm64 armhf i386"
CONSERVAR=3

LOCAL=""
[ "${1:-}" = "--local" ] && LOCAL="${2:?falta el directorio}"

[ -f "$DEB" ] || { echo "No existe $DEB: correr antes tools/construir_deb.sh"; exit 1; }
gpg --batch --list-secret-keys "$CLAVE" >/dev/null 2>&1 || { echo "No está la clave de firma $CLAVE en $GNUPGHOME"; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
if [ -n "$LOCAL" ]; then
  SITIO="$LOCAL"; mkdir -p "$SITIO"
else
  SITIO="$TMP/sitio"
  ORIGEN="$(git -C "$RAIZ" remote get-url origin)"
  if git -C "$RAIZ" ls-remote --exit-code --heads origin gh-pages >/dev/null 2>&1; then
    git clone -q --depth 1 --branch gh-pages "$ORIGEN" "$SITIO"
  else
    git init -q -b gh-pages "$SITIO"
    git -C "$SITIO" remote add origin "$ORIGEN"
  fi
fi

POOL="$SITIO/pool/main/p/picphotoviewer"
mkdir -p "$POOL"
cp -f "$DEB" "$POOL/"
# conservar solo las últimas $CONSERVAR versiones
ls "$POOL"/picphotoviewer_*_all.deb | sort -V | head -n -"$CONSERVAR" | xargs -r rm -f

cd "$SITIO"
rm -rf dists
for a in $ARQS; do
  d="dists/stable/main/binary-$a"
  mkdir -p "$d"
  apt-ftparchive packages pool > "$d/Packages"
  gzip -9nk "$d/Packages"
done
apt-ftparchive \
  -o APT::FTPArchive::Release::Origin=PicPhotoViewer \
  -o APT::FTPArchive::Release::Label=PicPhotoViewer \
  -o APT::FTPArchive::Release::Suite=stable \
  -o APT::FTPArchive::Release::Codename=stable \
  -o "APT::FTPArchive::Release::Architectures=$ARQS" \
  -o APT::FTPArchive::Release::Components=main \
  -o "APT::FTPArchive::Release::Description=PicPhotoViewer, photo viewer for Debian" \
  release dists/stable > "$TMP/Release"
mv "$TMP/Release" dists/stable/Release
gpg --batch --yes --local-user "$CLAVE" --clearsign -o dists/stable/InRelease dists/stable/Release
gpg --batch --yes --local-user "$CLAVE" -abs -o dists/stable/Release.gpg dists/stable/Release

cp -f "$RAIZ/packaging/apt/picphotoviewer-archive-keyring.gpg" "$RAIZ/packaging/apt/picphotoviewer.sources" .
cp -f "$RAIZ/packaging/apt/index.html" index.html
touch .nojekyll   # que GitHub Pages sirva los archivos tal cual

if [ -n "$LOCAL" ]; then
  echo "Sitio armado en $SITIO (no se subió nada)."
  exit 0
fi

git add -A
git -c user.name="$(git -C "$RAIZ" config user.name)" -c user.email="$(git -C "$RAIZ" config user.email)" \
  commit -q -m "Repositorio APT: picphotoviewer $VERSION"
git push -q origin gh-pages
# GitHub Pages desde gh-pages (solo la primera vez)
if ! gh api "repos/nktrabajo/Pic-Photo-Viewer/pages" >/dev/null 2>&1; then
  gh api -X POST "repos/nktrabajo/Pic-Photo-Viewer/pages" -f 'source[branch]=gh-pages' -f 'source[path]=/' >/dev/null
  echo "GitHub Pages activado sobre gh-pages."
fi
echo "Repositorio APT actualizado con $VERSION: https://nktrabajo.github.io/Pic-Photo-Viewer/"
