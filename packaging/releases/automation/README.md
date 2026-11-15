# Control público de compilación

Este directorio y `../.github/workflows/` son fuentes del control de publicación
que se exporta a `Gente-del-Condado/headscale_gateway_releases`. Se mantienen
primero en Forgejo; el control no escribe en Forgejo ni replica su historial.

La primera comprobación `Verificar lectura privada de Forgejo` se activa al
actualizar el control en main. Consulta la API con un token de solo lectura,
selecciona una release estable y descarga su commit exacto. Rechaza borradores,
prereleases, cambios de etiqueta, rutas externas y enlaces en el archivo. Valida
VERSION y el manifiesto de los instaladores generados. No publica binarios.

Secretos del repositorio **headscale_gateway_releases**, no del espejo privado:

- `FORGEJO_RELEASE_READ_TOKEN`: token Forgejo limitado al principal,
  `repository` en Leídas y los demás permisos sin acceso.
- `PUBLICATION_TOKEN`: token GitHub fine-grained con Contents Read and write
  solo en `headscale_gateway_releases`, `headscale_gateway_flatpak`,
  `headscale_gateway_ynh`, `headscale_gateway_ha`, `Mis_app_ha` y
  `Mis_componente_ha`. No necesita acceso al principal privado.
- `ANDROID_SIGNING_BUNDLE`: la identidad Android existente, nunca una nueva
  clave para esta migración. Se introduce solo en el formulario cifrado.

Las pruebas locales del lector son ligeras:

```sh
python3 -B -m unittest discover -s packaging/releases/automation -p 'test_*.py'
```

El lector no sigue redirecciones autenticadas: una respuesta del SSO o un error
HTTP detienen la ejecución sin imprimir tokens. Las compilaciones y sus fuentes
correspondientes se preparan en runners públicos estándar de GitHub; el principal
y su historial permanecen privados. La comprobación inicial de lectura por sí
sola no afirma que una release ya se haya compilado o publicado.

## Compilación y publicación

`Compilar y publicar desde Forgejo` se activa con cambios del controlador y
consulta Forgejo cada hora (minuto 17 UTC). No requiere lanzar flujos a mano.
Una etiqueta sola no publica: debe existir una release estable de Forgejo.
La versión y el commit se fijan al comienzo; cada trabajo vuelve a comprobarlos.

Las comprobaciones de seguridad Go/npm, Go/JS/Python, Debian, Windows, integración
Home Assistant y contenedores preceden a la compilación de entrega. Después se
construyen Android con la firma estable y Lint, los seis motores, bandejas,
Debian/Fedora, fuentes correspondientes, Flatpak y el manual estricto. Solo
entonces se entregan los resultados a los seis repositorios públicos. El AAB
se prepara, pero no se envía a Play Store. Tampoco se solicita Flathub.

La rama de cada tienda conserva las otras aplicaciones. El repositorio de
descargas conserva su propio controlador. Las sumas se comprueban antes de
publicar y las descargas se verifican sin credenciales. No se reemplaza un
archivo publicado con contenido diferente. Un recibo al final de la release
evita reconstruir versiones ya completadas. Si un intento publica parcialmente
y falla, revisar y recuperar sus resultados: no mover etiquetas ni sustituir
archivos para ocultar el fallo.

GitHub desactiva las programaciones de repositorios públicos tras 60 días sin
actividad. Si el proyecto queda inactivo tanto tiempo, el mantenedor debe
reactivar el flujo. Las compilaciones usan runners estándar públicos y no
consumen la cuota de ejecución del espejo privado. No se suben grandes
artefactos intermedios a Actions; los resultados se publican como releases.

## Guía vigente del control

La exportación de mantenimiento copia `docs/PUBLICACION.md` del principal como
`automation/manual-publication.md` en el control público. Es un derivado; el texto
se edita una sola vez en docs/. Tras una entrega completada, el flujo del manual
superpone esa guía al árbol de documentación de la release, valida todos los
enlaces y actualiza las dos ramas gh-pages. Los fuentes y los instaladores de la
entrega conservan sus archivos originales. Este trabajo no compila el motor.
