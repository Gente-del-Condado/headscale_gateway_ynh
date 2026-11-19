# Control público de compilación

Este directorio y `../.github/workflows/` son fuentes del control de publicación
que se exporta a `Gente-del-Condado/headscale_gateway_releases`. Se mantienen
primero en Forgejo; el control no escribe en Forgejo ni replica su historial.

La primera comprobación `Verificar lectura privada de Forgejo` es un diagnóstico manual para el mantenedor. Consulta la API con un token de solo lectura,
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

## Validar una revisión antes de crear la release

`Validar revisión antes de publicar` comprueba un commit exacto de una rama
`codex/` de Forgejo. El mantenedor indica rama, SHA y versión; el lector verifica
que la rama sigue apuntando a ese commit y que los paquetes generados coinciden.
No acepta otra rama, no publica paquetes y no dispone de credenciales de firma
ni de escritura en destinos. Usa el token de lectura ya existente solo al descargar
el árbol; las pruebas se ejecutan después sin ese secreto en su entorno.

Ejecuta seguridad, motor, panel y conservación, el complemento Home Assistant,
el proxy SSO de YunoHost y la aceptación del servicio nativo en un Windows
desechable. Las pruebas del SCM solo se activan dentro de ese runner, nunca al
hacer `go test` en el PC del usuario. La publicación estable mantiene su circuito
independiente y sus comprobaciones obligatorias.

## Fuentes reutilizables de escritorio

Las nuevas versiones separan los archivos grandes en una release
`desktop-sources-electron-VERSION-HUELLA` del mismo repositorio público. La huella
procede del lock completo y de la fragmentación; la publicación rechaza cambios
de contenido y conserva «Latest» para la aplicación. La 1.4.16 no pierde archivos.

Durante la exportación de mantenimiento se copian también:

- `tools/desktop_sources.py` → `automation/desktop_sources.py`.
- `tools/split_release.py` → `automation/split_release.py`.
- `tools/publish_public_release.py` → `automation/publish_public_release.py`.
- `packaging/desktop/electron-sources.lock.json` → `automation/desktop-sources.lock.json`.

El workflow `desktop-sources.yml` prepara el primer conjunto en un runner
público, reutilizando los archivos verificables de la 1.4.16 sin editarlos. Para
un futuro lock ausente en aquella release obtiene fuentes upstream por HTTPS y
exige los tamaños y SHA-256 fijados. Las publicaciones normales preparan el
conjunto desde los fuentes del runtime, lo contrastan y reutilizan la release
existente sin volver a subir GB. La primera publicación verifica las descargas
anónimas completas; las reutilizaciones comprueban los digest de todos los
adjuntos y descargan anónimamente índice y sumas. Un fallo bloquea instaladores.

## Comprobar la siguiente entrega sin publicarla

El ensayo `test_desktop_sources.py` prepara datos mínimos de una entrega
hipotética 1.4.17: ejecuta el particionador real de las cuatro distribuciones y
comprueba que los adjuntos de Electron quedan fuera. Las pruebas de reutilización
impiden cualquier subida o edición cuando la release existente coincide.

`tools/check_release_reuse.py --lock packaging/desktop/electron-sources.lock.json`
consulta la release real sin tokens ni escrituras, contrasta lock, índice,
fragmentos y digest de todos los adjuntos y lee sus sumas. Se exporta como
`automation/check_release_reuse.py`, junto con `tests/test_desktop_sources.py`
como `automation/test_desktop_sources.py`. El workflow omite la etapa que recibe
PUBLICATION_TOKEN si el conjunto ya existe. No descarga otra vez los archivos
grandes ni crea una nueva versión Gateway para comprobarlo.

Las copias derivadas para el manual son `manual-project-readme.md` (README
principal), `manual-downloads.md` (README de releases), `manual-desktop.md`
(README de escritorio), `manual-licenses.md` y `manual-publication.md` (guías
correspondientes de docs/). También se exportan `manual-state.md`,
`manual-changes.md` y `manual-verification.md` desde el estado, changelog y
validación vigentes. Se copian desde Forgejo al actualizar el control.


## Evitar ejecuciones repetidas

`release-public.yml` excluye las guías y el controlador de retención de su filtro
de cambios. Invoca los workflows reutilizables del manual y retención solo si
termina el trabajo de publicación real. Las guías conservan su propio disparador;
la retención conserva su programación diaria. El chequeo inicial de runner se
ha retirado. No se reactiva ningún temporizador ni credencial de YunoHost.

## Lectura desde el espejo GitHub privado

La variable `HGW_SOURCE_BACKEND=github-mirror` activa la lectura por SHA desde
el espejo privado `Gente-del-Condado/headscale_gateway`. El token
`MIRROR_READ_TOKEN` solo necesita Contents y Metadata de lectura en ese único
repositorio; se guarda en el controlador público. El valor inicial `forgejo`
permite preparar y verificar la migración antes de cambiar el origen.

La exportación de mantenimiento debe copiar también el lector común
`packaging/homeassistant-store/github_mirror.py` y su prueba
`test_github_mirror.py` a `automation/`. Se mantiene una única fuente compartida
con los publicadores de JackSignal y PiVigia.

El workflow `mirror-read-check.yml` verifica releases, igualdad de etiquetas,
archivo, manifiesto y sumas sin publicar, firmar ni acceder a los otros
repositorios privados. Un error de lectura nunca activa una descarga alternativa.
El control conserva Forgejo para autorizar releases estables y valida de nuevo
ambas referencias antes de publicar. Consulta `docs/PUBLICACION.md`.
