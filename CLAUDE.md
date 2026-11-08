# PicPhotoViewer — Contexto del proyecto

Bitácora técnica del proyecto. Se actualiza en **cada sesión de trabajo**: decisiones con
fecha, bugs con causa raíz y la ruta de trabajo con su estado real.

Estándar transversal de ITCorp: `ESTANDAR-ITCorp.md` (copiado en la raíz de este proyecto) —
deploy, logs, migraciones, estructura y plantillas de código. Este archivo no lo repite: solo
anota lo propio de PicPhotoViewer.

> **Proyecto PÚBLICO que no usa el deploy del estándar (2026-11-08, pedido del usuario).**
> Se distribuye SOLO por GitHub (`git@github.com:nktrabajo/Pic-Photo-Viewer.git`) como `.deb`
> en Releases. No hay `update.sh`/`setup.sh`/`rollback.sh`/satélite/APIHub/`version.itc`,
> ni base de datos (`sql/` y `satellite/` del generador se quitaron a propósito). Lo
> equivalente: `VERSION` + `tools/construir_deb.sh` + `tools/publicar_release.sh` (§3.6).

---

## 🔧 EN QUÉ SEGUIR (lista viva, en orden de prioridad)

1. [ ] **Probarlo de verdad en el escritorio** (lo hace el usuario): instalar el `.deb`,
       abrir fotos, poner fondo en 1, 2 y 4 pantallas, fondo de GDM y cerrar sesión. Nada de
       eso se pudo ver en una pantalla real (ver «Lo que NO se pudo verificar»).
       `./tools/construir_deb.sh && cp dist/picphotoviewer_0.1.0_all.deb /tmp/ && sudo apt install /tmp/picphotoviewer_0.1.0_all.deb && nautilus -q`
       **Instalar SIEMPRE desde una copia local**: dentro del montaje SSHFS, root no puede
       leer (montado sin `allow_other`) y apt 3.0 responde un engañoso «Unsupported file
       … given on commandline» (visto 2026-11-08).
2. [x] ~~**Primer push + release `v0.1.0`**~~ — PUBLICADA 2026-11-08 (Claude, con
       autorización explícita del usuario): `main` + tag `v0.1.0` y la release
       https://github.com/nktrabajo/Pic-Photo-Viewer/releases/tag/v0.1.0 con el `.deb` y el
       `.sha256`. Verificado desde afuera: la API devuelve `v0.1.0`, el `.deb` baja y su
       SHA256 coincide, `instalar.sh` responde por raw.githubusercontent. `gh` quedó
       instalado y con sesión de `nktrabajo` en esta máquina.
3. [ ] Lo de «Qué le falta al proyecto», por prioridad del usuario.

**Parados a propósito, no arrancar sin retomarlos con el usuario**: —

**Decidido que NO se hace**:
- Fondo de **pantalla de bloqueo** propio (2026-11-08): GNOME 48 no lo tiene; la de bloqueo
  muestra el fondo del escritorio difuminado. El usuario eligió cambiar el de **GDM**. Se
  descartó la extensión de GNOME Shell (habría que mantenerla con cada versión de GNOME).
- Actualización **automática** sin preguntar (2026-11-08, pedido del usuario): solo avisa y
  pregunta.
- `.env` del estándar (2026-11-08): es una app de escritorio por usuario, sin secretos →
  `~/.config/picphotoviewer/config.ini` (XDG).

## Qué es esto

Un clon para Linux del **visor de fotos de Picasa**: al abrir una imagen, aparece a pantalla
completa sobre una capa oscura translúcida que deja ver el escritorio, con el nombre y las
dimensiones debajo, la tira de fotos de la carpeta y la barra de botones al pie (`+ − 1:1`,
editor, ◀ ▶ ▶, carpeta, rotar, estrella, menú ▼). Clic fuera de la foto la cierra.

Además pone una foto como **fondo de escritorio en una, varias o todas las pantallas** (con
un diagrama de los monitores reales) y como **fondo de la pantalla de inicio de sesión**,
desde el visor o con clic derecho en Nautilus.

## Objetivo

1. Misma interfaz y comportamiento que el visor de Picasa (captura de referencia del usuario,
   2026-11-08), funcionando en Linux.
2. Instalable con un `.deb` que se registra como visor de imágenes.
3. Menú contextual: fondo de escritorio (por pantalla) y fondo de inicio de sesión.
4. Aviso de versión nueva desde GitHub, con la opción de actualizar.

