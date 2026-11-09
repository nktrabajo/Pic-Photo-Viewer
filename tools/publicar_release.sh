#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# publicar_release.sh — publica la versión de VERSION como Release de GitHub.
#
#   ./tools/publicar_release.sh            (LO CORRE EL USUARIO, nunca Claude)
#
# Es el «deploy» de este proyecto: los equipos con PicPhotoViewer instalado
# consultan  https://api.github.com/repos/nktrabajo/Pic-Photo-Viewer/releases/latest
# una vez al día y, si el tag es mayor que su versión, preguntan si actualizar.
#
# Además actualiza el repositorio APT firmado de GitHub Pages
# (tools/publicar_apt.sh): los equipos reciben la versión con `apt upgrade`.
#
# Contrato que el visor espera (src/actualizar/github.py):
#   tag  vX.Y.Z   (no draft, no prerelease)
#   adjuntos  picphotoviewer_X.Y.Z_all.deb  +  picphotoviewer_X.Y.Z_all.deb.sha256
# Sin el .sha256 el visor IGNORA la release.
#
# Requiere `gh` autenticado (sudo apt install gh && gh auth login). Sin gh: crear
# la release a mano en GitHub con el mismo tag y los dos adjuntos de dist/.
# ---------------------------------------------------------------------------
set -euo pipefail
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"
VERSION="$(tr -d '[:space:]' < VERSION)"
TAG="v$VERSION"
DEB="dist/picphotoviewer_${VERSION}_all.deb"

command -v gh >/dev/null || { echo "Falta gh: sudo apt install gh && gh auth login"; exit 1; }
git diff --quiet && git diff --cached --quiet || { echo "Hay cambios sin commitear: commitear antes de publicar."; exit 1; }
git rev-parse "$TAG" >/dev/null 2>&1 && { echo "El tag $TAG ya existe: subir VERSION antes."; exit 1; }
grep -q "^picphotoviewer ($VERSION)" packaging/debian/changelog || { echo "packaging/debian/changelog no tiene la entrada $VERSION"; exit 1; }

echo "Pruebas…"
python3 -I tools/pruebas/prueba_todo.py >/dev/null
python3 -I tools/pruebas/prueba_visor.py >/dev/null
echo "Paquete…"
./tools/construir_deb.sh >/dev/null
(cd dist && sha256sum -c "$(basename "$DEB").sha256")

# primero el repositorio APT: el .deb trae su .sources, así que tiene que existir
# antes de que alguien instale esta versión
echo "Repositorio APT…"
./tools/publicar_apt.sh

NOTAS="$(awk -v v="$VERSION" '$0 ~ "^picphotoviewer \\("v"\\)" {f=1; next} /^ -- / {if (f) exit} f' packaging/debian/changelog | sed 's/^  //')"
git tag -a "$TAG" -m "PicPhotoViewer $VERSION"
git push origin HEAD "$TAG"
gh release create "$TAG" "$DEB" "$DEB.sha256" --repo nktrabajo/Pic-Photo-Viewer \
  --title "PicPhotoViewer $VERSION" --notes "$NOTAS"
echo "Publicada $TAG. Los equipos instalados la ofrecerán en su próxima consulta diaria."
