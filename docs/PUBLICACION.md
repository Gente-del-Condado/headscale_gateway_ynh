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
Lee la API de Forgejo con un token limitado y descarga solo
el árbol de fuentes de la etiqueta publicada; no copia el historial privado.

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
4. Cada trabajo descarga el mismo commit y vuelve a comprobar etiqueta, versión
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
de Electron/Chromium/FFmpeg, sus parches, avisos y sumas se distribuyen aparte en
la misma release pública. Solo el archivo grande de fuentes Chromium usa partes.
Conserva esos fuentes y avisos al redistribuir el escritorio.

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

## PiVigia y JackSignal

Sus flujos reciben el espejo desde Forgejo y publican directamente en GitHub
tras calidad correcta del mismo SHA de main. Los pull requests no publican.
Sus secretos PUBLICATION_TOKEN permanecen en los respectivos principales
privados, limitados a sus destinos públicos. Esta migración del compilador de
Headscale no cambia sus credenciales ni sus flujos.
