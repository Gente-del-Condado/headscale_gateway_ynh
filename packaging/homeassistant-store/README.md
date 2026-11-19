# Consumidores públicos de la tienda Home Assistant

El workflow `sync-forgejo.yml` se ha retirado. JackSignal y PiVigia ya se leen
anónimamente desde sus repositorios públicos mediante `sync-public-apps.yml`.
`PUBLIC_APP_MIGRATIONS=jacksignal,pivigia` selecciona ambos consumidores.
`FORGEJO_APPS_READ_TOKEN` y `DISTRIBUTION_TOKEN` dejan de ser necesarios en la tienda.
Los helpers históricos que comparten validación y preparación con los lectores
actuales se conservan como código; no hay un workflow que invoque su lectura privada.

PGM tiene un consumidor independiente mantenido en su origen Forgejo:
`.github/pgm-publication/sync-pgm-app.yml`. Solo escribe su propia carpeta en
build-source con el GITHUB_TOKEN de Mis_app_ha. Los consumidores llaman al
workflow de imágenes para publicar o recuperar contextos pendientes.
Gateway sigue entregando su contexto con PUBLICATION_TOKEN del compilador.
La tienda no almacena ninguna de esas credenciales de escritura de terceros.

Los controladores de imágenes y los consumidores de JackSignal/PiVigia se
mantienen aquí y se exportan expresamente a los públicos. No ejecutar Actions
en los espejos privados. Conservar versiones, slugs, firmas y recibos.

## Documentación histórica anterior al cierre

Las instrucciones de reversión por sync-forgejo que siguen ya no son operativas;
recuperar código y credenciales requeriría una decisión explícita de mantenimiento.

# Imágenes de Mis_app_ha

Control común mantenido primero en el principal Headscale Gateway de Forgejo.
Se exporta al repositorio público `Gente-del-Condado/Mis_app_ha`:

- `build-images.yml` → `.github/workflows/build-images.yml`.
- Los Python de este directorio → `.github/ha-images/`.
- `check_gateway.py` deriva de `tools/check_container.py`; se actualizan juntos.

Cada origen entrega únicamente su aplicación a `build-source`, después de sus
comprobaciones habituales. La tienda conserva `main` para aplicaciones instalables.
El workflow selecciona árboles exactos pendientes, construye en runners nativos
amd64 y arm64, prueba los contenedores y publica candidatos identificados por el
árbol. Después crea la etiqueta de versión multi arquitectura y exige acceso
anónimo al índice antes de copiar la aplicación a main con `image:`.

Imágenes: `ghcr.io/gente-del-condado/ha-headscale-gateway`,
`ha-jacksignal-installer`, `ha-pivigia` y `ha-private-git-manager`.
Las versiones corresponden a config.yaml. Una modificación de un contexto ya
publicado exige incrementar su versión; no se reemplazan etiquetas estables.
`.images/APP.json` registra árbol, commit de preparación, origen Forgejo y digest.
La publicación conserva otras aplicaciones y reintenta conflictos sin forzar Git.

El GITHUB_TOKEN efímero de la tienda tiene `packages: write` en compilación y
además `contents: write` al actualizar main. La construcción de imágenes no requiere credenciales personales,
claves Android ni acceso de escritura a Forgejo. GHCR puede crear paquetes privados
la primera vez: comprobar su visibilidad pública antes de distribuirlos. El flujo
espera un máximo acotado y mantiene la tienda anterior si no puede descargarlos
anónimamente; nunca incorpora credenciales de registro a los manifiestos.

La primera entrega conserva las versiones actuales: las instalaciones existentes
seguirán utilizando su contenedor hasta una actualización explícita. No se
reinstalan aplicaciones ni se borran datos para efectuar esta migración.

Pruebas: Gateway (Supervisor/Ingress/CSRF/secretos/cierre), PiVigia (arranque,
autenticación y ejecución del modelo OpenCV), Private Git Manager (Ingress,
claves, redacción y rechazo de suplantación), JackSignal (instalación repetida,
copia de la versión anterior y archivos del usuario conservados). Son pruebas
nativas de las imágenes en contenedores desechables, no una actualización de
las instalaciones Home Assistant reales del usuario.

## PiVigia y JackSignal sin runners privados

`sync-forgejo.yml` se exporta como `.github/workflows/sync-forgejo.yml`.
Consulta cada hora el `main` de ambos principales con `FORGEJO_APPS_READ_TOKEN`,
limitado en Forgejo a esos dos repositorios y `repository → Leídas`. Los espejos
privados se conservan; su cuota de Actions no condiciona este recorrido.

`forgejo_apps.py` descarga un SHA exacto, rechaza redirecciones SSO, rutas externas,
enlaces, archivos excesivos e historial Git. Usa un Git local efímero para los
publicadores existentes. Ejecuta las mismas comprobaciones de seguridad y calidad
que sus CI: PiVigia (auditoría, Ruff, pytest, paquetes, manual, ShellCheck y Docker),
JackSignal (auditoría, integración/panel y pruebas de publicación). Ninguna prueba
recibe el token. Solo el contexto publicable con sus sumas y modos se transfiere
al trabajo de preparación; nunca el árbol privado completo.

