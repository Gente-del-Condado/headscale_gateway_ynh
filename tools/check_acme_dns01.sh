#!/usr/bin/env bash
# CA y DNS de laboratorio: no utiliza tokens, dominios ni almacenes de producción.
set -euo pipefail
cd "$(dirname "$0")/.."
export GOMAXPROCS="${GOMAXPROCS:-2}" GOMEMLIMIT="${GOMEMLIMIT:-512MiB}" GOFLAGS="${GOFLAGS:--p=1}"
mkdir -p builds/acme-lab-tools builds/acme-lab-tmp
export TMPDIR="$PWD/builds/acme-lab-tmp"
# La versión explícita se construye fuera del módulo del producto; Pebble nunca
# forma parte de los paquetes ni modifica las dependencias del motor.
GOBIN="$PWD/builds/acme-lab-tools" go -C src install github.com/letsencrypt/pebble/v2/cmd/pebble@v2.10.3
HGW_PEBBLE_BIN="$PWD/builds/acme-lab-tools/pebble" CGO_ENABLED=0 \
    go -C src test -count=1 -timeout=150s -run '^TestTechnitiumACMELabIssueRenewAndCleanTXT$' -v .
