# Publicación en una dirección

Forgejo conserva el principal privado. Su espejo privado de GitHub recibe ramas
y etiquetas. Los publicadores de GitHub generan las distribuciones públicas;
ninguno escribe en Forgejo. Las etiquetas y los archivos publicados no se
reemplazan por otros de contenido diferente.

| Principal privado | Distribuciones públicas | Tiendas compartidas |
| --- | --- | --- |
| headscale_gateway | headscale_gateway_ynh, headscale_gateway_ha, headscale_gateway_releases y headscale_gateway_flatpak | Mis_app_ha y Mis_componente_ha |
| pivigia | pivigia_ha | Mis_app_ha y Mis_componente_ha |
| jacksignal | jacksignal_ha | Mis_app_ha y Mis_componente_ha |

## Headscale Gateway: compilación pública

Desde la entrega 1.4.9, el control de
[headscale_gateway_releases](https://github.com/Gente-del-Condado/headscale_gateway_releases/actions)
compila en runners públicos estándar. Así no depende de la cuota de ejecución
del espejo privado. Los publicadores antiguos del espejo se retiraron del árbol actual para evitar
entregas duplicadas; la comprobación de calidad de pull requests se conserva.
Forgejo autoriza la entrega mediante su release estable. Con la migración
`HGW_SOURCE_BACKEND=github-mirror`, el controlador comprueba que la etiqueta del
espejo privado de GitHub tiene el mismo SHA y descarga de allí únicamente el
árbol de fuentes. No copia el historial privado ni publica por un push a main.

Sus fuentes se mantienen primero en `packaging/releases/automation/` y
`packaging/releases/.github/workflows/` del principal de Forgejo. Exportar ese
control al repositorio público es una tarea de mantenimiento por SSH; no se
necesita repetirla para cada versión normal de la aplicación.

1. Prepara las fuentes y `VERSION` con `tools/set_version.py`, los cambios de uso
   y los instaladores generados del manifiesto. Revisa y sube por SSH a Forgejo.
2. Publica allí una **release estable** `vX.Y.Z`, con VERSION coincidente y el
   commit preparado. Una etiqueta sola, un borrador o una prerelease no publica.
3. El flujo **Compilar y publicar desde Forgejo** consulta las releases cada hora,
   en el minuto 17 UTC. También se activa al actualizar su controlador en main.
   No hace falta lanzar flujos a mano. GitHub puede retrasar sus programaciones.
4. Cada trabajo descarga del origen seleccionado el mismo commit y vuelve a comprobar etiqueta, versión
   y manifiesto. Seguridad Go/npm, pruebas Go/JS/Python, Windows, Debian,
   integración Home Assistant y contenedores preceden a la entrega. Un fallo
   bloquea la publicación de instaladores.
5. El runner construye Android con la identidad de firma existente y Lint, los
   seis motores, bandejas, Debian/Fedora, fuentes correspondientes y Flatpak.
   Instala y comprueba Flatpak y compila el manual estricto antes de publicar.
6. Se actualizan paquetes, tiendas y ambas ramas gh-pages. Las tiendas conservan
   las otras aplicaciones. Se publican las descargas en cuatro repositorios y
   se comprueban todas sin credenciales y por SHA-256. Un recibo con el commit
   Forgejo y el controlador identifica la entrega completada y evita repetirla.

La etiqueta 1.4.9 conserva su commit original aunque después cambien el control
o las guías del principal. No se mueve una etiqueta para corregir automatización.
Una publicación parcial requiere revisar los resultados originales y completar
su recuperación; no recompilar para sustituir archivos ya distribuidos.

### Secretos del control público

Los siguientes secretos se guardan en Actions de **headscale_gateway_releases**:

- `FORGEJO_RELEASE_READ_TOKEN`: solo `wolfbelmi88/headscale_gateway`, permiso
  `repository` en Leídas y el resto sin acceso. No permite escribir en Forgejo.
- `MIRROR_READ_TOKEN`: token GitHub fine-grained, solo el repositorio privado
  `headscale_gateway`, Contents y Metadata de lectura. Se usa únicamente para
  contrastar referencias y descargar el commit aprobado; no firma ni publica.
- `PUBLICATION_TOKEN`: token GitHub fine-grained con Contents de lectura y
  escritura solo en los seis destinos públicos de Headscale de la tabla.
  No necesita Administration, Workflows ni acceso al espejo privado.
- `ANDROID_SIGNING_BUNDLE`: la firma Android existente. Nunca crear otra clave
  para una actualización: impediría actualizar las instalaciones actuales.

GitHub no permite recuperar los valores guardados. Para cambiar de repositorio
compilador hay que volver a introducirlos en sus secretos cifrados. No se pegan
en incidencias, conversaciones ni archivos Git. La prueba de lectura comprueba
API, archivo de fuentes, SSO y firma sin compilar; la prueba de publicación usa
`git push --dry-run` sin modificar referencias.

Los tokens tienen caducidad: renuévalos antes de su fecha límite. GitHub desactiva
las programaciones de repositorios públicos después de 60 días sin actividad;
si sucede, el mantenedor debe reactivar el flujo. El principal sigue siendo
privado y todas las compilaciones grandes se ejecutan fuera del Linux del usuario.

## Descargas públicas y nuevos paquetes Linux

Las instantáneas saneadas completas se publican en `upstream-source` del paquete
YunoHost y en etiquetas `source-vX.Y.Z`, sin claves, bases de datos ni historial
privado. Su main contiene solo el paquete YunoHost. Los binarios del motor y sus
fuentes correspondientes se sirven desde `server-vX.Y.Z` en ese mismo destino.

Los instaladores de bandeja son archivos pequeños completos. Los fuentes exactos
de Electron/Chromium/FFmpeg, Node y NAN se distribuyen en una release propia
`desktop-sources-electron-VERSION-HUELLA`, reutilizada mientras no cambie el lock.
Se mantienen fuentes exactos, parches, avisos y sumas, con enlace desde cada
instalador y release Gateway. El publicador comprueba el conjunto antes de
publicar los instaladores; rechaza fuentes distintos y no reemplaza adjuntos.
La release de dependencias no ocupa «Latest». La 1.4.16 conserva todos sus
archivos y enlaces originales; la separación se aplica a las siguientes entregas. Solo el archivo grande de fuentes Chromium usa partes.
Conserva esos fuentes y avisos al redistribuir el escritorio.
No elimines una release de dependencias mientras existan instaladores que la
referencien. Cada release tiene su propio `SHA256SUMS`: no intercambies el de
Gateway con el de los fuentes de Electron.

Antes de preparar otro conjunto, el workflow consulta de forma anónima el
existente. Si coincide con el lock, omite por completo la preparación y subida.
Solo un 404 de la release permite preparar uno nuevo; una suma distinta, un
adjunto ausente o un error de acceso bloquean el proceso. El constructor y el
publicador también rechazan los archivos de terceros en la carpeta de adjuntos
de Gateway. El ensayo automatizado de una versión siguiente no crea etiquetas,
no cambia `VERSION` y no publica una nueva aplicación.


El mismo manual se genera desde las fuentes y se publica en gh-pages de YunoHost
y Home Assistant. Android utiliza la dirección estable
https://gente-del-condado.github.io/headscale_gateway_ynh/.
Renombrar un repositorio conserva releases y permisos, pero sus enlaces Pages
deben actualizarse expresamente.

Consulta [Debian y Fedora](LINUX_NATIVO.md), [Flatpak](FLATPAK.md) y
[descargas públicas](DESCARGAS_PUBLICAS.md). Flatpak distribuye el motor completo,
consola y panel web. No se solicita inclusión en Flathub ni en el catálogo
YunoHost. **Play Store continúa solo preparado**: el AAB no se envía a la tienda.

Los resultados históricos del laboratorio real YunoHost se conservan en sus
commits y notas; los informes privados se archivan fuera del árbol de desarrollo. Las pruebas
nginx/NSS en contenedor son complementarias; no equivalen a repetir package_check
o la actualización de una instalación real con datos y secretos. No ejecutes
máquinas virtuales ni compilaciones grandes en el Linux del usuario.

## Cierre de credenciales de la tienda

JackSignal y PiVigia ya se consumen desde sus públicos, con lectura anónima y
GITHUB_TOKEN del destino. Se retira `sync-forgejo.yml` de Mis_app_ha y de esta
plantilla; `FORGEJO_APPS_READ_TOKEN` y `DISTRIBUTION_TOKEN` de la tienda dejan de
ser necesarios. PGM usa también su consumidor público autónomo.

Gateway conserva `PUBLICATION_TOKEN`: sus seis destinos y la retención todavía
lo requieren. No revocar la firma Android, el índice F-Droid ni accesos de copias.
Las claves SSH de espejos privados y sus tokens exclusivos de lectura siguen
vigentes. La CI privada permanece desactivada.

## PiVigia y JackSignal (recorrido histórico sustituido)

Forgejo conserva los dos principales privados y GitHub sus espejos. La tienda
pública consulta el SHA de main y ejecuta calidad sin credenciales antes de
preparar aplicaciones e integraciones. Las distribuciones dedicadas y
Mis_componente_ha se publican con DISTRIBUTION_TOKEN, limitado a esos tres
destinos públicos. Los pull requests no publican y no hay escritura de regreso
a Forgejo. Los publicadores antiguos de los espejos se han retirado.

## Imágenes precompiladas de Home Assistant

Forgejo sigue siendo el origen y GitHub el espejo. El publicador entrega el
contenido aprobado a `build-source` de `Mis_app_ha`. Un único workflow de esa
tienda construye imágenes nativas `amd64` y `aarch64`, ejecuta las pruebas de
arranque con datos desechables y crea un índice multi arquitectura en GHCR.
Solo después de verificar su descarga anónima actualiza la aplicación en `main`
y añade `image:`. La versión anterior sigue instalable mientras se prepara la nueva.

Los Dockerfile y fuentes se conservan; Home Assistant descarga la imagen preparada.
No se cambian slugs, opciones, volúmenes, permisos, datos ni credenciales. Una imagen
ya distribuida no se sustituye con otro contenido: aumenta la versión al cambiar
el contexto de compilación. El cambio inicial publica las versiones actuales sin
forzar actualizaciones ni reinstalaciones de los equipos existentes.

El controlador común se mantiene en `packaging/homeassistant-store/` de
`headscale_gateway` en Forgejo y se exporta a `.github/ha-images/` y al workflow
de `Mis_app_ha`. No escribe en los principales ni devuelve cambios a Forgejo.

`Verificar aplicaciones desde Forgejo` consulta main cada hora con
FORGEJO_APPS_READ_TOKEN de solo lectura. El plan compara los recibos antes de
descargar los proyectos. Una validación correcta publica los contextos y llama
al workflow reutilizable de imágenes solo cuando hay árboles pendientes. Así
funciona también con commits escritos por GITHUB_TOKEN y se recuperan intentos
de imágenes fallidos sin repetir la calidad ya validada.

## Actions simplificadas

La tienda pública comprueba primero SHA y recibos de PiVigia/JackSignal. Una
consulta sin cambios no descarga fuentes ni ejecuta calidad/publicación. Las
integraciones se exportan con sumas y se publican en sus repositorios dedicados
y Mis_componente_ha; los demás proyectos se conservan. DISTRIBUTION_TOKEN concede
Contents de escritura únicamente a esos tres destinos públicos. Los secretos
anteriores de los principales privados no se reutilizan ni se extraen.

Los antiguos publicadores privados se retiran cuando este recorrido ha pasado
sus pruebas. La CI de los espejos queda para pull requests y ensayos manuales,
sin duplicar cada réplica de main. Headscale conserva las pruebas nativas de
Windows, Debian, Android, integración HA y contenedores; verify.sh se ejecuta una
vez por revisión y los paquetes dependen de su resultado.

El manual y la retención GitHub son workflows reutilizables invocados después
de una publicación real, sin engancharse al éxito de un plan sin cambios. Las
guías se actualizan también por cambios documentales, excluidos del disparador
del compilador. La retención conserva su tarea diaria y las protecciones de
fuentes Electron. Esta simplificación no activa la limpieza local de YunoHost
cancelada anteriormente. La lectura de Forgejo queda como diagnóstico manual y
se retira la comprobación inicial que solo imprimía el estado del runner.

## Tienda Android F-Droid propia

`packaging/fdroid-store/` mantiene el controlador de
[Mis_app_fdroid](https://github.com/Gente-del-Condado/Mis_app_fdroid). Se exporta
con `python3 tools/prepare_fdroid_store.py /ruta/nueva`, desde el commit revisado
y fusionado en Forgejo. La exportación enumera archivos públicos explícitamente
y registra su origen; no copia APK locales, historial ni claves.

GitHub Actions consulta las releases públicas en el minuto 43 UTC y actualiza
el índice firmado de GitHub Pages si hay versiones nuevas; lo renueva cada semana
aunque las APK no cambien. La APK directa conserva su firma original. El secreto
`FDROID_REPO_SIGNING_BUNDLE` solo firma el índice, con una identidad distinta.
No necesita acceso al principal ni devuelve cambios a Forgejo. El sitio contiene
solo el resultado público. El índice verifica exactamente las APK comprobadas,
con dos versiones estables por aplicación. Un fallo conserva el despliegue previo.

La tienda propia no implica aceptación en f-droid.org ni publicación en Play Store.
Sus instrucciones de instalación, huella y recuperación están en su README.

## Activar la lectura desde el espejo privado de Gateway

El controlador incluye un cambio gradual, sin Actions privadas. La variable
`HGW_SOURCE_BACKEND` de `headscale_gateway_releases` acepta `forgejo` (valor
inicial) o `github-mirror`. No cambia de origen automáticamente cuando falla
un token o falta una etiqueta: detiene la entrega. Forgejo y el espejo deben
apuntar al mismo commit tanto para releases como para ramas candidatas.

Primero guardar `MIRROR_READ_TOKEN` en el publicador público y ejecutar
**Verificar espejo privado sin publicar**. Ese diagnóstico fuerza la lectura
del espejo, contrasta la release estable, descarga sus fuentes y verifica el
manifiesto y todas las sumas sin construir ni volver a publicar instaladores.
Después de un resultado correcto, activar `HGW_SOURCE_BACKEND=github-mirror`.
La lectura inicial de una entrega ya completada debe omitir su reconstrucción.

Conservar `FORGEJO_RELEASE_READ_TOKEN`: el espejo Git no replica la información
de releases estables/borradores, y una etiqueta sola no autoriza la entrega.
Conservar `PUBLICATION_TOKEN`, la firma Android y la firma separada del índice
F-Droid mientras sus consumidores sigan activos. Los destinos YunoHost, Flatpak,
Home Assistant y F-Droid mantienen URLs, versiones e identidades de firma.
No cambiar ni republicar una release existente para probar esta migración.

Para volver temporalmente al origen previo, seleccionar `forgejo` y esperar a
que termine cualquier trabajo en curso. No mover etiquetas ni sustituir
archivos ya publicados. La reversión no habilita Actions privadas.
