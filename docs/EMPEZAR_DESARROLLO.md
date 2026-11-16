# Empezar a desarrollar

Esta guía permite preparar un entorno y hacer un primer cambio sin conocer
el historial del proyecto. No necesitas acceso a servidores, tokens ni una
clave de firma para ejecutar las pruebas generales.

## Qué vas a modificar

Headscale coordina los nodos VPN. Gateway ejecuta un nodo, publica servicios
HTTPS y ofrece el panel administrativo. El motor está en `src/`, el panel común
en `src/internal/admin/` y las adaptaciones de instalación en `packaging/`.
La [tabla de fuentes](ESTRUCTURA.md) indica dónde editar cada componente.

No confundas la aplicación Home Assistant, que ejecuta el servidor, con su
integración, que consulta siete entidades. El paquete YunoHost tampoco instala
Headscale: necesita un coordinador existente. La nueva gestión del coordinador
requiere registrar expresamente un controlador; consulta [su guía](CONTROL_HEADSCALE.md).

## Requisitos

| Trabajo | Herramientas |
| --- | --- |
| Motor y pruebas generales | Git, Go de `src/go.mod`, Python 3.11 o posterior, Node.js 22 |
| Manual | Entorno Python con `requirements-docs.txt` |
| Bandeja | Node.js y dependencias de `src/desktop/package-lock.json` |
| Android | JDK 17, Gradle 8.13, SDK API 36 y NDK declarados en `android/build.gradle` |
| Contenedores y VM | Solo para la aceptación específica de esa plataforma |

Los gestores descargan dependencias la primera vez. Mantén sus cachés fuera de
las fuentes. En un equipo limitado, utiliza `GOMAXPROCS=2`, `GOFLAGS=-p=2` y,
si lo necesitas, `GOMEMLIMIT=2GiB`; no cambies los recursos de una VM sin acordarlo.

## Primer recorrido: comprobar sin instalar

Desde la raíz del clon:

```sh
git status --short
git log -1 --oneline
python3 -B tools/check_repository.py
python3 -B tools/check_privacy.py
GOMAXPROCS=2 GOFLAGS=-p=2 go -C src test ./internal/headscalecontrol ./internal/admin
```

Las pruebas usan datos ficticios y carpetas temporales. Para comprobar el
repositorio completo, ejecuta `GOMAXPROCS=2 GOFLAGS=-p=2 bash tools/verify.sh`.
Consulta [PRUEBAS.md](PRUEBAS.md) si una comprobación necesita herramientas adicionales.

## Abrir un panel de desarrollo aislado

Estos comandos son para Linux. Utilizan otro directorio de datos y una cuenta
propia, sin acceder a la SQLite de una aplicación instalada. La contraseña se
introduce de forma oculta en la terminal:

```sh
mkdir -p builds/dev
GOMAXPROCS=2 GOFLAGS=-p=2 go -C src build -o ../builds/dev/headscale-gateway .
HGW_DEV_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/headscale-gateway-dev"
python3 tools/configure.py \
  --data-dir "$HGW_DEV_ROOT/data" \
  --config-dir "$HGW_DEV_ROOT/config" \
  --listen 127.0.0.1:19091 \
  --admin desarrollo
GATEWAY_BOOTSTRAP_FILE="$HGW_DEV_ROOT/config/startup.json" \
  builds/dev/headscale-gateway --db "$HGW_DEV_ROOT/data/gateway/gateway.sqlite"
```

Abre `http://127.0.0.1:19091/admin/`. El usuario es `desarrollo` y la contraseña
es la elegida en el comando anterior. Detén el proceso con Ctrl+C. No hace falta
conectar una VPN para trabajar en partes del panel o ejecutar las pruebas.
Si configuras una Tailnet, crea una identidad y credenciales exclusivas del laboratorio.

Un segundo proceso no puede utilizar esa misma base ni su identidad VPN. Para
otra instalación, elige otra carpeta y otro puerto. No guardes los datos de
este ejemplo dentro del repositorio.

## Hacer un primer cambio

1. Crea una rama desde `main` y empieza por un cambio pequeño: texto, enlace o
   una validación cubierta por una prueba.
2. Edita la fuente, no su copia generada. Para YunoHost y la aplicación HA,
   utiliza `packaging/`. Para las entidades, `custom_components/`.
3. Actualiza la guía que describe ese comportamiento en la misma modificación.
4. Ejecuta las comprobaciones del componente; si cambias mensajes o rutas,
   regenera referencia e i18n. Regenera los paquetes cuando corresponda.
5. Revisa `git diff`, la auditoría de privacidad y los archivos preparados.
   [CONTRIBUTING.md](../CONTRIBUTING.md) explica el commit y sus sumas.

## Encontrar una respuesta

| Necesidad | Documento |
| --- | --- |
| Qué archivo editar | [Estructura](ESTRUCTURA.md) |
| Cómo interactúan las piezas | [Arquitectura](ARQUITECTURA.md) |
| Contratos y trabajo con agentes | [AGENTS.md](../AGENTS.md) |
| Situación de la próxima entrega | [Estado de desarrollo](ESTADO_DESARROLLO.md) |
| Reproducir las comprobaciones | [Pruebas](PRUEBAS.md) |
| No publicar datos privados | [Privacidad del repositorio](SEGURIDAD.md) |
| Generar el sitio de documentación | [Manual web](MANUAL_WEB.md) |
| Flujo entre repositorios | [Publicación](PUBLICACION.md) |
