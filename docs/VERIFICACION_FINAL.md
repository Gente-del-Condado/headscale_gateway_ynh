# Validación y límites conocidos

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
