# Publicación en una dirección

Forgejo conserva el principal privado. Su espejo privado de GitHub recibe las
ramas y etiquetas. GitHub Actions prueba la revisión y publica las distribuciones
públicas. Ningún publicador de GitHub escribe en Forgejo.

| Principal privado | Distribución individual | Tiendas compartidas |
| --- | --- | --- |
| headscale_gateway | headscale_gateway_ynh y headscale_gateway_ha | Mis_app_ha y Mis_componente_ha |
| pivigia | pivigia_ha | Mis_app_ha y Mis_componente_ha |
| jacksignal | jacksignal_ha | Mis_app_ha y Mis_componente_ha |

Edita las fuentes, aumenta la versión cuando cambie el contenido instalable y
sube el commit a Forgejo por SSH. Los publicadores esperan una ejecución correcta
del flujo de calidad y descargan su SHA exacto. Omiten las revisiones que ya no
sean main al comenzar la publicación. Los pull requests nunca publican.

`PUBLICATION_TOKEN` se guarda en los secretos de Actions de los tres principales.
Es fine-grained, limitado a los seis repositorios públicos indicados y con
Contents de lectura y escritura. No necesita Administration, Workflows ni acceso
a Forgejo. Los publicadores conservan las otras aplicaciones de cada tienda y
no sobrescriben etiquetas ni recursos publicados con otro contenido.

Las entregas a distintos repositorios son independientes: comprueba todas las
ejecuciones antes de anunciar una versión. Ante un fallo transitorio, reejecuta
el flujo de calidad; su finalización correcta activa de nuevo los publicadores.
Ante un defecto, corrígelo primero en Forgejo. No evites las pruebas para publicar.

El manual se genera desde Headscale Gateway y se publica en gh-pages de sus dos
distribuciones. Android utiliza la dirección estable
https://gente-del-condado.github.io/headscale_gateway_ynh/.
Renombrar un repositorio conserva releases y permisos, pero sus enlaces de
GitHub Pages deben actualizarse expresamente. Los paquetes públicos excluyen
claves, bases de datos e historial privado y conservan los fuentes y licencias
correspondientes a los binarios distribuidos.

Antes de retirar derivados de Forgejo, conserva una copia recuperable y verifica
que todos sus publicadores utilizan ya los destinos nuevos, incluidos los de
otras aplicaciones de las tiendas compartidas.

El paquete YunoHost 1.4.7~ynh2 conserva los informes de su laboratorio real.
Las comprobaciones de nginx/NSS en contenedor son complementarias: no sustituyen
package_check ni la actualización con datos y secretos. No se solicita su
entrada en el catálogo oficial. No ejecutes máquinas virtuales del laboratorio
ni compilaciones grandes en el Linux del usuario; utiliza GitHub para esas tareas.

El publicador YunoHost también mantiene las instantáneas públicas de fuentes en
`upstream-source` y etiquetas `source-vX.Y.Z`, sin historia privada ni claves.
Son los fuentes completos de Android y del proyecto; `main` sigue conteniendo
solo el paquete YunoHost. Las etiquetas existentes no se desplazan.

Los destinos se resuelven por su identificador estable de GitHub. Así se puede
comprobar la publicación antes de renombrarlos y conservarla después, sin
escribir en Forgejo ni ampliar los permisos del token.

## Descargas públicas y nuevos paquetes Linux

El principal privado publica los instaladores y sus fuentes en
[headscale_gateway_releases](https://github.com/Gente-del-Condado/headscale_gateway_releases).
Home Assistant y YunoHost conservan sus repositorios y releases propios.
`headscale_gateway_flatpak` recibe el paquete específico Flatpak. No se publica
el historial privado. PUBLICATION_TOKEN incluye estos dos nuevos destinos
públicos, además de los seis originales, con Contents de lectura y escritura.

**Preparar distribución pública** comprueba los paquetes Debian/Fedora, construye
e instala Flatpak y prepara los fuentes correspondientes sin recompilar en el
Linux del mantenedor. **Publicar descargas públicas** exige además calidad
correcta del mismo SHA vigente de main. Publica por separado en cuatro destinos,
verifica los borradores y comprueba las descargas sin credenciales. Un archivo
publicado con otro contenido nunca se reemplaza. Para reintentar, reutiliza los
artefactos preparados; no cambies una etiqueta ni un instalador publicado.

Los instaladores de bandeja son archivos pequeños completos. Los fuentes de
Electron/Chromium/FFmpeg se proporcionan aparte en la misma release, con sus
versiones, parches y sumas. Solo el archivo grande de fuentes Chromium utiliza
fragmentos. Esto no modifica los binarios 1.4.8 ni la firma Android.

Consulta [Debian y Fedora](LINUX_NATIVO.md), [Flatpak](FLATPAK.md) y
[descargas públicas](DESCARGAS_PUBLICAS.md). El Flatpak es del motor completo,
consola y panel web; no se solicita inclusión en Flathub ni se afirma aceptación.
Play Store continúa solo preparado.
