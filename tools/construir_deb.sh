#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# construir_deb.sh — arma dist/picphotoviewer_<VERSION>_all.deb y su .sha256.
#
#   ./tools/construir_deb.sh
#
# Reemplaza al update.sh del estándar: este proyecto es público y se reparte
# SOLO por GitHub Releases (decidido 2026-11-08). No sube nada: publicar la
# release lo hace el usuario (ver tools/publicar_release.sh y CLAUDE.md).
#
# Qué NO entra al paquete: la documentación interna (CLAUDE.md, ESTANDAR,
# doc/), las pruebas (tools/) y __pycache__. El paquete se arma copiando SOLO
# lo que se nombra acá abajo, no excluyendo — así nada nuevo se cuela solo.
# ---------------------------------------------------------------------------
set -euo pipefail
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$RAIZ/VERSION")"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "VERSION inválida: $VERSION"; exit 1; }

DIST="$RAIZ/dist"
ARMADO="$(mktemp -d)"
trap 'rm -rf "$ARMADO"' EXIT
P="$ARMADO/pkg"

install -d "$P/DEBIAN" "$P/usr/bin" "$P/usr/share/picphotoviewer" "$P/usr/libexec/picphotoviewer" \
  "$P/usr/share/applications" "$P/usr/share/icons/hicolor/scalable/apps" \
  "$P/usr/share/polkit-1/actions" "$P/usr/share/nautilus-python/extensions" \
  "$P/usr/share/doc/picphotoviewer"

# código (sin cachés)
rsync -a --exclude='__pycache__' --exclude='*.pyc' --exclude='CLAUDE.md' "$RAIZ/src" "$P/usr/share/picphotoviewer/"
install -m 644 "$RAIZ/VERSION" "$P/usr/share/picphotoviewer/VERSION"

cat > "$P/usr/bin/picphotoviewer" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 -I /usr/share/picphotoviewer/src/main.py "$@"
EOF
chmod 755 "$P/usr/bin/picphotoviewer"

install -m 755 "$RAIZ/packaging/helper/picphotoviewer-gdm" "$RAIZ/packaging/helper/picphotoviewer-instalar" \
  "$P/usr/libexec/picphotoviewer/"
install -m 644 "$RAIZ/packaging/picphotoviewer.desktop" "$P/usr/share/applications/"
install -m 644 "$RAIZ/assets/picphotoviewer.svg" "$P/usr/share/icons/hicolor/scalable/apps/"
install -m 644 "$RAIZ/packaging/polkit/com.itcorp.picphotoviewer.policy" "$P/usr/share/polkit-1/actions/"
install -m 644 "$RAIZ/packaging/nautilus/picphotoviewer-nautilus.py" "$P/usr/share/nautilus-python/extensions/"
install -m 644 "$RAIZ/packaging/debian/copyright" "$P/usr/share/doc/picphotoviewer/"
gzip -9n -c "$RAIZ/packaging/debian/changelog" > "$P/usr/share/doc/picphotoviewer/changelog.gz"
chmod 644 "$P/usr/share/doc/picphotoviewer/changelog.gz"

find "$P/usr" -type d -exec chmod 755 {} +
find "$P/usr/share/picphotoviewer" -type f -exec chmod 644 {} +

TAM=$(du -sk "$P/usr" | cut -f1)
sed -e "s/@VERSION@/$VERSION/" -e "s/@SIZE@/$TAM/" "$RAIZ/packaging/debian/control.in" > "$P/DEBIAN/control"
install -m 644 "$RAIZ/packaging/debian/triggers" "$P/DEBIAN/"
install -m 755 "$RAIZ/packaging/debian/postinst" "$RAIZ/packaging/debian/prerm" "$RAIZ/packaging/debian/postrm" "$P/DEBIAN/"
(cd "$P" && find usr -type f -exec md5sum {} + | sort -k2 > DEBIAN/md5sums)

mkdir -p "$DIST"
DEB="$DIST/picphotoviewer_${VERSION}_all.deb"
dpkg-deb --root-owner-group -Zxz --build "$P" "$DEB" >/dev/null
(cd "$DIST" && sha256sum "$(basename "$DEB")" > "$(basename "$DEB").sha256")
echo "$DEB"
echo "$DEB.sha256"
