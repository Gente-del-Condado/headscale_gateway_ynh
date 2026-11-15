#!/usr/bin/env bash
# Validación previa al envío. No publica ni usa datos de instalaciones reales.
set -euo pipefail
cd "$(dirname "$0")/.."
containers=false
inside=false
for option in "$@"; do
    case "$option" in
        --containers) containers=true ;;
        --inside-scope) inside=true ;;
        --help) echo 'Uso: bash tools/preflight_local.sh [--containers]'; echo 'DOCS_PYTHON selecciona el Python con requirements-docs.txt instalado.'; exit 0 ;;
        *) echo "Opción desconocida: $option" >&2; exit 2 ;;
    esac
done
# El cgroup limita el conjunto de hijos, además de limitar la concurrencia Go.
# No se configura ningún servicio permanente ni se modifica el equipo.
if ! "$inside"; then
    if ! systemctl --user show-environment >/dev/null 2>&1; then
        echo 'Se necesita una sesión systemd de usuario para aplicar límites de recursos.' >&2
        exit 1
    fi
    exec systemd-run --user --scope --quiet --collect \
        --property=MemoryMax=3G --property=MemorySwapMax=512M --property=CPUQuota=200% \
        bash "$PWD/tools/preflight_local.sh" --inside-scope "$@"
fi
export GOMAXPROCS=2 GOMEMLIMIT=512MiB GOFLAGS=-p=1 CGO_ENABLED=0 PYTHONDONTWRITEBYTECODE=1
# Evita llenar /tmp cuando está montado en RAM.
mkdir -p builds
run_dir=$(mktemp -d "$PWD/builds/preflight-XXXXXXXX")
export TMPDIR="$run_dir/tmp"
mkdir -p "$TMPDIR"
chmod 700 "$run_dir" "$TMPDIR"
exec 9>"$PWD/builds/.preflight.lock"
flock -n 9 || { echo 'Ya hay una validación local en curso.' >&2; exit 1; }
log="$run_dir/results.log"
exec > >(tee "$log") 2>&1
trap 'code=$?; printf "RESULTADO=%s\nInforme: %s\n" "$code" "$log"' EXIT
printf 'Commit de partida: '; git rev-parse HEAD
printf 'Versión: '; cat VERSION
# Comprueba primero los generados; si están obsoletos pide regenerarlos.
bash tools/verify.sh
(cd src && go run golang.org/x/vuln/cmd/govulncheck@v1.9.0 -scan module && go run golang.org/x/vuln/cmd/govulncheck@v1.9.0 ./...)
(cd src/desktop && npm audit --include=dev --audit-level=low)
python3 -B tools/check_deployment.py
bash tools/check_acme_dns01.sh
"${DOCS_PYTHON:-python3}" -m mkdocs build --strict --site-dir "$run_dir/manual"
python3 -B tools/check_manual.py "$run_dir/manual"
if "$containers"; then
    # Podman rootless evita requerir acceso al daemon del sistema.
    if command -v podman >/dev/null; then runtime=podman; else runtime=docker; fi
    image="hgw-preflight-$$"
    trap 'code=$?; "$runtime" network rm "$image-net" >/dev/null 2>&1 || true; "$runtime" image rm "$image-ha" "$image-ynh" >/dev/null 2>&1 || true; printf "RESULTADO=%s\nInforme: %s\n" "$code" "$log"' EXIT
    "$runtime" build --build-arg BUILD_VERSION="$(cat VERSION)" --build-arg BUILD_ARCH=amd64 --memory 2g --cpu-period 100000 --cpu-quota 200000 -t "$image-ha" addons/headscale_gateway
    "$runtime" network create --subnet 172.30.32.0/24 "$image-net"
    "$runtime" run --rm --network "$image-net" --ip 172.30.32.2 --add-host supervisor:127.0.0.1 --cpus 2 --memory 2g -v "$PWD/tools/check_container.py:/check.py:ro,Z" -v "$PWD/addons/headscale_gateway/config.yaml:/addon-config.yaml:ro,Z" --entrypoint python3 "$image-ha" /check.py
    "$runtime" build --memory 2g --cpu-period 100000 --cpu-quota 200000 -f tests/containers/yunohost-sso.Dockerfile -t "$image-ynh" yunohost
    "$runtime" run --rm --cpus 2 --memory 1g -v "$PWD/tools/check_yunohost_sso.py:/check_yunohost_sso.py:ro,Z" "$image-ynh"
fi
printf 'VALIDACION_LOCAL_OK\nWindows SCM y la tablet requieren sus pruebas de dispositivo independientes.\n'
