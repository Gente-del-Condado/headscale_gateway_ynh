# Estado de desarrollo y siguiente entrega

## 1.4.20: donativos Ko-fi preparados para publicación

Acerca de → Donativos enlaza a `https://ko-fi.com/gentedelcondado` con un enlace
HTML del panel común. Android utiliza su apertura de enlaces externos existente.
No se incorporan widgets, credenciales ni procesamiento de pagos. Incluye el
texto en español e inglés y la explicación en el manual. Se prepara la versión
común 1.4.20 para publicación por solicitud de fusión en Forgejo. La recepción
automática en los destinos públicos se verifica tras publicar la release estable.

La entrega combinada con main supera la verificación completa, 26 pruebas del
controlador público y 31 de la tienda, además del manual estricto (51 páginas y
3306 enlaces locales). La subida SSH requiere la clave de Forgejo cargada; no
se ha creado aún la release estable de 1.4.20.

Validación: verificación completa correcta (102 pruebas Python, 43 del panel,
5 de escritorio, pruebas Go, vet y compilación), referencia e i18n actualizados,
manual estricto y 3302 enlaces locales correctos.

## Tienda F-Droid propia publicada

Se añade un controlador independiente en `packaging/fdroid-store/`, exportable a
`Gente-del-Condado/Mis_app_fdroid`. Recoge únicamente releases públicas completas,
comprueba firma APK fijada, identidad y sumas; genera índices v1/v2 con una firma
propia y publica Pages desde Actions. No recompila ni vuelve a firmar las APK.
La aplicación conserva 1.4.19 y su firma; esta tarea no mueve etiquetas existentes.

El ensayo local con fdroidserver 2.4.5 genera y verifica índices firmados con las
APK públicas 1.4.19 y 1.4.18. Pasan doce pruebas de selección, identidad, firmas,
sumas, retención y omisión de trabajo sin cambios. La clave del índice se guarda
fuera del proyecto. El secreto Actions está guardado y los trabajos de generación
y despliegue en GitHub han terminado correctamente. Se han descargado por HTTPS
ambas APK y verificado las firmas de los índices v1/v2 y sus sumas. La corrección
del entorno temporal del workflow se fusionó por Forgejo #47.

La prueba real en F-Droid 2.0.3 de la tablet física ha pasado: alta con huella,
catálogo, versiones 1.4.19/1.4.18 y descarga de 1.4.19. Android la reconoce como
actualización de la APK existente y muestra la confirmación de conservación de
datos. Se canceló esa instalación: esta tarea prueba la tienda, no cambia la
versión instalada. La consulta sin cambios devuelve `cambios=false`.

El primer intento falló con EAI_NODATA al resolver el dominio con la VPN activa.
Con autorización se pausó solo la VPN de las aplicaciones, manteniendo los
servicios del Gateway; por Wi-Fi el alta y la descarga funcionaron. Después se
reconectó la VPN y se comprobó su servicio activo. No se cambian DNS, configuración
ni datos. Play Store permanece solo preparado.

El catálogo incorpora el PNG existente de Headscale Gateway en los metadatos
localizados. El ensayo real verifica el icono referenciado y su suma en el índice
firmado; la publicación rechaza iconos ausentes o alterados. No cambia la APK
ni su firma. La comprobación visual de esta corrección se realiza tras desplegar.

## 1.4.19: protecciones por plataforma validadas

El portal Linux incorpora restricciones systemd adicionales sin ampliar sus
privilegios. El actuador opcional de Headscale conserva su unidad independiente.
Android usa capacidades temporales del documento superior para sus descargas;
Flatpak mantiene solo red y comprueba loopback sin usar proxies del entorno.

Han pasado la suite general, Lint Android, compilación de motores Android arm64
y x86_64, pruebas del puente y exportaciones en la tablet física, y pruebas del
motor bajo las unidades YunoHost/Debian y una sesión Fedora con aislamiento.
El Flatpak de laboratorio instalado usa permisos efectivos de red únicamente;
conserva datos privados y ejecuta las pruebas TLS/DNS/restauración.
La instalación/reinstalación y retirada de DEB/RPM en contenedores conserva datos.
Waydroid no se ha utilizado. No se cambian recursos ni red de las VM.

