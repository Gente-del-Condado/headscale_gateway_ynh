# Validación y límites conocidos

## Validación local del candidato 1.4.14

El 15 de noviembre de 2026 se comprobó el panel compartido en Windows 11 LTSC,
YunoHost y Home Assistant OS, manteniendo la RAM y CPU de las VM. Se apagó
cada VM al terminar su primera aceptación y se volvió a encender para la prueba
conjunta de red. Debian queda pendiente; Fedora se probó con un motor aislado.

Windows pasó el servicio LocalService real, instalación, actualización con datos,
credenciales, configuración y clave maestra conservados, recuperación tras fallo,
reinicio desde el panel y acceso del menú Inicio. Edge verificó el dominio
principal, enlaces HTTP/HTTPS y conservación del foco. La prueba del navegador
utiliza una página con el renderizador real y datos ficticios; el servicio se
prueba con su panel y API reales.

YunoHost 12.1.42 con SSOwat 12.1.1 pasó instalación, actualización forzada del
mismo candidato, copia/restauración y recuperación automática. Se conservaron
configuración, datos, clave maestra y secreto del proxy. Se comprobó el SSO real
con un administrador temporal, CSRF y rechazo de cabeceras de identidad enviadas
directamente al backend. Los recursos del candidato se sirvieron localmente con
sus sumas verificadas; los scripts de instalación fueron los del paquete.

Home Assistant OS 18.4, Supervisor 2026.11.0 y Core 2026.11.1 pasaron instalación
local, Ingress real con identidad administradora, reconstrucción de imagen y
copia/restauración parcial, conservando configuración, datos y clave maestra.
La imagen se compiló con el Dockerfile del paquete y se entregó por un registro
OCI temporal mediante SSH. El ejemplar de laboratorio utiliza un slug separado.
Los navegadores de ambas plataformas comprobaron también los enlaces del panel
instalado, sustituyendo solo la respuesta de estado para probar URL ficticias.

Se instaló el DEB oficial de Headscale 0.29.7, con suma comprobada, en YunoHost.
El coordinador de ensayo usa HTTPS con una CA RSA de laboratorio y DERP/STUN
locales. Windows no validó la CA Ed25519 inicial del ensayo; se reemitió con RSA.
Las CA propias de los Gateways se conservaron. No se cambiaron los DNS, rutas ni
certificados de instalaciones habituales. Windows, YunoHost, Home Assistant y
Fedora intercambiaron tráfico TSMP en ambos sentidos y sus portales respondieron
por HTTPS con la CA individual y el nombre TLS verificados.

La tablet USB con APK `.lab` 1.4.14 pasó arranque, sesión normal, navegación,
conexión a Headscale, ping TSMP hacia los cuatro Gateways y recepción de una
petición HTTPS desde otro nodo con CA verificada. La clave maestra se conservó
entre repeticiones. La instrumentación propaga explícitamente el entorno Java
que hereda el proceso Go; `Os.setenv` solo no actualizaba esa caché. Se prueba
el motor del Gateway: en esta ejecución no se activó la VPN de aplicaciones del
teléfono. La preparación del cliente espera tráfico VPN antes de comprobar
HTTPS, pues `tsnet.Up` no acredita que la ruta hacia un peer ya esté lista.

El coordinador queda como instalación de laboratorio: sus claves de alta y API
caducan en 24 horas, su certificado en 30 días y su CA en 90 días. Las
identidades y datos de los Gateways son persistentes. Los informes de esta
aceptación se guardan localmente en `builds/1414-platform-lab/` y
`builds/windows-links-1414/`; no contienen claves privadas de distribución.
La verificación general pasó 92 pruebas Python, las suites Go y JavaScript,
vet y compilación. El manual se compiló en modo estricto y se comprobaron sus
45 páginas HTML y 2.628 enlaces locales. Play Store continúa solo preparado.

## Validación local del candidato 1.4.13

Revisión del 15 de noviembre de 2026, anterior a la publicación estable. La
validación local con contenedores ha superado 91 pruebas de repositorio, las
pruebas Go y JavaScript, vet, compilación, auditorías Go y npm sin
vulnerabilidades detectadas, actualización con credenciales y clave estables,
integridad SQLite y manual estricto (45 páginas y 2.615 enlaces locales).
Home Assistant pasa Ingress, SSO, CSRF y rechazo de cabeceras suplantadas;
YunoHost pasa nginx/NSS, SSO, raíz/subruta, revocación y conservación de clave.
Esta última prueba es de contenedor y no sustituye una instalación completa en VM.

En Windows 11 LTSC se ha validado el servicio LocalService real: instalación,
actualización con contraseña, configuración, datos y clave conservados,
recuperación tras terminar deliberadamente el proceso y reinicio desde el panel.
El fallo inicial tenía dos causas: el registro automático del SCM al importar
el adaptador Caddy de Technitium y los permisos heredados de archivos al
actualizar. Se utiliza ahora únicamente el proveedor libdns MIT, con procedencia
y licencia conservadas, y se espera al cierre del proceso antes de sustituirlo.
Tailscale estaba detenido por decisión del usuario; esta ejecución no certifica
la coexistencia con Tailscale activo. El panel local no necesita Internet.

