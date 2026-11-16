# Git, actualizaciones y entregas

Forgejo conserva el origen privado. GitHub recibe su espejo privado y el
compilador público genera las distribuciones. [PUBLICACION.md](PUBLICACION.md)
explica los destinos y sus permisos; esta página describe el trabajo con Git.

## Empezar una modificación

Clona por SSH el repositorio para el que tengas autorización. Este ejemplo usa
un servidor ficticio:

```sh
git clone ssh://git@forgejo.example.net:2222/usuario/headscale_gateway.git
cd headscale_gateway
git status --short
git fetch origin
git switch -c codex/mi-cambio origin/main
```

Lee [CONTRIBUTING.md](../CONTRIBUTING.md) y
[Empezar a desarrollar](EMPEZAR_DESARROLLO.md). Edita las fuentes y documenta el
cambio. No edites directamente `addons/` o `yunohost/`: son instaladores generados.
Revisa trabajo ajeno antes de cambiar de rama o preparar el índice.

## Guardar el resultado local

Ejecuta las pruebas correspondientes y revisa archivos nuevos y eliminados.
Después de preparar el índice, actualiza sus sumas:

```sh
git add --all
python3 -B tools/check_privacy.py
git ls-files -z -- . ':(exclude)CONTENIDO.sha256' | xargs -0 sha256sum > CONTENIDO.sha256
git add CONTENIDO.sha256
git diff --cached --check
sha256sum --check --quiet CONTENIDO.sha256
git commit -m "Describir el cambio y su finalidad"
```

Un commit local no instala, publica ni sube nada. Si se pidió preparar sin
subir, este es el punto de parada. Conserva en el informe los resultados reales
y lo pendiente, sin contraseñas ni rutas personales de instalaciones.

## Subir y fusionar cuando esté autorizado

Sube la rama por SSH y abre una solicitud de fusión en Forgejo. `main` está
protegido; no se desactiva la protección ni se utiliza `--force` para eludirla.
Después de fusionar, descarga y comprueba la referencia remota y su `VERSION`.
Comprueba el mismo commit en el espejo de GitHub. La réplica Git transmite ramas
y etiquetas; no transmite los metadatos ni adjuntos de releases.

## Identificar y publicar una entrega

`VERSION` identifica motor y paquetes. Se cambia con
`python3 tools/set_version.py X.Y.Z`; después se regeneran los instaladores.
Solo tras la aprobación de publicación, crea una etiqueta **nueva** `vX.Y.Z`
en el commit correcto de `main` y súbela por SSH. Comprueba el commit al que
apunta, también cuando sea una etiqueta anotada.

Publica una **release estable en Forgejo** con esa etiqueta. Una etiqueta sola,
un borrador o un push a `main` no activa una entrega. El controlador público
consulta esa release, fija el commit y ejecuta seguridad y pruebas antes de
compilar y publicar instaladores, paquetes, tiendas y manuales. No necesita
adjuntos preparados en el servidor YunoHost ni un runner de Forgejo.

Los workflows vigentes del compilador se mantienen en
`packaging/releases/.github/workflows/`. Los flujos de la raíz comprueban el
espejo y las propuestas de cambio; no constituyen otro publicador. Las recetas
privadas de entrega y los publicadores de Forgejo antiguos se retiraron del
árbol actual; sus versiones originales permanecen en las etiquetas históricas.

No muevas etiquetas publicadas ni reemplaces un adjunto por otro de distinto
contenido. Una corrección exige otra versión. Conserva junto a los escritorios
los fuentes y avisos de Electron/Chromium/FFmpeg, y la firma Android estable
fuera del repositorio. Consulta [licencias](LICENCIAS.md).

## Exportar fuentes sin el historial privado

```sh
python3 -B tools/prepare_git_install.py --check
python3 -B tools/check_privacy.py
python3 tools/repository_archive.py --output builds/export/headscale-gateway-fuentes.zip
```

El exportador selecciona carpetas y archivos concretos y excluye claves,
SQLite, copias, cachés y resultados locales. La exportación pública usa una
historia independiente; no se convierte en público el principal ni se copia su
`.git`. Audita también la carpeta exportada según [SEGURIDAD.md](SEGURIDAD.md).
