# Continuar Headscale Gateway

Punto de entrada para desarrolladores y agentes de IA. Antes de editar, lee
`README.md`, `docs/ESTRUCTURA.md`, `docs/ESTADO_DESARROLLO.md` y la guía del
componente. Para preparar el entorno por primera vez, sigue
`docs/EMPEZAR_DESARROLLO.md`. Comprueba `git status`, rama, último commit,
remotos e instrucciones locales. Respeta los cambios ajenos y el alcance pedido.

## Arquitectura y fuentes

El motor Go y el panel de `src/` son comunes a Linux, Windows, macOS, Android,
Home Assistant y YunoHost. Android adapta ciclo de vida y túnel en `android/src/`.
Los instaladores se mantienen en `packaging/`. No crees otro servidor o API
para una plataforma. El proyecto se desarrolla principalmente en español.

| Área | Fuente | Comprobación |
| --- | --- | --- |
| Arranque y recarga | `src/main.go`, `startup_*.go`, `runtime_*.go` | Go y despliegue aislado |
| Proxy y DNS | `src/proxy*.go`, `src/dns_*.go` | Transporte, propiedad y limpieza DNS |
| Panel y API | `src/internal/admin/` | Go, JS, referencia e i18n |
| Persistencia | `src/internal/state/` | Migración, restauración y concurrencia |
| Copias y perfiles | `src/internal/securebackup/`, `configtransfer/`, `src/admin_backup_restore_*` | Integridad, permisos y compatibilidad |
| Coordinador Headscale | `src/internal/headscalecontrol/`, `src/admin_headscale_*` | Revisión, rollback, permisos y clientes Windows/Linux |
| Entidades HA | `custom_components/headscale_gateway/` | `tests/homeassistant/` |
| Aplicación HA | `packaging/homeassistant/` | Python y contenedor |
| Paquete YunoHost | `packaging/yunohost/` | Python, nginx/NSS y aceptación aislada |
| Android | `android/src/`, `src/mobile_android.go` | Motores de ambas arquitecturas, Lint e instrumentación |
| Bandeja | `src/desktop/` | `npm test` y comprobación visual pertinente |
| Manual | `docs/`, documentos de plataforma, `mkdocs.yml` | MkDocs estricto y enlaces HTML |
| Publicación | `packaging/releases/automation/` y sus workflows | Pruebas del controlador y destinos permitidos |

`addons/` y `yunohost/` son instaladores generados y versionados. Edita las
fuentes y ejecuta `python3 -B tools/prepare_git_install.py`; el manifiesto detecta
modificaciones manuales. Mantén `packaging/homeassistant/config.yaml.in` como
plantilla: el archivo descubrible es `addons/headscale_gateway/config.yaml`.

## Contratos obligatorios

- SQLite es la configuración persistente; el arranque aporta opciones del proceso
  y valores iniciales. Actualizar conserva credenciales, MFA, identidad VPN,
  certificados, claves y datos.
- Un solo proceso utiliza cada base y cada identidad tsnet. Nunca pruebes con
  la SQLite de una instalación activa.
- Sesión web, rol, alcances Bearer, exposición API y CSRF son comprobaciones
  distintas. Loopback o una cabecera recibida no acreditan un administrador.
- El controlador local de Headscale se vincula como administrador del anfitrión;
  un perfil importado no concede privilegios locales. Los demás Gateway usan
  delegación explícita, TLS verificado y alcances limitados. No hay reenvío en cadena.
- Las rutas de un contrato remoto pertenecen al sistema de destino: las rutas
  Linux del actuador no se interpretan con `filepath` del cliente Windows.
- DNS elimina solo registros dentro de la propiedad del Gateway. Un fallo de
  limpieza no se oculta ni autoriza a borrar registros ajenos.
- La restauración valida la carpeta temporal antes de programar su limpieza.
  Los transportes del proxy conservan la escritura del cuerpo en respuestas 101.
