# Headscale Gateway

Gateway de servicios privados para redes Headscale. Ejecuta un nodo VPN,
publica servicios con HTTPS y permite gestionar DNS, certificados, acceso y
copias cifradas desde un panel en español. Comparte el motor entre Linux,
Windows, macOS, Home Assistant, YunoHost y Android.

## Repositorio principal y distribución

Este es **headscale_gateway**, el principal completo: motor Go, panel, bandeja,
Android, integración de Home Assistant e instaladores. Se desarrolla primero en
[Forgejo privado](https://gentedelcondado.es/forgejo/wolfbelmi88/headscale_gateway).
[GitHub privado](https://github.com/Gente-del-Condado/headscale_gateway) es su
espejo; los cambios y las solicitudes se tramitan en Forgejo.

El control de publicación de [headscale_gateway_releases](https://github.com/Gente-del-Condado/headscale_gateway_releases/actions)
consulta las releases estables de Forgejo y utiliza runners públicos estándar de
GitHub. Comprueba el commit etiquetado y solo publica tras superar seguridad,
pruebas de plataforma y compilación. El principal y su historial permanecen
privados. Los destinos son:

| Destino público de GitHub | Contenido |
| --- | --- |
| [headscale_gateway_releases](https://github.com/Gente-del-Condado/headscale_gateway_releases) | Descargas generales sin autenticación, fuentes correspondientes, escritorios ligeros, Debian y Fedora |
| [headscale_gateway_flatpak](https://github.com/Gente-del-Condado/headscale_gateway_flatpak) | Motor completo empaquetado para la sesión de usuario, fuera del catálogo Flathub |
| [headscale_gateway_ynh](https://github.com/Gente-del-Condado/headscale_gateway_ynh) | Paquete YunoHost: manifiesto, scripts, configuración y documentación; recursos del motor en releases |
| [headscale_gateway_ha](https://github.com/Gente-del-Condado/headscale_gateway_ha) | Integración de entidades; requiere un Gateway ya funcionando |
| [Mis_app_ha](https://github.com/Gente-del-Condado/Mis_app_ha) | Aplicación que ejecuta el Gateway en Home Assistant |
| [Mis_componente_ha](https://github.com/Gente-del-Condado/Mis_componente_ha) | Copia de la integración para el catálogo de Private Git Manager |

El mismo manual se publica en gh-pages de las dos distribuciones dedicadas.
Los publicadores no escriben en Forgejo ni publican desde pull requests. Las
reglas, permisos y recuperación están en [Publicación](docs/PUBLICACION.md).
Una release estable nueva en Forgejo se detecta en la consulta horaria del
control público y activa la compilación y publicación sin lanzar flujos a mano.

## Qué descargar

| Necesidad | Descarga |
| --- | --- |
| Gateway completo en PC | [Última release de Gateway](https://github.com/Gente-del-Condado/headscale_gateway_releases/releases/latest): DEB/RPM para Debian/Fedora, Flatpak o archivos del motor para Windows/Linux/macOS |
| Android | `headscale-gateway-release.apk` de esa release, con la firma estable; también en la [tienda F-Droid propia](https://github.com/Gente-del-Condado/Mis_app_fdroid) |
| Bandeja opcional | `gateway-tray-linux-x64.tar.gz` o `gateway-tray-windows-x64.zip`; requiere un Gateway en funcionamiento |
| Fuentes del proyecto | `headscale-gateway-fuentes-publicos-VERSION.zip` y `headscale-gateway-go-sources-VERSION.tar.gz` de la misma entrega |
| Fuentes de Electron y dependencias | Release `desktop-sources-electron-VERSION-HUELLA`, enlazada desde las notas y `legal/PUBLIC-SOURCES.json` de la bandeja |

Para instalar no necesitas descargar Chromium, Electron, Node ni NAN por
separado. Sus fuentes corresponden al runtime de la bandeja y se conservan
para reconstrucción y redistribución. El motor Go, Android, YunoHost, Home
Assistant y Flatpak no necesitan instalar esa bandeja. Comprueba el
`SHA256SUMS` de la release que contiene cada archivo. Los instaladores de la
bandeja se extraen directamente; solo los fuentes Chromium usan partes.

Las futuras entregas reutilizan el mismo conjunto mientras coincida el lock.
La 1.4.16 conserva sus adjuntos y enlaces originales por compatibilidad. Más
detalles en la [guía de descargas](packaging/releases/README.md) y en
[fuentes y licencias de escritorio](packaging/desktop/README.md).

## Leer el manual

Manual web público: [YunoHost](https://gente-del-condado.github.io/headscale_gateway_ynh/)
y [Home Assistant](https://gente-del-condado.github.io/headscale_gateway_ha/).
Ambas webs muestran el mismo manual, generado desde las fuentes del proyecto.

Empieza por el [manual del proyecto](docs/index.md) y los
[primeros pasos](docs/PRIMEROS_PASOS.md). Incluye ejemplos, capturas y solución
de problemas. Para generar la web con búsqueda y navegación desde estas
mismas fuentes, sigue [Manual web y GitHub Pages](docs/MANUAL_WEB.md).

| Quiero… | Guía |
| --- | --- |
| Instalar el complemento de Home Assistant | [Tienda Mis_app_ha](https://github.com/Gente-del-Condado/Mis_app_ha) · [Instalación, Ingress y copias](packaging/homeassistant/DOCS.md) |
| Ver el Gateway como entidades de Home Assistant | [Integración de entidades](packaging/hacs/README.md) |
| Instalar en YunoHost | [Instalación, SSO y actualización](packaging/yunohost/doc/ADMIN.md) |
| Ejecutar el servidor directamente | [Manual de uso](docs/USO_COMPLETO.md) |
| Utilizar Android | [Aplicación Android](android/README.md) |
| Publicar el primer servicio | [Ejemplos completos](docs/EJEMPLOS.md) |
| Recuperar el acceso | [Procedimiento de recuperación](docs/RECUPERAR_ACCESO.md) |
| Modificar el código o continuar con una IA | [Guía de continuidad](AGENTS.md) y [contribución](CONTRIBUTING.md) |

## Encontrar el portal y la administración

En **Resumen → Estado**, **Dominio principal** aparece primero y enlaza al
portal de servicios de este Gateway. La **URL administrativa** abre el panel;
**Servidor Headscale** corresponde al coordinador VPN. Las direcciones web
completas son enlaces y conservan su puerto y ruta. Se abren en otra pestaña
o en el navegador del dispositivo. Sin un dominio confirmado se muestra
**Pendiente de conexión**, sin crear un enlace ficticio.

El navegador necesita resolver ese DNS, alcanzar la red correspondiente y
confiar en su certificado. Ingress o el SSO de YunoHost permiten administrar
el Gateway, pero no dan por sí solos conectividad del navegador a la Tailnet.
En Android, activa **Conectar aplicaciones** cuando el destino lo requiera.

## Organización

```text
headscale-gateway/
├── src/                    Motor Go, panel, cliente de bandeja y pruebas
│   ├── internal/           API, SQLite, PKI, copias y componentes compartidos
│   ├── desktop/            Cliente Electron
│   ├── locale/             Traducciones editables
│   ├── tools/              Utilidades Go y laboratorios visuales
│   └── third_party/        Inventario y avisos legales
├── android/                Aplicación, JNI y fuentes HEV necesarias
├── packaging/              Fuentes de instaladores y sus manuales
├── addons/                 Complemento Home Assistant generado e instalable
├── custom_components/      Integración de entidades Home Assistant
├── yunohost/               Paquete generado con ejecutables amd64 y arm64
├── tools/                  Compilación, verificaciones, empaquetado y tema web
├── tests/                  Contratos Python e integración con plataformas
├── docs/                   Manual y capturas
├── examples/               Configuraciones ficticias
├── AGENTS.md               Reglas y mapa para continuar el trabajo
└── mkdocs.yml              Navegación y construcción del manual web
```

El [mapa de componentes](docs/ESTRUCTURA.md) distingue fuentes, contenidos
generados y datos de ejecución. `addons/` y `yunohost/` forman parte de Git para
permitir instalar desde un clon privado. Se generan desde `src/` y `packaging/`.
La plantilla Home Assistant es `config.yaml.in`, que se convierte en
`config.yaml` dentro del complemento instalable.

## Continuar el desarrollo

Empieza por [la guía para desarrolladores nuevos](docs/EMPEZAR_DESARROLLO.md).
Explica el entorno mínimo, las pruebas sin credenciales y un panel de laboratorio
con datos fuera del clon. El [estado de la siguiente entrega](docs/ESTADO_DESARROLLO.md)
indica qué está preparado, validado o pendiente; el [historial de cambios](CHANGELOG.md)
no sustituye la comprobación de las releases publicadas.

Los agentes de IA deben leer [AGENTS.md](AGENTS.md), respetar los contratos del
motor compartido y el alcance autorizado. [Privacidad y limpieza](docs/SEGURIDAD.md)
explica cómo evitar que datos de instalaciones entren en Git o en las distribuciones.

## Preparar el desarrollo

Requisitos comunes del motor y sus verificaciones:

- Go **1.27.4**, según `src/go.mod`.
- Python **3.11 o posterior** para herramientas y MkDocs.
- Node.js **22** para comprobar JavaScript y trabajar en el cliente Electron.
- Git y las herramientas del sistema que necesite la plataforma de destino.

Desde la raíz del proyecto:

```bash
go -C src run -buildvcs=false . --help
python3 tools/check_repository.py
bash tools/verify.sh
```

En Windows utiliza `powershell -File tools/verify.ps1`. El módulo Go vive en
`src/`. Las dependencias se fijan en los archivos de módulo y lock existentes.
El motor ejecutable funciona independientemente del entorno de Node.js.

## Compilar y generar instaladores

```bash
# Ejecutables en bin/, fuera de las fuentes versionadas.
python3 tools/build_release.py --targets linux-amd64 windows-amd64

# Complemento e instalador incluidos en Git.
python3 tools/prepare_git_install.py
python3 tools/prepare_git_install.py --check

# ZIP de fuentes, con manifiesto de integridad.
python3 tools/repository_archive.py --output releases/headscale-gateway-fuentes.zip
```

`VERSION` identifica la versión común del motor. Para cambiarla utiliza
`python3 tools/set_version.py X.Y.Z` y regenera los instaladores. Las etiquetas
Git identifican commits y se gestionan según [Git y entregas](docs/MIGRACION_REPOSITORIO.md).

Android requiere JDK 17, Gradle 8.13, SDK API 36 y NDK 27.0.12077973. Su
[guía](android/README.md) contiene los comandos, permisos y ubicación de la APK.
Los resultados de compilación se guardan en `bin/`, `builds/` o `releases/`.

## Mantener una instalación

Utiliza el procedimiento de la plataforma, realiza una copia comprobada y
conserva la ubicación de sus datos. La configuración reside en SQLite y cada
nodo mantiene su identidad VPN. Las guías incluyen actualización, recuperación
y diferencias entre copiar ajustes y restaurar una identidad completa.

Los resultados comprobados y los recorridos que requieren equipos reales están
en [validación y límites](docs/VERIFICACION_FINAL.md). El [plan de pruebas](docs/PRUEBAS.md)
explica cómo repetir las verificaciones.

## Licencia y distribución

El código propio se distribuye bajo **GNU AGPL versión 3 únicamente**
(`AGPL-3.0-only`), con el alcance indicado en [NOTICE](NOTICE) y los términos
completos de [LICENSE](LICENSE). Se permite el uso, modificación y distribución,
también comercial, respetando sus condiciones. Los
avisos de dependencias están en [NOTICE](NOTICE) y en los inventarios de terceros.
Consulta [licencias](docs/LICENCIAS.md) antes de preparar una distribución.

## Autor y soporte

Autor: **Gente del Condado**. Soporte: [headscale-gateway@gentedelcondado.es](mailto:headscale-gateway@gentedelcondado.es).
[Manual en línea](https://gente-del-condado.github.io/headscale_gateway_ynh/).

## Administración del coordinador Headscale

El motor y el panel comunes incorporan gestión local o delegada del coordinador:
DNS de la Tailnet, restricciones OIDC, registros dinámicos y observación de nodos.
Consulta [Control de Headscale](docs/CONTROL_HEADSCALE.md) para registrar el ayudante
local, delegar permisos y conocer sus límites. Todas las plataformas comparten la
interfaz; YunoHost añade su adaptación de instalación.

## Protecciones de la plataforma

Consulta las [protecciones y sus límites](docs/SEGURIDAD_PLATAFORMAS.md): aislamiento del servicio,
autorización del contenedor Android y permisos Flatpak. Las actualizaciones
conservan los datos y la identidad; no requieren desactivar protecciones del sistema.