El instalador YunoHost encontró repositorios APT inaccesibles en la VM. Las
dependencias exigidas ya estaban instaladas. Para el ensayo se retiró únicamente
su aprovisionamiento APT de una copia del manifiesto y se sirvieron los recursos
por loopback, conservando sumas y scripts. Esta adaptación del laboratorio no
se publica; el paquete de producción conserva sus recursos APT y URL originales.
La instalación anterior y la semilla de SSO, configuración, servicios y copia
cifrada pasaron. El primer intento de actualización se bloqueó durante su copia
previa con un fallo del kernel 6.1.0-55 en ext4. Tras autorización del usuario se
arrancó el kernel 6.1.0-54 ya instalado, solo para ese arranque; no se eliminaron
kernels ni se modificaron RAM, CPU o red. Un archivo de metadatos de la primera
copia quedó vacío tras el fallo; se conservó como diagnóstico y se creó una copia
ficticia nueva con la misma clave antes de repetir la aceptación.

Con 6.1.0-54 pasó la actualización real 1.4.18~ynh1 → 1.4.19~ynh1. Se verificaron
SSO, rechazo de secreto de proxy incorrecto, servicios, ajustes, huellas de clave
maestra y arranque, descarga cifrada, PKI, descubrimiento y exportación portable.
La adaptación sin aprovisionamiento APT solo afecta a la copia del laboratorio;
el paquete publicado conserva dependencias y URL de producción. La VM quedó con
la aplicación de laboratorio activa. La selección de kernel no cambia el valor
predeterminado para próximos arranques. Play Store permanece solo preparado.
La publicación se tramita por solicitud de fusión en Forgejo.

## 1.4.18: AppArmor preparado para publicación

Se incorpora un perfil restrictivo al paquete y al instalador generado. Probado
con Supervisor real en una copia aislada de Home Assistant OS 18.4, amd64:
perfil cargado en enforce, protección activa y clasificación 7/8. Se conservan
host_network, Ingress y el motor Go; no se solicitan capacidades nuevas.
Python desactiva la caché sobre sus bibliotecas de solo lectura.

Pasaron las peticiones reales de Ingress/SSO/CSRF, PKI, descubrimiento, copia
SQLite cifrada, descarga y exportación del perfil. Las pruebas Go de TLS local,
renovación, DNS, restauración e identidad se ejecutaron dentro del perfil.
El reinicio conservó la clave maestra y las opciones. Las comprobaciones
negativas bloquearon shadow, escritura sobre programas y ejecución de shell.
Estos ensayos no acreditan una conexión a Headscale ni una emisión ACME externa.
El perfil también pasó en una VM nueva
HAOS 18.4 aarch64 emulada con QEMU/TCG, Supervisor 2026.11.0: 7/8, enforce,
las 14 pruebas Go bajo confinamiento y el comprobador de panel y bloqueos.
El reinicio completo de esa VM conservó SSH y claves y arrancó Gateway
automáticamente con el perfil activo. Core quedó listo para el alta inicial.
La aplicación existente de la VM amd64 no se modificó.
VERSION y los paquetes están sincronizados en 1.4.18. La solicitud de fusión
y la release estable de Forgejo activarán el recorrido automático de GitHub.
La validación de la tienda y del paquete publicado se registrará al completarse.
Play Store permanece solo preparado.


## Mantenimiento de Actions (sin nueva versión del motor)

El control público mantiene app, integración y tiendas desde un SHA de Forgejo.
El plan evita trabajos sin cambios; las imágenes solo se solicitan si hay árboles
pendientes. Las comprobaciones unitarias cubren propiedad de archivos, sumas,
etiquetas inmutables, conservación de otros componentes y planificación sin
cambios. Los flujos antiguos se retiran por solicitudes de fusión en el origen.
El manual sigue privado en Olivar y no se activa ningún servicio de laboratorio.