## Stack (decidido 2026-11-08)

- **Python 3 + PySide6 (QWidgets)** — PySide6 está en los repos de Debian 13
  (`python3-pyside6.*` 6.8.2), así que el `.deb` solo depende de paquetes de `apt`, sin pip.
  QWidgets y no QML (el estándar §10 habla de QML): todo el visor es UNA superficie pintada
  con QPainter con zonas de clic propias; así la translucidez y el estilo «Picasa» no
  dependen del tema del sistema.
- **PIL** (`python3-pil`): EXIF en Propiedades, rotar formatos no-JPEG, JPEG para GDM.
- **exiftran**: rotación de JPEG sin pérdida (ver 3.4).
- **glib** (`gresource`, `glib-compile-resources`) + **pkexec/polkit** para el fondo de GDM.
- **nautilus-python 4.0** para el menú contextual.
- Destino: Debian 13 / GNOME 48. Lo relevado en dev: GNOME Shell 48.7 en **X11**, 4
  monitores (2 verticales), Nautilus 48.3.

## Topología

- **dev**: este árbol (moonserver por SSHFS). Las pruebas corren en local, sin pantalla
  (`QT_QPA_PLATFORM=offscreen`).
- **distribución**: GitHub `nktrabajo/Pic-Photo-Viewer` → Releases con
  `picphotoviewer_X.Y.Z_all.deb` + `.sha256`.
- **equipo del usuario final**: el visor consulta
  `https://api.github.com/repos/nktrabajo/Pic-Photo-Viewer/releases/latest` como mucho una
  vez cada 24 h (3 s después de abrir una foto); si hay versión mayor, pregunta; si acepta,
  baja el `.deb`, verifica el SHA256 y lo instala con `pkexec` + `apt`.

Instalado queda así:

| Ruta | Qué |
|---|---|
| `/usr/bin/picphotoviewer` | lanzador (`python3 -I …/src/main.py`) |
| `/usr/share/picphotoviewer/{src,VERSION}` | el código |
| `/usr/libexec/picphotoviewer/picphotoviewer-gdm` | ayudante root del fondo de GDM |
| `/usr/libexec/picphotoviewer/picphotoviewer-instalar` | ayudante root de actualización |
| `/usr/share/polkit-1/actions/com.itcorp.picphotoviewer.policy` | las 2 acciones de pkexec |
| `/usr/share/nautilus-python/extensions/picphotoviewer-nautilus.py` | menú contextual |
| `/var/lib/picphotoviewer/` | fondo de GDM + copia del tema original |
| `~/.config/picphotoviewer/config.ini` | preferencias del usuario |
| `~/.local/share/picphotoviewer/{fondos/,fondos.json}` | fondos compuestos y su estado |

## Decisiones de diseño

### 3.1 Un fondo por pantalla en GNOME = una imagen «spanned» (2026-11-08, relevado)

GNOME tiene **una sola** imagen de fondo. Con `picture-options='spanned'` mutter la estira
al rectángulo que encierra todas las pantallas (`meta-background.c`, caso SPANNED). Entonces
`src/fondos/aplicar.py` compone una imagen del tamaño de ese rectángulo (en dev 6000×1920),
pinta la foto en las pantallas elegidas y conserva las demás, y la aplica en `picture-uri`
**y** `picture-uri-dark` (sin la segunda, en modo oscuro no cambia nada).

Cómo se conserva lo que había en las pantallas NO elegidas, en este orden:
1. Si el fondo actual es nuestro compuesto y el lienzo no cambió → se copian sus píxeles.
2. Si no, se repinta desde `fondos.json` (pasa al cambiar la disposición de monitores).
3. Si tampoco, se pinta el fondo actual de GNOME con su modo (incluido uno «spanned» ajeno y
   el primer `<file>` de un fondo XML).

Con **una sola pantalla** no se compone: se pone la foto directa con el modo de GNOME. Las
fotos se copian a `~/.local/share/picphotoviewer/fondos/` para que el fondo no dependa de
que el original siga existiendo; lo que ya no se usa se borra (solo de esa carpeta). Cada
compuesto lleva nombre nuevo (con el mismo nombre GNOME no recarga — ver bug 9.a).

### 3.2 Fondo de GDM parcheando el tema de gnome-shell (2026-11-08, pedido del usuario)

