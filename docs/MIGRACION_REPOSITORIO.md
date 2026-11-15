# Git, actualizaciones y entregas

El proyecto se mantiene en Git con el código común en `src/`, las fuentes
Android en `android/src/` y los instaladores generados en `addons/` y `yunohost/`.
Para localizar un componente consulta [ESTRUCTURA.md](ESTRUCTURA.md).

## Abrir un clon de trabajo

Clona el repositorio autorizado con tu clave SSH. El siguiente ejemplo usa una
dirección ficticia que debes sustituir por la de tu servidor.

```bash
git clone ssh://git@forgejo.example.net:2222/usuario/headscale_gateway.git
cd headscale_gateway
git status
python3 tools/check_repository.py
python3 tools/prepare_git_install.py --check
sha256sum -c CONTENIDO.sha256
```

Los requisitos de compilación están en el [README](../README.md). Para instalar
los paquetes ya incluidos, sigue [INSTALACION_PRIVADA.md](INSTALACION_PRIVADA.md).

## Trabajar sobre una versión nueva

Con el árbol limpio, descarga los cambios antes de empezar.

```bash
git pull --ff-only
```

Edita las fuentes y prepara los contenidos generados cuando corresponda. Revisa
las diferencias y ejecuta las pruebas indicadas en [CONTRIBUTING.md](../CONTRIBUTING.md).
Los commits nuevos conservan la historia de las versiones publicadas.

```bash
git diff
git switch -c codex/mi-cambio
git add .
git ls-files -z -- . ':(exclude)CONTENIDO.sha256' | xargs -0 sha256sum > CONTENIDO.sha256
git add CONTENIDO.sha256
git diff --cached --stat
git commit -m "Describir el cambio realizado"
git push -u origin codex/mi-cambio
```

`CONTENIDO.sha256` contiene las sumas de los archivos versionados del árbol
entregado. Añade primero los archivos nuevos y después calcula las sumas.
Revisa el contenido preparado antes de confirmar el commit.

## Identificar una entrega

La versión del motor se define en `VERSION` y se cambia con
`python3 tools/set_version.py X.Y.Z`. Regenera después los paquetes instalables.
Una etiqueta Git identifica el commit de una entrega. El nombre debe ser nuevo
y responder a la política de versiones acordada.

```bash
# Tras fusionar el commit aprobado de 1.4.7 en main.
git tag -a v1.4.7 -m "Headscale Gateway 1.4.7"
git push origin refs/tags/v1.4.7
git ls-remote origin refs/heads/main 'refs/tags/v1.4.7^{}'
```

Las dos referencias de una entrega recién etiquetada deben resolver al commit
que acabas de publicar. La primera prueba documental utilizó `v0.1.0.1` mientras
el motor declaraba `1.4.4`. Consulta ambos valores antes de automatizar números
de versión en instaladores.

### Publicación y adjuntos

Forgejo conserva el origen privado y replica ramas y etiquetas en el principal
privado de GitHub. La calidad y los publicadores se ejecutan en GitHub Actions.
Las Actions de Forgejo están desactivadas para este proyecto. El runner local,
la carpeta histórica de preparación y `HGW_RELEASE_READ_TOKEN` no forman parte
del recorrido automático vigente. No prepares nuevos adjuntos en YunoHost
siguiendo instrucciones de entregas anteriores.

Después de fusionar una revisión en Forgejo, comprueba la misma referencia en
GitHub y la ejecución **Calidad multiplataforma**. Su finalización correcta en
`main` activa los publicadores de paquetes, integración, tiendas y manual.
Consulta [PUBLICACION.md](PUBLICACION.md) para los destinos y permisos.

El flujo **Preparar entrega completa** de GitHub construye los motores de las
seis plataformas, los escritorios Linux/Windows con sus fuentes de terceros y
los candidatos APK/AAB sin firma. Conserva los resultados como artefactos de
Actions durante siete días; no crea una release ni publica Android sin firma.
Se ejecuta sobre la revisión elegida con `workflow_dispatch`. Antes de distribuir,
verifica la calidad de ese SHA, firma Android con la identidad estable local y
comprueba la actualización desde la entrega anterior. Play Store queda preparado,
sin enviar la aplicación a la tienda.

Después, **Preparar borrador de release** recibe el número de esa ejecución.
Exige calidad correcta en el `main` vigente, una etiqueta ya replicada desde
Forgejo y los mismos fuentes de motor, Android y escritorio. Revalida las sumas,
incorpora la documentación actual y prepara un borrador en el principal privado
de GitHub. Los escritorios grandes se dividen sin retirar sus fuentes. Verifica
cada descarga; no modifica una release existente ni publica automáticamente el
borrador. Incorpora después Android firmado y su validación antes de publicarlo.
Así los adjuntos grandes no vuelven a ocupar espacio en el servidor YunoHost.

El espejo Git no copia metadatos de releases ni adjuntos. Una etiqueta recibida
por GitHub no garantiza que estén publicados los instaladores de escritorio o
Android. Comprueba por separado la lista de archivos, sus tamaños y SHA-256 y
las notas de la entrega antes de anunciarla. No sobrescribas etiquetas ni
archivos de una versión anterior.

Los escritorios deben acompañarse de los fuentes y avisos completos de Electron
y FFmpeg previstos en [LICENCIAS.md](LICENCIAS.md). Si se divide un archivo con
`tools/split_release.py`, se distribuyen todas las partes, las sumas y las
instrucciones de reconstrucción. Android conserva su identidad de aplicación y
la firma de release para permitir actualizar una instalación existente. Las
claves de firma permanecen fuera del repositorio.

## Exportar una carpeta o un ZIP limpio

```bash
python3 tools/prepare_git_install.py --check
python3 tools/repository_archive.py --output releases/headscale-gateway-fuentes.zip
```

El exportador utiliza una lista de fuentes permitidas y verifica los paquetes.
Cada ZIP incorpora su propia lista `CONTENIDO.sha256`. Con `--include-releases`
añade los archivos Android autorizados de `releases/android/`, si existen y su
suma coincide.

Descomprime las entregas en una carpeta nueva y comprueba sus sumas antes de
usarlas. Si trabajas sobre un clon existente, incorpora los cambios como una
modificación revisada que conserve su directorio `.git` y su historia.

## Datos de las instalaciones

Las fuentes del proyecto y los datos de ejecución tienen ubicaciones propias.
En Home Assistant los datos del motor están en `/data/gateway/`. En YunoHost se
utiliza la subcarpeta `gateway/` del directorio de datos asignado a la instancia.
Mantén las bases de datos, claves, perfiles y copias privadas fuera del clon.
Las actualizaciones se realizan con el procedimiento de cada plataforma.