CertMagic sigue gestionando ACME. Pebble 2.10.3 y un DNS local de laboratorio
han validado emisión y renovación del nodo y su comodín, cadena y nombres TLS,
clave de cuenta conservada, retirada de TXT propios y conservación de un TXT
manual antiguo. La primera cuenta exige aceptación explícita sin consola; las
cuentas guardadas renuevan aunque falte la opción nueva. Se comprueba además
que los errores del proveedor no exponen el token. No se han tocado registros
DNS ni certificados de producción.

La APK directa mantiene la firma estable, target API 36 y los dos motores
arm64-v8a/x86_64 con alineación ELF de 16 KiB. Incluye LICENSE y NOTICE completos.
La tablet había sido desinstalada por el usuario antes de esta revisión y se
reinstaló con autorización; no se atribuye conservación a aquellos datos ya
retirados. La actualización posterior del candidato se realiza con `adb install -r`,
conservando identidad del paquete y fecha de primera instalación. Android Lint
mantiene cero errores y 23 avisos de mantenimiento. Play Store continúa preparado,
sin publicación en la tienda.

## Revisión de dependencias de la versión 1.4.6

Revisión del 11 de noviembre de 2026. Se actualizan Caddy a 2.11.5, go-jose a
4.1.6, QUIC a 0.63.0 y las dependencias de red y compresión. La compilación
requiere Go 1.27.4 para incorporar las correcciones de la biblioteca estándar.

La bandeja fija glob 14.0.4 y minimatch 11.0.8 mediante `overrides`. El
empaquetador ASAR todavía solicita versiones principales anteriores. Las
pruebas comprobaron la creación y lectura de un ASAR, el empaquetado Linux
completo y el arranque Electron con autenticación de prueba, aislamiento del
renderer y almacenamiento cifrado. `npm audit` y `govulncheck` registraron
cero vulnerabilidades, incluidos los avisos de módulos sin llamadas detectadas.

El aviso GHSA-wwhq-w58m-w29c carece de versión corregida declarada en GitHub,
pero Caddy 2.11.5 ya elimina la segunda expansión de los valores en
`VarsMatcher` y `MatchVarsRE`. Los módulos HTTP de Caddy afectados por ese
aviso no forman parte de los paquetes compilados del Gateway.

Para repetir el análisis desde `src/`, ejecuta
`go run golang.org/x/vuln/cmd/govulncheck@v1.9.0 -show verbose ./...`.
Desde `src/desktop/`, ejecuta `npm ci`, `npm audit`, `npm test` y
`npm run pack`. La prueba `npm run smoke` requiere un escritorio gráfico.

## Preparación de la versión 1.4.7

La versión común se aplica al motor, Home Assistant, YunoHost, la bandeja y
Android. El cliente de bandeja admite una URL base con subruta y limita la
respuesta de la API a 4 MiB mientras la recibe, conservando el rechazo de
redirecciones y de HTTP remoto. Las pruebas HTTP incluyen una subruta real,
una respuesta excesiva y un intento de redirección.

`tools/verify.sh` ha terminado correctamente: contratos Python, panel y
bandeja JavaScript, pruebas Go, variantes comerciales, formato, vet y
compilación Linux. Los dos análisis de Go (módulos y llamadas) y `npm audit`
no detectaron vulnerabilidades en esta revisión. Esto es un resultado fechado,
no una garantía de ausencia futura; los flujos repiten la auditoría antes de
fusionar y publicar.

Android usa el motor Go común en arm64-v8a y x86_64, target API 36 y una clave
estable guardada fuera del repositorio. El verificador comprueba identidad,
versión, ausencia de depuración, firma y alineación ELF de 16 KiB de todas las
bibliotecas nativas. Se preparan APK directo firmado, APK sin firmar para
F-Droid y AAB para Play. El gesto Atrás usa la API moderna desde Android 13;
el inicio conserva la navegación del sistema. Los secretos se excluyen tanto
de las copias en la nube como de la transferencia automática entre dispositivos.

La aceptación en teléfonos físicos, cambios Wi-Fi/datos, suspensión, IPv6 y
proveedores DNS/ACME reales sigue pendiente. El emulador local se cierra con
un fallo de segmentación antes de ofrecer un dispositivo ADB; no se atribuye
una prueba funcional nueva a esa ejecución. Los resultados de Waydroid en
[ANDROID.md](ANDROID.md) son antecedentes de la adaptación del motor, no una
certificación de cada APK nueva. Tampoco se ha publicado en F-Droid ni Play.

La construcción local con `fdroidserver 2.4.5`, desde una exportación Git sin
historial privado, completó el escaneo de fuentes, la compilación de ambos
motores Go y del APK y el escaneo binario. Se usó `build --test --no-tarball
--scan-binary`; no equivale a una construcción en los servidores oficiales ni
a la admisión en F-Droid. El Lint de Android, repetido sin reutilizar tareas,
terminó con cero errores y 23 avisos pendientes de mantenimiento.

