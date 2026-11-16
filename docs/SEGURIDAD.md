# Privacidad del repositorio y limpieza local

El repositorio contiene código, ejemplos ficticios, licencias y paquetes
instalables generados. Los principales de Forgejo y GitHub son privados; los
paquetes, las tiendas, los fuentes exportados y los manuales son públicos.
Que un archivo esté en el principal privado no autoriza a incluirlo en una entrega.

## Dónde guardar cada cosa

| Contenido | Ubicación |
| --- | --- |
| Compilaciones reproducibles e informes sin secretos | `builds/`, `bin/` o una carpeta temporal |
| Datos de una instalación de desarrollo | Directorio privado fuera del clon |
| SQLite, `master.key`, identidad tsnet y CA privadas | Directorio de datos de su instalación |
| Firma Android y sus contraseñas | Almacén privado externo al proyecto |
| Tokens de publicación | Secretos cifrados de Actions en el repositorio compilador |
| Entregas antiguas y sus fuentes de terceros | Archivo externo protegido o release correspondiente |

Nunca incluyas claves SSH, tokens, cookies, contraseñas, exportaciones de perfiles,
copias cifradas, volcados de entornos ni capturas con datos reales. No publiques
el historial privado en los repositorios de distribución. El exportador de
fuentes selecciona las carpetas permitidas y excluye estado, claves y cachés.

## Comprobar antes de un commit

```sh
python3 -B tools/check_privacy.py
git diff --cached --stat
git diff --cached --check
```

El comprobador no necesita servicios externos y no imprime los valores
sospechosos. Revisa también capturas y documentos: una comprobación de texto no
puede garantizar que una imagen carezca de datos privados.

Como segunda revisión, usa Gitleaks 8.30.1 o posterior desde su distribución
oficial, comprobando la suma de descarga. Guarda sus informes fuera del clon,
con permisos privados. Con `.gitleaks.toml` cargado desde la raíz:

```sh
gitleaks git . --log-opts=--all --redact
```

Esto examina las referencias locales del historial. Para revisar una carpeta
exportada, usa `gitleaks dir /ruta/de/la/exportacion --redact --config .gitleaks.toml`.
La excepción declarada corresponde únicamente a líneas SHA-256 de los dos
manifiestos generados; no excluye tests, dependencias ni todo el contenido JSON.
Los manifiestos se comprueban además contra sus fuentes y archivos reales.

Ningún escáner demuestra por sí solo ausencia absoluta de secretos. Si encuentra
una credencial real, retírala del árbol, revócala o rótala con su propietario y
revisa qué se llegó a publicar. No reescribas todo el historial ni muevas etiquetas
sin valorar las réplicas y las copias recuperables.

## Limpiar sin perder una instalación

1. Revisa `git status --short`, `git worktree list` y el contenido de cada carpeta.
2. Conserva las claves de firma y los originales que aún necesites para distribuir
   fuentes y avisos de terceros. Mantén los informes privados fuera del proyecto.
3. Detén solo los procesos de laboratorio identificados. Una carpeta en uso no
   se limpia mientras su proceso mantiene abierta la SQLite.
4. Retira worktrees limpios con `git worktree remove RUTA`; no borres su carpeta
   a mano. `git worktree prune` elimina únicamente registros que ya no existen.
5. Borra resultados reproducibles concretos, tras revisarlos. No uses `git clean
   -fdx` sobre todo el clon: también alcanza datos ignorados que no son cachés.

`yunohost/payload/` y `addons/headscale_gateway/source.tar.gz` son archivos
versionados necesarios para instalar desde el clon. No se eliminan como si
fueran resultados de `builds/`. `src/third_party/` contiene avisos legales,
no una caché de dependencias. Tampoco se elimina para ahorrar espacio.

El historial se conserva. `git gc` puede compactar objetos sin mover ramas o
etiquetas; no uses purgas inmediatas de objetos ni expiraciones forzadas para
hacer una limpieza ordinaria.