Comprobado el flujo público [44213839402](https://github.com/Gente-del-Condado/Mis_app_ha/actions/runs/44213839402):
PiVigia y JackSignal superaron calidad; se publicaron sus dos distribuciones y
las dos carpetas del catálogo con recibos de SHA y versión. No hubo imágenes
pendientes y el trabajo de imágenes se omitió. Los ensayos locales pasaron 100
pruebas generales, 18 del controlador de tienda y 21 del controlador de releases;
el manual estricto pasó 50 páginas y 3171 enlaces. Estas pruebas de mantenimiento
no equivalen a actualizar instalaciones reales de las aplicaciones.

## 1.4.17: entrega de mantenimiento

La entrega incorpora la separación y reutilización de fuentes de Electron y las
guías de descargas actualizadas. Conserva el motor común y la firma Android.
La publicación exige la solicitud de fusión en Forgejo y todas las comprobaciones
del compilador público; la versión declarada no acredita por sí sola su resultado.
Play Store permanece solo preparado.

## 1.4.16: publicada y verificada

La 1.4.16 se publicó mediante la solicitud #32 de Forgejo y se replicó en
GitHub con commit `4724ff7d449eb526ffc959f926cf4392f884eb00`. La
[CI pública](https://github.com/Gente-del-Condado/headscale_gateway_releases/actions/runs/43798821660)
terminó correctamente, incluida la suite y compilación Windows nativa. Se
verificaron los seis destinos, ambas webs Pages y 45 descargas anónimas con
SHA-256. Play Store continúa solo preparado.

Incluye:

- Contrato de rutas del controlador Linux validado como POSIX también desde
  Windows; pruebas de regresión sin omitir esa plataforma.
- Retirada de workflows privados desactivados y del publicador antiguo de
  Forgejo. El compilador público sigue siendo el único publicador.
- Guía inicial para un desarrollador nuevo, instrucciones de agentes actualizadas,
  mapa de fuentes, README de paquetes y flujo de publicación coherentes.
- Comprobación local de privacidad integrada en `tools/verify.sh` y reglas de
  Gitleaks que distinguen las sumas de los manifiestos de las credenciales.
- Retirada de laboratorios, cachés y entregas antiguas del árbol de trabajo.
  Los originales y diagnósticos privados se conservan fuera del proyecto;
  la firma estable Android y el historial Git permanecen intactos.

Las comprobaciones locales completadas se registran en
[Validación](VERIFICACION_FINAL.md): motor y suites generales, auditorías Go/npm,
Windows bajo Wine, paquetes, exportación y manual estricto. Los informes completos de mantenimiento son
locales y no se publican si contienen datos de instalaciones.

## Situación de 1.4.15

La etiqueta estable de Forgejo y el espejo GitHub contienen los cambios del
motor común: DNS de la Tailnet, restricciones OIDC, observador y control local
o delegado de Headscale. La publicación de instaladores quedó bloqueada por
[el fallo del trabajo Windows](https://github.com/Gente-del-Condado/headscale_gateway_releases/actions/runs/43784256540/job/133056107526).
No se presenta aquella ejecución como una distribución completada.

La causa era `filepath.Join` y `filepath.IsAbs` aplicando reglas Windows a las
rutas del actuador Linux. La 1.4.16 utiliza el contrato POSIX del destino y sigue
rechazando rutas relativas, ambiguas, Windows y caracteres de control.

La APK 1.4.15 se compiló con la firma existente y se instaló en la tablet. La
prueba posterior de instalación limpia y conexión entre la tablet y la VM se
**detuvo por petición del usuario**. En esa VM se instalaron Dex y Headscale;
la configuración nueva del Gateway, Technitium y la integración Dex adicional
no quedaron completadas. No se reanudan por el hecho de continuar el desarrollo.

## Qué debe hacer el siguiente mantenedor

1. Leer este estado, `AGENTS.md`, la guía inicial y `git status`; no asumir que
   una rama o una versión local ya está publicada.
2. Repetir las comprobaciones del cambio que vaya a realizar. No hace falta una
   VM ni credenciales productivas para modificar la documentación o ejecutar Go.
3. Para retomar las pruebas detenidas, acordar expresamente el alcance y utilizar
   identidades aisladas. No cambiar recursos de VM ni importar claves productivas.
4. Para otra versión, seguir [PUBLICACION.md](PUBLICACION.md), comprobar réplica
   y CI y conservar inmutables las etiquetas y los archivos ya publicados.

La autenticación OIDC del Gateway y las restricciones OIDC de Headscale son
funciones distintas. Configurar el laboratorio Dex/Technitium no es una
condición para ejecutar el motor común ni una función ya validada en esta entrega.

## Mantenimiento posterior a la 1.4.16

Se separa la publicación de los fuentes Electron y sus dependencias en una
release reutilizable por lock, conservando los enlaces antiguos. Este cambio
del publicador no recompila ni reemplaza la 1.4.16 y no cambia VERSION. Las
siguientes entregas de Gateway enlazarán el conjunto verificado en lugar de
duplicar los archivos grandes.

El publicador cuenta con un ensayo aislado de la próxima entrega (1.4.17 como
dato de prueba), una barrera contra adjuntos de terceros mezclados y una
comprobación pública que evita volver a preparar o subir un conjunto existente.
El ensayo no cambia VERSION, crea etiquetas ni publica otra aplicación. Las
guías vigentes se actualizan en ambas webs sin modificar los instaladores.

## Migración del lector de Gateway al espejo privado

Preparado el selector de origen del controlador público y un diagnóstico sin
publicación. El modo GitHub exige que la release estable de Forgejo y la
etiqueta del espejo coincidan antes de descargar y antes de publicar. No
cambia VERSION ni reconstruye por sí solo la entrega existente. La activación
requiere el token limitado del espejo y una comprobación pública satisfactoria;
no debe confundirse la preparación local con la migración ya activada.
