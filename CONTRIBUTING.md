# Desarrollar Headscale Gateway

El motor Go, el panel, SQLite, la identidad VPN y los formatos de copia son
comunes a todas las plataformas. Android y los instaladores adaptan el entorno;
no mantienen otra implementación del servidor. El código propio es
`AGPL-3.0-only`: conserva licencias, avisos y procedencia de terceros.

## Primera contribución

Sigue [Empezar a desarrollar](docs/EMPEZAR_DESARROLLO.md): explica requisitos,
una instalación de desarrollo aislada y un primer cambio pequeño. Después lee
[el mapa de fuentes](docs/ESTRUCTURA.md), [la arquitectura](docs/ARQUITECTURA.md)
y la guía del componente que vas a modificar. [AGENTS.md](AGENTS.md) establece
los contratos técnicos para personas y agentes de IA.

```sh
git status --short
git log -1 --oneline
python3 -B tools/check_repository.py
python3 -B tools/check_privacy.py
```

Trabaja en una rama `codex/descripcion-del-cambio` creada desde el `main` vigente.
Revisa antes los cambios de otras personas. No sobrescribas su trabajo ni
reescribas etiquetas o commits publicados para limpiar archivos locales.

## Editar, comprobar y documentar

1. Localiza la fuente en [ESTRUCTURA.md](docs/ESTRUCTURA.md). `addons/` y
   `yunohost/` se generan: no se editan directamente.
2. Lee el recorrido normal y sus pruebas. Añade una prueba del fallo o del
   comportamiento nuevo cuando cambie la lógica.
3. Modifica las fuentes, los comentarios útiles en español y su documentación.
   Conserva identificadores públicos y avisos de terceros.
4. Si cambian rutas o mensajes, genera y comprueba los catálogos:

```sh
python3 -B tools/reference_catalog.py
python3 -B tools/extract_i18n.py
python3 -B tools/check_i18n.py
```

La extracción escribe archivos; la comprobación de i18n es de solo lectura.
Si cambian el motor, la versión o las plantillas, regenera los instaladores:

```sh
python3 -B tools/prepare_git_install.py
python3 -B tools/prepare_git_install.py --check
GOMAXPROCS=2 GOFLAGS=-p=2 bash tools/verify.sh
```

La guía de [pruebas](docs/PRUEBAS.md) describe las comprobaciones de cada
plataforma. Compilar para Windows no equivale a ejecutar sus pruebas allí;
una prueba de contenedor no equivale a una aceptación en VM. No uses los datos
ni las claves de una instalación real para que una prueba pase.

Para cambios del manual, sigue [MANUAL_WEB.md](docs/MANUAL_WEB.md), compila
con `--strict` y comprueba los enlaces HTML. No hace falta arrancar VMs para
corregir un texto. El [estado de la entrega](docs/ESTADO_DESARROLLO.md) separa
las comprobaciones actuales de las históricas y de las pendientes.

## Preparar un commit y una versión

`python3 tools/set_version.py X.Y.Z` actualiza la versión común. Después
regenera los instaladores y comprueba que no quedan referencias funcionales a
la versión anterior. Las notas históricas y etiquetas conservan sus números.

Prepara solo los archivos revisados. Las sumas se calculan después de añadir
los archivos nuevos y las eliminaciones al índice:

```sh
git add --all
git diff --cached --stat
python3 -B tools/check_privacy.py
git ls-files -z -- . ':(exclude)CONTENIDO.sha256' | xargs -0 sha256sum > CONTENIDO.sha256
git add CONTENIDO.sha256
sha256sum --check --quiet CONTENIDO.sha256
git diff --cached --check
git commit -m "Describir el cambio y su finalidad"
```

No incluyas `builds/`, cachés, claves, bases, perfiles, diagnósticos privados ni
contraseñas. [SEGURIDAD.md](docs/SEGURIDAD.md) explica la auditoría y la limpieza.
El archivo `.gitignore` no protege un secreto que ya estuviera versionado.

## Publicar cuando esté autorizado

[PUBLICACION.md](docs/PUBLICACION.md) describe el único recorrido vigente:
**Forgejo principal privado → espejo privado GitHub → compilador público
`headscale_gateway_releases` → paquetes, tiendas, descargas y manuales**.
No se publica desde un pull request ni se escribe desde GitHub hacia Forgejo.

Una release estable de Forgejo, con etiqueta y `VERSION` coincidentes, habilita
la detección. Un push a `main` por sí solo no publica una entrega. La CI pública
debe superar todas sus comprobaciones antes de distribuir archivos. Los
workflows del compilador se mantienen en `packaging/releases/`; los de la raíz
son comprobaciones del espejo, no otro publicador. La cuota privada de GitHub
puede impedir esas comprobaciones sin impedir que arranque el compilador público.

Sube por SSH solo dentro del alcance autorizado. `main` está protegido: utiliza
una solicitud de fusión en Forgejo y verifica el commit remoto después. Si el
usuario pide preparar sin subir, termina con el commit local y las pruebas;
no crees etiquetas, releases ni cambios en los repositorios derivados.
