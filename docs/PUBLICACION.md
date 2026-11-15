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
Es fine-grained, limitado a los ocho repositorios públicos indicados y con
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

## Publicar una nueva versión desde Forgejo

1. Prepara un `main` válido: aumenta `VERSION` con `tools/set_version.py`, actualiza
   las fuentes y los instaladores generados exigidos por el manifiesto y sube por
   SSH a Forgejo. GitHub recibe el espejo, ejecuta calidad y actualiza paquetes,
   ambas tiendas y manuales automáticamente. Una CI fallida bloquea la publicación.
2. Publica en Forgejo una **release estable** con etiqueta `vX.Y.Z`, igual a
   `VERSION`, apuntando al commit vigente de `main`. Puedes publicar solo las notas:
   GitHub construye los instaladores desde los fuentes. Una etiqueta sin release,
   un borrador o una prerelease no autorizan las descargas generales.
3. **Detectar versiones de Forgejo** se ejecuta al recibir main o una etiqueta,
   después de calidad y, como respaldo, cada hora. Solo consulta Forgejo mediante
   GET con un token de lectura. La cola y los horarios de GitHub pueden retrasarlo;
   no se necesita pulsar Run workflow. No se envía ningún cambio a Forgejo.
4. El detector despacha **Preparar entrega completa** para el SHA aprobado.
   Construye motores, escritorios con sus fuentes exactos y Android Go compartido:
   APK directo firmado, APK F-Droid sin firma y AAB firmado solo preparado.
5. Su finalización correcta activa **Preparar y publicar release privada**.
   Verifica origen, versión, sumas y descargas y publica la entrega privada.
   **Preparar distribución pública** se activa por la finalización de ese flujo:
   no depende del evento release creado mediante `GITHUB_TOKEN`, que no iniciaría
   otra Action. Construye Debian/Fedora y Flatpak y comprueba su instalación.
6. **Publicar descargas públicas** espera calidad y preparación correctas del
   mismo SHA de main. Exporta los dos derivados nuevos y publica en los cuatro
   destinos, verificando los archivos y sus descargas anónimas. Los archivos y
   etiquetas ya publicados se conservan. Una versión completa no se recompila.

La cadena utiliza tres enlaces `workflow_run` después de la compilación; no se
excede su límite en GitHub. `workflow_dispatch` se conserva como mecanismo
interno llamado por el detector y como recuperación administrativa, no como paso
manual de una publicación normal. No avances main a otra revisión durante la
entrega: el cambio se detecta y se detiene la publicación de la revisión anterior.

### Credenciales

En el principal privado de GitHub se mantienen:

- `PUBLICATION_TOKEN`: Contents lectura/escritura en los ocho destinos públicos.
- `FORGEJO_RELEASE_READ_TOKEN`: solo `repository:read`, limitado al principal de
  Forgejo. Una redirección al SSO o una respuesta que no sea JSON detienen el flujo;
  nunca se reenvía el Bearer a otro origen ni al portal de autenticación.
- `ANDROID_SIGNING_BUNDLE`: copia de la identidad Android existente, contraseña
  y alias dentro de un secreto cifrado de Actions. Solo se materializa en una
  carpeta temporal privada; se verifica su certificado público fijado y se retira
  al finalizar. No se genera una clave distinta ni se distribuye en artefactos.

La compilación comprueba firma, identidad, versión y bibliotecas del APK y AAB.
No afirma una actualización en un teléfono real en cada entrega: esa aceptación
sigue siendo una prueba adicional. Play Store y F-Droid quedan preparados; no se
envían aplicaciones ni solicitudes a sus catálogos. Flatpak se distribuye fuera
de Flathub.