Debian 13 NO tiene `alternative` para el tema de GDM (relevado: `update-alternatives
--display gdm-theme.gresource` → no existe). GDM pinta su fondo con `#lockDialogGroup` de
`/usr/share/gnome-shell/gnome-shell-theme.gresource`. El ayudante
`packaging/helper/picphotoviewer-gdm` (root, vía pkexec):

- guarda el original en `/var/lib/picphotoviewer/gnome-shell-theme.gresource.original`
  ANTES del primer parche;
- extrae los 8 recursos, agrega un bloque marcado `/* PicPhotoViewer:inicio … fin */` al
  final de las 3 hojas CSS (dark, light, high-contrast), recompila al lado, **verifica**
  (misma lista de recursos + bloque presente) y recién ahí hace `rename()`;
- `reaplicar` es idempotente (parte siempre de la copia original).

**Regla que no se puede equivocar**: gnome-shell pisa ese archivo al actualizarse. El
paquete tiene un **trigger de dpkg** (`packaging/debian/triggers`) sobre esa ruta → el
`postinst triggered` corre `reaplicar`, que parchea **el tema nuevo** (nunca reinstala un
tema viejo sobre un gnome-shell nuevo). El `prerm remove` restaura el original.

### 3.3 Interfaz (2026-11-08)

`src/visor/ventana.py`: un QWidget sin marco, a pantalla completa en el monitor donde está
el puntero, `WA_TranslucentBackground`, opacidad del fondo configurable (`opacidad_fondo`,
0,72). Disposición copiada de la captura del usuario; los íconos se dibujan en
`src/visor/dibujo.py` — **ningún recurso gráfico de Google**. «Edit in Picasa» y «Upload»
se reemplazaron por **«Abrir con editor»** y **«Abrir carpeta»** (decidido con el usuario).
Las fotos chicas no se agrandan, y no se puede alejar más allá de «ajustada», como en Picasa.
La carga va en hilos (`cargador.py`, QImage nunca QPixmap fuera de la UI) y para zoom < 1
se pinta desde una copia reducida cacheada.

### 3.4 Rotar el archivo, no la vista (2026-11-08)

JPEG con `exiftran -i -p -9/-2`: sin pérdida **y** corrige la orientación EXIF (con
`jpegtran` solo, una foto con orientación ≠ 1 quedaría rotada dos veces). Otros formatos con
PIL conservando el formato (WEBP sin pérdida si el original lo era). No se usó la rotación
«virtual» de Picasa en `.picasa.ini`: los demás programas de Linux no la verían.

### 3.5 Estrellas en `.picasa.ini` (2026-11-08)

`[foto.jpg]` + `star=yes`, como Picasa. Se toca solo esa clave y se conserva el resto del
archivo (caras, rotaciones, álbumes); claves con mayúsculas intactas (`optionxform=str`);
lee UTF-8 o latin-1 (Picasa en Windows escribía ANSI).

### 3.6 Versiones y actualización por GitHub (2026-11-08, pedido del usuario)

- `VERSION` (semver) es la fuente de verdad; `packaging/debian/changelog` debe tener la
  entrada de esa versión (lo exige `publicar_release.sh`).
- `tools/construir_deb.sh` arma el paquete **copiando solo lo que nombra** (no excluyendo):
  la doc interna y las pruebas no pueden colarse.
- Release = tag `vX.Y.Z` + `picphotoviewer_X.Y.Z_all.deb` + `.deb.sha256`. **Sin `.sha256`
  el visor ignora la release**; si el hash no coincide, no instala.
- `picphotoviewer-instalar` (root) solo instala paquetes llamados `picphotoviewer`, copiados
  antes a un directorio de root, con `apt-get install` (resuelve dependencias nuevas).
- Menú ▼ → «Buscar actualizaciones» fuerza la consulta; «No avisar de esta versión» la
  silencia hasta la siguiente.

### 3.7 Logs (2026-11-08)

`~/Logs/PicPhotoViewer-<fecha>.txt` como el estándar, pero solo se registran **acciones**
(fondo, rotación, papelera, actualización) y errores: abrir y cerrar una foto no deja
archivo. Como un visor se abre muchas veces al día, se conservan los últimos 50.

## Estructura actual (2026-11-08)