El paquete YunoHost incorpora descripción en inglés y español, README generado
con la versión, documentación administrativa completa y pruebas de raíz/subruta
con sesión SSO administradora. El linter oficial ya no registra errores de
empaquetado; señala que la aplicación se mantiene fuera del catálogo,
ni tiene estado y categoría asignados allí. La
[guía de mantenimiento y sus evidencias](../packaging/yunohost/doc/CATALOGO.md) distinguen
estos avisos de los fallos funcionales. Los resultados de `package_check` se
conservan con cada entrega; no se asigna un nivel oficial localmente.

El 14 de noviembre de 2026 se validó `1.4.7~ynh2` en una VM limitada a 2 GiB.
La batería completa duró 34 minutos y 29 segundos: siete operaciones correctas
y un fallo de descarga durante la actualización sobre la misma revisión. La
réplica eliminaba una etiqueta creada únicamente en GitHub y devolvía la release
a borrador. Se corrigió creando primero `server-v1.4.7` en Forgejo, sin mover su
commit. La repetición oficial selectiva de instalación raíz y actualización
terminó correctamente en 9 minutos y 23 segundos. En conjunto quedaron correctas
las ocho operaciones, incluida la migración desde `1.4.7~ynh1`; se conservan
ambos informes originales, incluido el fallo anterior.

La actualización aislada conservó los datos SQLite de prueba, clave maestra,
credenciales y secreto de proxy, con permisos privados. Una segunda prueba
comparó la configuración, servicios, plantillas y autenticación persistidos y
descifró correctamente una clave API ficticia sembrada antes de actualizar.
La sesión SSO administradora respondió 200; SSOwat redirigió al SSO (302) los
accesos sin sesión y la API del motor rechazó con 403 tanto las peticiones
anónimas como las cabeceras de identidad falsificadas por loopback.
Los 13 archivos de ejecución y configuración del paquete final
coinciden por SHA-256 con los probados. Los 54 contratos Python terminaron
correctamente con un pico de unos 106 MiB. El exportador de fuentes evita
recorrer compilaciones, máquinas virtuales y dependencias antes de filtrarlas.

El 13 de noviembre de 2026, `package_check` completó las siete comprobaciones
en 28 minutos y 36 segundos sobre YunoHost 12.1.41.2, amd64: linter,
instalación raíz, subruta, multiinstancia, copia/restauración, actualización
desde la misma versión y cambio de URL. Se corrigió también la recuperación
de permisos privados de `startup.json` tras restaurar. Las sumas de los 950
archivos de ejecución, configuración y payload se comparan con la entrega.
Esto no acredita una ejecución en arm64 ni una actualización desde cada
versión anterior.

El resultado global local del comprobador es `0 (Broken)`: el linter marca
`AppCatalog.is_in_catalog` como crítico y `AppCatalog.state_is_working` como
error al no existir una entrada oficial. El aviso
`AppCatalog.has_category` tiene la misma causa. Se conservan esos resultados
sin alterar el catálogo para obtener una calificación. Las siete pruebas
correctas y estos avisos se presentan por separado como evidencias del mantenimiento independiente.

El manual se compila en modo estricto y se revisan sus enlaces locales. Las dos
webs de GitHub Pages se publican desde las mismas fuentes. Una compilación del
manual no acredita por sí sola que la publicación remota haya terminado.

## Límites de la entrega

Las compilaciones cruzadas de Windows y macOS verifican que el código compila;
no sustituyen una prueba de escritorio en esos sistemas. Home Assistant OS y
los equipos reales requieren su aceptación específica. Las pruebas se hacen
sin actualizar ni reinstalar el YunoHost personal. La revisión oficial del
catálogo y la aprobación de las tiendas pertenecen a sus respectivos equipos.

## Repetir la comprobación

Desde la raíz del proyecto:

```bash
bash tools/verify.sh
builds/docs-env/bin/python -m mkdocs build --strict
python3 tools/check_manual.py builds/manual
sha256sum --check --quiet CONTENIDO.sha256
```

Prepara el entorno documental según [MANUAL_WEB.md](MANUAL_WEB.md). La suma
corresponde al contenido entregado; cambiar un archivo hace necesario actualizarla.
Consulta [CONTRIBUTING.md](../CONTRIBUTING.md) antes de preparar un commit.

## Comprobar una exportación

El archivo externo `.zip.sha256` verifica el ZIP. Dentro, `CONTENIDO.sha256`
contiene la suma de cada archivo entregado. Compruébalo desde la carpeta
extraída antes de modificarla. El exportador incluye fuentes nativas, manuales,
capturas, herramientas del manual y paquetes instalables. Excluye historial
Git, cachés, credenciales, SQLite y perfiles de ejecución.

La [guía de Git y entregas](MIGRACION_REPOSITORIO.md) explica cómo generar una
exportación y revisarla. Los paquetes de ejecutables incluyen también los
recursos de las guías, como las capturas, conservando sus subdirectorios.