- Errores, informes y logs excluyen tokens, contraseñas y claves privadas.
- Conserva `LICENSE`, `NOTICE`, procedencia y avisos de terceros. No retires los
  fuentes correspondientes necesarios para redistribuir Electron o FFmpeg.
- No cambies RAM, CPU, red, certificados o servicios de una VM por iniciativa
  propia para resolver un fallo de pruebas. Distingue un fallo del laboratorio
  de un fallo del producto. Una petición de detener revoca el trabajo de pruebas.

## Secuencia de trabajo

1. Delimita el cambio, lee el recorrido existente y reproduce el fallo pertinente.
2. Edita fuentes y documenta comportamiento, rutas, parámetros y migraciones.
   Usa comentarios propios en español cuando expliquen finalidad o confianza;
   conserva identificadores públicos, `//go:build` y textos originales de terceros.
3. Añade pruebas del comportamiento y de sus fallos cuando cambie la lógica.
   Compilar para otra plataforma no equivale a ejecutar allí sus pruebas.
4. Si cambian rutas o mensajes, genera referencia e i18n y verifica por separado:

```sh
python3 -B tools/reference_catalog.py
python3 -B tools/extract_i18n.py
python3 -B tools/check_i18n.py
```

5. Regenera instaladores si cambian motor, versión o plantillas. Ejecuta las
   comprobaciones necesarias, con paralelismo acotado en equipos limitados:

```sh
python3 -B tools/prepare_git_install.py
GOMAXPROCS=2 GOFLAGS=-p=2 bash tools/verify.sh
python3 -B tools/check_privacy.py
```

6. Para el manual, instala `requirements-docs.txt` en un entorno externo al clon;
   ejecuta `python -m mkdocs build --strict` y
   `python3 tools/check_manual.py builds/manual`. Consulta `docs/MANUAL_WEB.md`.
   Home Assistant y YunoHost se documentan en `packaging/`; el manual los incorpora
   con `tools/manual_hooks.py`, sin duplicar páginas editables.
7. Revisa diferencias y archivos nuevos. Actualiza `CONTENIDO.sha256` después
   de preparar el índice. Guarda un commit nuevo y registra resultados reales,
   límites y cómo repetirlos. No presentes una prueba interrumpida como completada.

## Versiones, publicación y autorización

`VERSION` identifica motor y paquetes, con formato `X.Y.Z`. Usa
`python3 tools/set_version.py X.Y.Z` y regenera los instaladores. Las etiquetas
publicadas son inmutables; una corrección posterior pertenece a otro commit.

El flujo vigente es Forgejo privado → espejo GitHub privado → compilador público
`headscale_gateway_releases` → distribuciones, tiendas y manuales. El controlador
lee una release estable de Forgejo y el commit etiquetado. Un push a main no
publica por sí solo. Las Actions de Forgejo no forman parte de este recorrido.
GitHub no devuelve commits, estados ni paquetes a Forgejo. Lee
`docs/PUBLICACION.md` antes de tocar automatización.

Sube por SSH solo cuando esté autorizado. `main` requiere una solicitud de fusión
en Forgejo. No retires sus protecciones ni fuerces un push para evitar esa vía.
Verifica las referencias remotas después de subir. Si se pide preparar sin
subir, no hagas push, no crees etiquetas o releases y no modifiques destinos
públicos ni sus secretos. Actualizar las fuentes del manual no implica publicar
GitHub Pages de inmediato.

## Datos y limpieza

`builds/`, `bin/` y las entregas locales son resultados, no fuentes. Revisa su
contenido y procesos antes de retirarlos. Conserva fuera del clon las claves
SSH, firma Android, bases, copias, perfiles y diagnósticos privados. Usa nombres,
redes e identidades ficticios en tests y capturas. Nunca extraigas secretos de
Actions ni los pegues en informes. Sigue `docs/SEGURIDAD.md` para auditar y limpiar.