```
VERSION                         versión del paquete (semver)
README.md                       el del repo público
LICENSE                         MIT
instalar.sh                     instalador de una línea desde la última release
desinstalar.sh                  apt purge + rescata el fondo actual + pregunta por los datos
src/main.py                     entrada: visor, --fondo, --fondo-gdm, --restaurar-gdm, --version
src/core/                       logger (estándar) y config (XDG, no .env)
src/visor/ventana.py            la ventana estilo Picasa (≈900 líneas)
src/visor/dibujo.py             botones e íconos pintados
src/visor/cargador.py           imágenes y miniaturas en hilos, caché LRU
src/visor/imagenes.py           formatos, orden natural, carga con EXIF
src/visor/acciones.py           rotar, papelera, editor, carpeta, visor predeterminado
src/visor/estrellas.py          .picasa.ini
src/visor/dialogos.py           propiedades (EXIF), atajos, acerca de
src/fondos/componer.py          pantallas y composición del lienzo (puro, probado píxel a píxel)
src/fondos/aplicar.py           orquesta el fondo por pantalla + fondos.json
src/fondos/gnome.py             gsettings
src/fondos/dialogo.py           diagrama de pantallas
src/fondos/gdm.py               lado usuario del fondo de GDM
src/actualizar/github.py        consulta, descarga y verificación de releases
src/actualizar/ui.py            el aviso «¿actualizar?»
packaging/helper/               los 2 ayudantes root (gdm, instalar)
packaging/debian/               control.in, postinst, prerm, postrm, triggers, changelog, copyright
packaging/polkit/               acciones de pkexec
packaging/nautilus/             extensión del menú contextual
packaging/picphotoviewer.desktop
assets/picphotoviewer.svg       ícono propio
tools/construir_deb.sh          arma dist/*.deb + .sha256
tools/publicar_release.sh       tag + push + gh release (LO CORRE EL USUARIO)
tools/check_system.sh           diagnóstico solo lectura
tools/pruebas/                  prueba_todo.py (53) y prueba_visor.py (20)
```

## Cómo se verificó (2026-11-08)

- **`tools/pruebas/prueba_todo.py` — 53 comprobaciones, 0 fallas** (2,4 s): orden y
  formatos; `.picasa.ini` (conserva claves de Picasa, borra secciones vacías, sin permiso
  falla); composición píxel por píxel con **la disposición real de los 4 monitores de dev**
  (rellenar, ajustar, centrar, extendida sobre 2 pantallas); `aplicar()` con gsettings falso
  (1ª vez conserva el fondo de fábrica, 2ª conserva la 1ª, cambio de disposición, una sola
  pantalla); rotación PNG; GitHub contra un `http.server` local (versión nueva, prerelease,
  sin `.sha256`, **SHA256 distinto rechazado**, una consulta por día); ayudante de GDM sobre
  una **copia** del tema real: los 8 recursos, CSS con el bloque y el resto byte a byte
  igual, reaplicar no duplica, trigger tras «actualizar gnome-shell», rechaza no-JPEG,
  restaurar deja el archivo **idéntico al de fábrica** (`cmp`).
- **`tools/pruebas/prueba_visor.py` — 20 comprobaciones, 0 fallas, 3 corridas seguidas**:
  clics en botones, teclado, arrastre, zoom (no aleja más allá de ajustada), estrella,
  clic en miniatura, presentación y Esc, Supr a la papelera, ayuda, clic fuera cierra.
- **Vistas fallar a propósito** (en una copia del código): rellenar↔ajustar (2 fallas), no
  borrar sección vacía (1), no verificar SHA (1), GDM sin bloque CSS (5), no copiar
  «previo» (2 — antes no se detectaba y se agregó el caso que esconde la foto original),
  clic fuera no cierra + zoom sin límite (2).
- **Capturas offscreen** del visor (normal, 200 %, ayuda) sobre un escritorio falso, y del
  diagrama de pantallas con los 4 monitores de dev (normal y extendida): se ven como la
  captura de referencia.
- **`.deb`**: `lintian` limpio salvo `no-manual-page`; `desktop-file-validate` OK; la
  extensión de Nautilus cargada con el `gi` real (`Nautilus 4.0`) devuelve los 3 ítems con
  1 imagen y ninguno con 2; el paquete extraído arranca (`--version` → 0.1.0).

**Lo que NO se pudo verificar**, y queda para el usuario:

