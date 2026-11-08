# PicPhotoViewer

Visor de fotos para Linux al estilo del clásico visor de fotos de Picasa: la foto se abre
**sobre el escritorio**, con una capa oscura translúcida detrás, la tira de fotos de la
carpeta abajo y la barra de botones al pie. Clic fuera de la foto (o Esc) y desaparece.

> Proyecto independiente, sin relación con Google ni con Picasa. Los íconos y gráficos
> son propios.

## Qué hace

- Zoom con la rueda (donde está el puntero), `+` `−` `1:1`, doble clic, arrastrar.
- Anterior / siguiente, tira de miniaturas, presentación con fundido (F5).
- Rotar **el archivo** sin pérdida (JPEG con `exiftran`, que además corrige el EXIF).
- Estrellas guardadas en `.picasa.ini`, compatibles con las que ya marcó Picasa.
- Copiar, imprimir, mover a la papelera, propiedades con datos EXIF.
- **Fondo de escritorio por pantalla**: con varios monitores muestra un diagrama con su
  posición y orientación reales; se elige una, varias o todas, y opcionalmente una sola
  imagen extendida sobre las elegidas. Las demás pantallas conservan su fondo.
- **Fondo de la pantalla de inicio de sesión (GDM)**, con contraseña de administrador.
- Menú contextual en Nautilus: abrir, poner como fondo de escritorio, poner como fondo de
  inicio de sesión.
- Avisa cuando hay una versión nueva en GitHub y la instala si se acepta.

## Instalar

```bash
curl -fsSL https://raw.githubusercontent.com/nktrabajo/Pic-Photo-Viewer/main/instalar.sh | bash
```

Baja el `.deb` de la última [release](https://github.com/nktrabajo/Pic-Photo-Viewer/releases),
verifica su SHA256, lo instala con `apt` y reinicia Nautilus para que cargue el menú
contextual. A mano es lo mismo: bajar el `.deb` y `sudo apt install /ruta/al/picphotoviewer_*_all.deb`.

Para que las fotos se abran con PicPhotoViewer al hacer doble clic: menú ▼ del visor →
«Usar como visor de imágenes predeterminado».

Probado en Debian 13 con GNOME 48 (X11). Requiere Python 3.11+ y PySide6 de los
repositorios de Debian (`apt` los instala solos).

## Desinstalar

```bash
curl -fsSL https://raw.githubusercontent.com/nktrabajo/Pic-Photo-Viewer/main/desinstalar.sh | bash
```

Quita el paquete y, si habías cambiado el fondo de inicio de sesión, **devuelve el tema
original de GNOME**. Si tu fondo de escritorio actual lo armó PicPhotoViewer, lo guarda
en `~/.local/share/backgrounds/` para que el escritorio no quede vacío. Pregunta si
borrar también tus preferencias; las estrellas (`.picasa.ini`) no se tocan. Con
`sudo apt purge picphotoviewer` también se restaura el tema de GDM.

## Sobre la pantalla de bloqueo

GNOME 48 ya no tiene un fondo de bloqueo propio: al bloquear muestra el fondo del
escritorio difuminado. Lo que PicPhotoViewer cambia es el fondo de **GDM**, la pantalla
de inicio de sesión (al encender, al cerrar sesión, al cambiar de usuario). Para hacerlo
parchea el tema de gnome-shell guardando antes una copia del original. Cuando gnome-shell
se actualiza, el fondo se vuelve a aplicar solo, y al desinstalar el paquete se restaura
el tema original.

## Atajos

| Tecla | Acción |
|---|---|
| ← → / Re Pág Av Pág | anterior / siguiente |
| Inicio / Fin | primera / última |
| + − / rueda | acercar / alejar |
| 1 / 0 | tamaño real / ajustar |
| F5 | presentación |
| Ctrl+R / Ctrl+Mayús+R | rotar derecha / izquierda |
| Ctrl+8 o S | estrella |
| Ctrl+C / Ctrl+P / Ctrl+E | copiar / imprimir / abrir con editor |
| Supr | papelera |
| F1 | ayuda |
| Esc | cerrar |

## Desarrollo

```bash
python3 -I src/main.py foto.jpg          # correr desde el código
python3 -I tools/pruebas/prueba_todo.py  # pruebas (sin tocar tu escritorio)
python3 -I tools/pruebas/prueba_visor.py
./tools/construir_deb.sh                 # dist/picphotoviewer_<versión>_all.deb + .sha256
```

Configuración por usuario en `~/.config/picphotoviewer/config.ini` (`editor`,
`segundos_presentacion`, `opacidad_fondo`, `buscar_actualizaciones`).

## Licencia

MIT — ver [LICENSE](LICENSE).