Antes de escribir `build-source` se vuelve a comprobar el SHA de Forgejo. Un plan
inicial consulta los recibos `.sources/` antes de descargar los proyectos. Si no hay cambios, no inicia calidad ni publicación. Las imágenes
pendientes se comprueban por separado para recuperar un intento fallido. El
workflow reutilizable de imágenes se llama solo si hace falta, incluso cuando
el commit lo escribe GITHUB_TOKEN. Un fallo impide preparar/publicar; no se ignoran las comprobaciones
ni se devuelven estados a Forgejo.

Las integraciones también se publican en `pivigia_ha`, `jacksignal_ha` y sus
carpetas de `Mis_componente_ha`, conservando las demás integraciones. Para ello
`DISTRIBUTION_TOKEN` requiere Contents de escritura solo en esos tres destinos.
Los exportadores se ejecutan sin credenciales durante calidad; el trabajo con
credenciales únicamente valida sumas/modos y copia sus resultados. `.publication/`
registra SHA y versión. Los tags JackSignal existentes se verifican y no se mueven.
El recibo de fuentes se actualiza después de completar las distribuciones; un
fallo permite reintentarlas sin marcar la entrega como terminada. El formato 2
obliga a comprobar una vez las fuentes de la migración anterior.

`store-readme.md` se exporta al README raíz de la tienda; sus aplicaciones solo
se editan en sus fuentes. No se publican tokens en YAML ni se cambian presupuestos.

## Migración preparada: espejo privado → aplicación pública → tienda pública

Los espejos privados son pasivos, con Actions deshabilitado. Las nuevas plantillas
se ejecutan exclusivamente en repositorios públicos y permanecen desactivadas
hasta configurar sus variables de adopción. Añadir estos archivos al principal
no activa ni sustituye el recorrido vigente.

- `publish-mirror.yml` → `.github/workflows/publish-mirror.yml` en `jacksignal_ha`
  y `pivigia_ha`; los módulos Python se exportan a `.github/ha-images/`.
- `sync-public-apps.yml` → workflow de `Mis_app_ha`.
- `sync-public-components.yml` → workflow de `Mis_componente_ha`.
- La versión actualizada de `sync-forgejo.yml` omite solamente las aplicaciones
  enumeradas en `PUBLIC_APP_MIGRATIONS`; sin variable conserva el comportamiento.

Cada aplicación pública recibe su propio `MIRROR_READ_TOKEN`: Contents de lectura
limitado a su espejo privado, sin escritura ni acceso a otras aplicaciones. No
se utiliza el token para pruebas, exportadores ni publicación. El lector verifica
identidad numérica, propietario, nombre y visibilidad privada; fija el SHA, limita
archivos y no reenvía Authorization a codeload. El trabajo de publicación vuelve a
validar el SHA y el recibo en un runner separado; utiliza GITHUB_TOKEN con Contents
de escritura exclusivamente para el propio repositorio público.

La rama pública independiente `public-source` contiene únicamente el contexto de
la aplicación, sus distribuciones autorizadas y `receipt.json`. No conserva el
historial privado. Las tiendas descargan esa rama por SHA sin credenciales y
validan sus sumas, permisos y procedencia antes de copiar. Cada tienda escribe en
sí misma con GITHUB_TOKEN; `Mis_app_ha` mantiene la compilación y validación de
imágenes ya existente. Los consumidores se programan explícitamente: no dependen
de que un push de GITHUB_TOKEN dispare otro workflow.

Adopción por aplicación, empezando por JackSignal:

1. Revisar y desplegar controladores en los cuatro destinos públicos; no activar
   `ENABLE_MIRROR_PUBLICATION` todavía. Mantener credenciales vigentes.
2. Configurar `MIRROR_READ_TOKEN` en el publicador público correspondiente con
   lectura del único espejo privado. Mantener Actions privados deshabilitados.
3. Esperar a que termine cualquier publicación antigua en curso. Establecer
   `PUBLIC_APP_MIGRATIONS=jacksignal` en ambas tiendas. Esto detiene las nuevas
   publicaciones directas de esa aplicación desde Forgejo; las versiones
   instalables anteriores permanecen disponibles. La lista puede ampliarse luego
   a `jacksignal,pivigia`, siempre idéntica en ambos consumidores.
4. Activar `ENABLE_MIRROR_PUBLICATION=true` en `jacksignal_ha` y ejecutar su
   workflow. Verificar integración, release, rama pública y recibo por SHA.
5. Ejecutar consumidores y comprobar imágenes, catálogos y descargas anónimas.
   Solo después incorporar PiVigia y retirar las credenciales que hayan quedado
   sin consumidores. No retirar firmas Android/F-Droid ni claves de espejos.
6. Para volver al productor previo: desactivar el publicador nuevo y esperar sus
   ejecuciones; quitar la aplicación de ambas listas y ejecutar sync-forgejo.
   No mover tags ni sobrescribir versiones publicadas.

Esta plantilla cubre JackSignal y PiVigia. No cambia las releases de Gateway,
PGM, YunoHost ni F-Droid. Gateway conserva su comprobación de release estable de
Forgejo: replicar tags Git no replica el estado draft/prerelease ni las releases.
Migrar ese control exige preservar explícitamente esa intención de publicación.
