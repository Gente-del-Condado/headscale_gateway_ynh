# Plan de regresión y despliegue seguro

## Validación local antes de enviar a Forgejo

En Linux con systemd, ejecuta las comprobaciones en este equipo antes de subir
un candidato. Las tareas van en secuencia, con un límite conjunto de 3 GiB de
RAM, 512 MiB de intercambio y dos CPU. Los temporales se guardan en el disco de
`builds/`, no en `/tmp`. No se publica nada ni se usan bases de producción.

```bash
# Entorno con requirements-docs.txt instalado:
DOCS_PYTHON=/ruta/al/entorno/bin/python bash tools/preflight_local.sh --containers
```

El script comprueba motor, panel, conservación de credenciales e identidad,
emisión y renovación ACME DNS-01 con una CA y un DNS locales de laboratorio,
paquetes generados y manual. `--containers` añade el complemento Home Assistant
y el proxy nginx/SSO de YunoHost con Docker o Podman rootless. Conserva el informe
en `builds/preflight-*/results.log` y se detiene al primer fallo. Antes de
repetirlo tras cambiar fuentes, regenera los paquetes con
`python3 tools/prepare_git_install.py`.

La prueba del proxy YunoHost no sustituye la aceptación completa en una VM.
Android se comprueba además en la tablet con la misma firma y sin borrar datos;
el arranque real del servicio Windows se comprueba en un runner Windows
o en una VM de laboratorio con `tools/check_windows_service.ps1 -LocalLab`.
La prueba local necesita PowerShell como administrador y un paquete Windows
compilado de las mismas fuentes. Crea su propio servicio y directorios con
nombres únicos; no sustituye una instalación existente y los retira al terminar.
GitHub mantiene las comprobaciones y la publicación de los destinos públicos.

## Automatizadas

```bash
./tools/verify.sh       # Linux/macOS: go -C src test, vet, build, JS y HTML
# o en PowerShell:
.\tools\verify.ps1
```

Comprobación del bloque de recuperación en un proceso aislado Linux/macOS:

```bash
python3 tools/check_console.py
```

Pruebas del módulo comercial opcional, sin generar claves reales:

```bash
CGO_ENABLED=0 go -C src test -tags commercial ./internal/licensing
CGO_ENABLED=0 go -C src test -tags commercial . -run '^TestCommercial'
```

Los resultados de esta revisión y los límites de lo probado están en [VERIFICACION_FINAL.md](VERIFICACION_FINAL.md). Las comprobaciones usan instancias temporales y no necesitan claves de producción.

## Manuales obligatorias antes de desplegar

1. **Primer arranque** en una instalación de prueba nueva (Windows/Fedora),
   permisos de datos y firewall, panel solo loopback.
2. **Migración** con una copia consistente de `gateway.sqlite` y `master.key`;
   confirmar que los tokens/OIDC, sesiones y plantillas permanecen intactos.
3. **Proxy y DNS**: HTTPS LAN y tailnet, servicios, cambios de IP, certificados
   CA local y ACME, limpieza DNS sin tocar registros externos.
4. **API**: revisar usuarios viewer/operator/admin, CSRF, tokens delegados y
   endpoints de Headscale; comprobar también los errores 401/403/404.
5. **PKI**: peer no autorizado, huella diferente, revocación y rechazo de CA.
6. **Backup**: exportación/importación `.hgw`, contraseña equivocada, archivos
   manipulados y restauración completa en equipo de laboratorio.
7. **Windows**: ejecutar, reiniciar desde el panel y repetir como servicio;
   comprobar que no quedan dos procesos con el mismo SQLite abierto.
8. **Logs**: rotación de 3 canales, DEBUG temporal, redacción de secretos y CLI.

La comprobación real del producto exige todas estas pruebas. **No probar
restauraciones destructivas ni políticas ACL de bloqueo sobre la red de
producción** como primer ensayo.

## Certificados ACME DNS-01 y Technitium

`bash tools/check_acme_dns01.sh` construye Pebble 2.10.3 como herramienta de
laboratorio y comprueba la emisión y renovación de un nodo y su wildcard.
Utiliza el configurador DNS-01 real del Gateway, el proveedor Technitium MIT,
una API Technitium simulada y un DNS autoritativo en loopback. Pebble valida los
TXT realmente; no se omite su validación. Se comprueban la cadena TLS, los
nombres, el cambio de certificado al renovar, la conservación de la cuenta
ACME y la retirada exclusiva de los TXT del desafío, conservando un TXT manual antiguo.
También se comprueba que una cuenta nueva exige aceptación explícita sin consola y que una cuenta guardada puede renovar sin la opción nueva.
La CA de ensayo solo se confía dentro del cliente de prueba. Las claves y el
almacén se generan en una carpeta temporal; no se utiliza el proveedor real.
Pebble se fija por versión y no se distribuye con el producto. La primera
preparación de la herramienta requiere acceso a los módulos Go; las peticiones
ACME y DNS del ensayo son locales.
