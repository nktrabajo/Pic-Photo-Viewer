"""Aviso de versión nueva desde las Releases de GitHub (decidido 2026-11-08).

El proyecto es público y se distribuye SOLO por GitHub: no hay satélite ni
APIHub. Esto NO actualiza solo: consulta, y si hay versión nueva PREGUNTA.

Contrato con la release (lo arma tools/construir_deb.sh, ver CLAUDE.md):
  - tag `vX.Y.Z` (la «v» es opcional)
  - adjunto `picphotoviewer_X.Y.Z_all.deb`
  - adjunto `picphotoviewer_X.Y.Z_all.deb.sha256` (salida de sha256sum)
Una release sin .sha256 se ignora: no se instala nada sin verificar.
"""
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.request

from core import config
from core.logger import get_logger

log = get_logger()

REPO = "nktrabajo/Pic-Photo-Viewer"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
INSTALADOR = "/usr/libexec/picphotoviewer/picphotoviewer-instalar"
CADA = 24 * 3600
AGENTE = "PicPhotoViewer-actualizador"


def version_tupla(v):
    v = v.strip().lstrip("vV")
    partes = re.findall(r"\d+", v.split("-")[0].split("+")[0])
    return tuple(int(p) for p in partes[:3]) + (0,) * (3 - len(partes[:3]))


def toca_buscar(ahora=None):
    if config.get("buscar_actualizaciones").lower() not in ("si", "sí", "1", "true", "yes"):
        return False
    try:
        ultima = float(config.get("ultima_busqueda") or 0)
    except ValueError:
        ultima = 0
    return (ahora or time.time()) - ultima >= CADA


def _get(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE,
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def interpretar_release(datos, instalada):
    """dict de la API → {'version','deb','sha256','notas','url'} si es más nueva, si no None."""
    if datos.get("draft") or datos.get("prerelease"):
        return None
    tag = datos.get("tag_name") or ""
    if version_tupla(tag) <= version_tupla(instalada):
        return None
    deb = sha = None
    for a in datos.get("assets", []):
        n = a.get("name", "")
        if n.endswith("_all.deb") and n.startswith("picphotoviewer_"):
            deb = a.get("browser_download_url")
        elif n.endswith(".deb.sha256"):
            sha = a.get("browser_download_url")
    if not deb or not sha:
        return None
    return {"version": tag.lstrip("vV"), "deb": deb, "sha256": sha,
            "notas": (datos.get("body") or "").strip(), "url": datos.get("html_url", "")}


def buscar():
    """Consulta GitHub. Devuelve la info de la versión nueva o None. Nunca lanza."""
    config.set("ultima_busqueda", int(time.time()))
    try:
        datos = json.loads(_get(API))
    except Exception as e:  # sin internet, GitHub caído, límite de la API…
        log.warning("No se pudo consultar GitHub por actualizaciones", {"error": str(e)})
        return None
    nueva = interpretar_release(datos, config.version())
    if nueva and nueva["version"] == config.get("version_ignorada"):
        return None
    return nueva


def descargar_y_verificar(info, progreso=None):
    """Baja el .deb a la caché y comprueba el SHA256. Devuelve la ruta."""
    os.makedirs(config.DIR_CACHE, exist_ok=True)
    esperado = _get(info["sha256"]).decode().split()[0].lower()
    if not re.fullmatch(r"[0-9a-f]{64}", esperado):
        raise RuntimeError("El .sha256 de la release no tiene un hash válido")
    destino = os.path.join(config.DIR_CACHE, f"picphotoviewer_{info['version']}_all.deb")
    h = hashlib.sha256()
    req = urllib.request.Request(info["deb"], headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(req, timeout=30) as r, open(destino + ".part", "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        leido = 0
        while True:
            bloque = r.read(65536)
            if not bloque:
                break
            f.write(bloque)
            h.update(bloque)
            leido += len(bloque)
            if progreso and total:
                progreso(leido * 100 // total)
    if h.hexdigest() != esperado:
        os.remove(destino + ".part")
        raise RuntimeError("El SHA256 del .deb no coincide con el publicado: no se instala")
    os.replace(destino + ".part", destino)
    return destino


def instalar(ruta_deb):
    r = subprocess.run(["pkexec", INSTALADOR, ruta_deb], capture_output=True, text=True)
    if r.returncode in (126, 127):
        raise RuntimeError("cancelado")
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "la instalación falló")
    log.info("Actualización instalada", {"deb": ruta_deb})
    try:
        os.remove(ruta_deb)
    except OSError:
        pass