- **Nada se vio en una pantalla real**: translucidez sobre el escritorio con mutter,
  pantalla completa en el monitor del puntero, animaciones, menú ▼, impresión.
- **El fondo «spanned» en GNOME de verdad** (no se cambió el fondo del usuario). La
  alineación depende de que el lienzo de Qt (`virtualGeometry`) coincida con el de mutter;
  en X11 sí debería. **Wayland con escalas distintas por monitor: sin probar.**
- **GDM real**: no se corrió nada como root ni se cerró sesión. Falta ver que el fondo
  aparece y que el trigger corre en una actualización real de gnome-shell.
- **Instalar el `.deb`** con `apt` (dependencias reales, postinst, polkit) y la
  actualización completa desde una release (no hay release todavía).
- **Rotación de JPEG**: `exiftran` no está instalado en dev; la prueba se salta (lo instala
  la dependencia del `.deb`).
- Copiar con `xclip` (no está instalado en dev; va como Recommends).

### Cómo correr las pruebas

```bash
cd ~/Documents/moonserverSSHFS/Proyectos/PicPhotoViewer
python3 -I tools/pruebas/prueba_todo.py && python3 -I tools/pruebas/prueba_visor.py
./tools/construir_deb.sh && lintian --tag-display-limit 0 dist/*.deb
```

## Cómo se libera

1. Subir `VERSION` y agregar la entrada en `packaging/debian/changelog`.
2. Commit.
3. `./tools/publicar_release.sh` (**el usuario**): corre las pruebas, arma el `.deb`, crea el
   tag, hace push y la release con los 2 adjuntos.

Qué NO viaja en el `.deb`: `CLAUDE.md`, `ESTANDAR-ITCorp.md`, `doc/`, `tools/`, `README.md`
(el paquete copia solo lo que nombra `construir_deb.sh`). En el **repo público** está todo
menos `ESTANDAR-ITCorp.md` (D1).

**Instalar desde GitHub** (lo que se le da a cualquiera): `instalar.sh` en la raíz baja la
última release, verifica el SHA256 e instala desde un temporal local:

```bash
curl -fsSL https://raw.githubusercontent.com/nktrabajo/Pic-Photo-Viewer/main/instalar.sh | bash
curl -fsSL https://raw.githubusercontent.com/nktrabajo/Pic-Photo-Viewer/main/desinstalar.sh | bash
```

`desinstalar.sh` (pedido del usuario, 2026-11-08): `apt purge` (el prerm devuelve el tema
de GDM original, el postrm borra `/var/lib/picphotoviewer`); **si el fondo de escritorio
actual es un compuesto nuestro, lo copia a `~/.local/share/backgrounds/` y apunta GNOME
ahí** — si no, al borrar los datos el escritorio quedaría gris; pregunta por `/dev/tty` si
borrar preferencias/fondos/caché (`--todo` sin preguntar); no toca los `.picasa.ini`.
Probado en seco con HOME, gsettings y dpkg falsos.

## Ruta de trabajo

1. [x] 2026-11-08 — Proyecto creado con `nuevo-proyecto.sh`; quitados `sql/` y `satellite/`.
2. [x] 2026-11-08 — Visor completo, fondos por pantalla, GDM, Nautilus, actualizador,
       `.deb`, pruebas.
3. [ ] Prueba real en el escritorio del usuario (EN QUÉ SEGUIR 1).
4. [ ] Resolver D1 y D2; primer push y release v0.1.0.

## Bugs encontrados y corregidos

### 9.a Dos fondos aplicados en el mismo segundo pisaban el mismo archivo (2026-11-08)

- **Síntoma**: la prueba «compuesto viejo borrado» falló.
- **Causa raíz**: el nombre era `compuesto-<fecha hasta segundos>-<pid>.jpg`; dos
  aplicaciones en el mismo segundo y proceso generaban el mismo nombre. GNOME no recarga
  una imagen cuyo URI no cambió, así que en uso real el segundo fondo no se vería.
- **Arreglo**: `src/fondos/aplicar.py` — se agregan los nanosegundos al nombre.
- **Verificado**: la prueba pasa; falló antes del arreglo.

### 9.b Al cerrar con miniaturas en cola, errores «Internal C++ object already deleted» (2026-11-08)

- **Causa raíz**: las tareas del QThreadPool seguían corriendo después de que Qt destruyó el
  `_Puente` por el que devuelven el resultado.
