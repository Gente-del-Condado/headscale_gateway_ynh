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