- **Arreglo**: `src/visor/cargador.py` `_Tarea.run` ignora ese `RuntimeError`.

### 9.c Diagnóstico equivocado sobre la papelera (2026-11-08, corregido en la misma sesión)

`prueba_visor.py` falló en «papelera» con `gio: … No such file or directory`. **Se creyó**
que `QFile.moveToTrash` devolvía `False` habiendo movido el archivo, y se cambió
`acciones.py` en consecuencia. **Era falso**: la prueba usaba un `HOME` que no existía, así
que ni Qt ni gio podían crear la papelera; el «No such file» era la carpeta de la papelera,
no la foto. Se revirtió el cambio en `acciones.py` y se creó el `HOME` en la prueba.

## Caminos descartados por experimento (no por opinión)

- `update-alternatives` para el tema de GDM → en Debian 13 no existe esa alternativa → por
  eso se parchea el gresource (3.2).

## Qué le falta al proyecto (relevado el 2026-11-08)

- GIF animados: se muestran como imagen fija (QMovie no está integrado).
- Si cambian los monitores (enchufar/desenchufar), el fondo compuesto no se rearma solo;
  se rearma al aplicar el siguiente.
- Fondo XML de GNOME (los que cambian con la hora): al componer se toma su primera imagen.
- Página de manual (`lintian: no-manual-page`).
- Interfaz solo en español.
- Wayland sin probar (la translucidez y `screenAt` pueden comportarse distinto).

## Seguridad

Sin servidor ni nada expuesto; lo sensible son los **dos ayudantes que corren como root**:
- `picphotoviewer-gdm`: solo acepta un JPEG regular (no enlace) ≤ 40 MB; escribe solo en
  `/var/lib/picphotoviewer/` y el gresource; `#!/usr/bin/python3 -I`; `PPV_RAIZ` solo sirve
  para las pruebas (pkexec limpia el entorno).
- `picphotoviewer-instalar`: solo instala un `.deb` cuyo `Package` es `picphotoviewer`,
  copiado antes a un directorio de root. polkit pide contraseña de administrador en las dos
  (`auth_admin_keep` / `auth_admin`).
- El actualizador no instala nada sin verificar el SHA256 publicado. Riesgo aceptado: el
  `.sha256` vive en la misma release que el `.deb` (protege contra descargas corruptas, no
  contra una cuenta de GitHub comprometida). Firmar con GPG queda como mejora.

No hay `SEGURIDAD.md` todavía: no hay superficie web.

## Reglas de trabajo (contrato con Claude)

Las del estándar (§2), adaptadas a que este proyecto no tiene servidor ni base de datos:

- Claude deja los cambios **listos en dev** (código + pruebas + `.deb` armado + doc) y avisa
  **qué falta publicar y con qué comando**.
- Claude **no** corre `publicar_release.sh`, no hace `git push`, no crea tags ni releases, y
  no hace commit sin pedido explícito.
- Claude **no** corre los ayudantes como root ni instala el `.deb` en la máquina del
  usuario: el GDM se prueba sobre una COPIA del tema (`PPV_RAIZ`).
- Claude **no** cambia el fondo real del usuario en las pruebas (gsettings falso).
- Se dice explícitamente qué quedó **sin verificar**.

## Decisiones abiertas

- [x] 2026-11-08 — **D1 — Doc interna en el repo público** — resuelto (usuario):
      `ESTANDAR-ITCorp.md` **fuera del repo** (en `.gitignore`, vive solo en dev porque
      describe la infraestructura interna de ITCorp); `CLAUDE.md` sí se publica. Como el
      commit inicial del generador ya lo tenía y no se había publicado nada, se rehízo el
      commit raíz sin él (no quedó en la historia).
- [x] 2026-11-08 — **D2 — Licencia** — resuelto (usuario): **MIT** (`LICENSE`, y
      `License: Expat` en `packaging/debian/copyright`).
- [x] 2026-11-08 — **Fondo de bloqueo** — resuelto: fondo de GDM (3.2).
- [x] 2026-11-08 — **Botones en lugar de «Edit in Picasa» / «Upload»** — resuelto: «Abrir
      con editor» y «Abrir carpeta».
- [x] 2026-11-08 — **Deploy** — resuelto: solo GitHub Releases, sin autoactualización;
      aviso + pregunta (3.6).
