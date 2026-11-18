# Validación y límites

## Preparación de 1.4.19

- Suite completa: 102 pruebas Python, Go, JavaScript, vet y compilación.
- Tablet física Android 8.1/arm64: rechazo de origen falsificado y capacidad
  caducada, cancelación de transferencia al navegar, exportación blob y API
  con nombre y bytes conservados mediante ContentResolver. No utiliza Waydroid.
- Motores Android arm64 y x86_64 compilados; Lint release correcto y APK arm64
  firmada con la identidad estable existente. No equivale a ejecutar Android x86.
- systemd 252 en YunoHost/Debian 12: comprobaciones negativas de capacidades,
  namespaces, memoria W^X y escritura; positivas de SQLite WAL, TLS, NSS y red.
  Doce pruebas Go de certificados, DNS y restauración ejecutadas bajo cada unidad;
  el laboratorio ACME externo se omite explícitamente.
- Fedora con SELinux activo: mismas pruebas en una unidad temporal de usuario
  con `PrivateUsers`, sin instalar un servicio de sistema ni política SELinux.
- Flatpak de laboratorio instalado: permiso efectivo de red únicamente, datos
  privados conservados, claves SSH del anfitrión inaccesibles y mismas pruebas Go.
- DEB y RPM: construcción, instalación, reinstalación y conservación tras retirar
  el programa, en contenedores desechables. No equivale a un arranque nativo RPM.
- Actualización real YunoHost 1.4.18 → 1.4.19 con kernel 6.1.0-54: SSO,
  configuración, servicios, clave maestra, secreto del proxy, copia cifrada,
  PKI, descubrimiento y exportación conservados. Dependencias previamente
  instaladas y recursos locales con sumas originales; APT exterior inaccesible.
  El primer intento bajo 6.1.0-55 se bloqueó en ext4 antes de aplicar la revisión;
  no se presenta como una prueba completada ni una garantía ante fallos del disco.
- Manual estricto: 51 páginas y 3.296 enlaces locales; privacidad e i18n correctas.

Los resultados de actualización YunoHost y publicación se anotan en
[estado de desarrollo](ESTADO_DESARROLLO.md). Estos ensayos no acreditan una
emisión ACME pública ni una nueva conexión VPN con un proveedor de producción.
Play Store permanece solo preparado.

## Preparación de 1.4.17

Comprobaciones locales completadas: `tools/verify.sh` (100 pruebas Python,
Go, JavaScript, vet y compilación), 9 pruebas del controlador, generados y
versiones coherentes, privacidad y manual estricto (50 páginas, 3167 enlaces).
La consulta anónima confirmó el conjunto Electron existente con el mismo lock,
sin subidas. Las compilaciones nativas y la publicación final se verifican en
el flujo público; estos controles locales no equivalen a una nueva prueba en VM.
Play Store permanece solo preparado.

## Revisión 1.4.16 publicada

La revisión actual limpia resultados locales y documentación, añade controles
de privacidad y corrige el contrato de rutas del controlador Headscale en
Windows. Fue publicada y el flujo completo de GitHub terminó correctamente,
con pruebas y compilación Windows nativa, 45 descargas anónimas verificadas y
los seis destinos y ambas webs Pages comprobados. El estado y lo pendiente se
mantienen en [ESTADO_DESARROLLO.md](ESTADO_DESARROLLO.md).

### Fallo Windows reproducido y corregido

El [trabajo Windows de 1.4.15](https://github.com/Gente-del-Condado/headscale_gateway_releases/actions/runs/43784256540/job/133056107526)
falló en `TestControllerBindingRejectsCredentialedOrUnencryptedRemoteOrigins`.
`filepath.Join` aplicaba separadores Windows a rutas que pertenecen al actuador
Linux; la validación rechazaba un contrato válido antes de comprobar su origen.

Se utiliza ahora `path` para ese contrato POSIX y se rechazan rutas Windows,
relativas, no canónicas y caracteres de control. No se omite la prueba en Windows
ni se retiran las comprobaciones de permisos, identidad o TLS.

Se compiló el ejecutable de pruebas Windows anterior y se reprodujo el mismo
fallo bajo Wine. El ejecutable corregido pasa la suite del controlador en ese
entorno. Esto es una ejecución de binario Windows bajo Wine, **no** una aceptación
nativa en la VM ni una prueba del SCM. La VM Windows no respondió al acceso SSH;
no se modificaron sus recursos ni se reanudó la aceptación detenida.

### Comprobaciones del mantenimiento

Comprobaciones locales de esta revisión:

- Verificación general Go, JavaScript y Python, vet y compilación del motor.
- Pruebas del lector/publicador público y de los contratos de paquetes.
- Auditorías Go a nivel de módulos y de llamadas: sin vulnerabilidades detectadas.
  Auditoría npm, incluidas dependencias de desarrollo: cero vulnerabilidades.
- Manual estricto: 50 páginas HTML y 3.160 enlaces locales comprobados.
- Binario Windows del motor compilado y suite Windows del controlador ejecutada
  bajo Wine, con fallo reproducido antes de la corrección y éxito después.
- Estructura y versión común 1.4.16, instaladores regenerados y exportación de
  fuentes revisada; auditoría de privacidad y Gitleaks sin secretos detectados.
- OCR de las cuatro capturas del manual: sin coincidencias de credenciales o de
  los identificadores del laboratorio buscados. No sustituye toda revisión visual.

Los comandos se mantienen en [CONTRIBUTING.md](../CONTRIBUTING.md) y
[SEGURIDAD.md](SEGURIDAD.md). Estas comprobaciones no atribuyen por anticipado
el éxito de una nueva CI remota ni una aceptación física en todas las plataformas.

La auditoría Gitleaks del historial local examinó 92 commits. Sus 683 coincidencias
iniciales correspondían exclusivamente a líneas SHA-256 de dos manifiestos;
se contrastaron con los archivos originales de cada commit. La regla específica
para esas líneas no excluye el resto del JSON. Tras esa clasificación no se
detectaron credenciales. Se revisan además las fuentes y la exportación preparada;
una auditoría no garantiza ausencia absoluta de datos privados.

## Evidencia anterior que se conserva como referencia

| Revisión | Qué se comprobó | Límite |
| --- | --- | --- |
| 1.4.15 | Motor, panel, DNS y restricciones OIDC; observación y delegación TLS entre dos Gateway; actualización y restauración real YunoHost conservando datos, secretos, CA e identidad; compilación Windows/Android y RPM | La CI Windows falló después por el contrato de rutas; la distribución completa quedó bloqueada |
| 1.4.14 | Enlaces y dominio principal; aceptación local en Windows, Fedora, YunoHost, Home Assistant y tablet; compilación y publicación públicas completadas | No demuestra una aceptación nueva de esas plataformas para 1.4.16 |
| 1.4.13 | Servicio Windows y recuperación, conservación de datos, emisión y renovación DNS-01 con CA/DNS aislados, TXT ajenos preservados | No se atribuye coexistencia con Tailscale activo si estaba detenido |
| 1.4.7~ynh2 | Linter y laboratorio YunoHost, migración, actualización, restauración, SSO y permisos | Es evidencia histórica; no un nivel de catálogo oficial ni una nueva prueba arm64 |

Los resultados y límites originales permanecen en los commits y notas de sus
versiones. Los informes locales completos se guardan fuera del árbol del
proyecto si contienen direcciones, identidades o credenciales del laboratorio.

## Pruebas interrumpidas y funciones pendientes

Después de la validación de 1.4.15, se instaló la APK directa en la tablet y se
inició otra instalación limpia del laboratorio. El usuario detuvo esa prueba.
Dex y Headscale quedaron instalados en la VM; no se completaron la instalación
del nuevo Gateway, Technitium, la configuración Dex adicional ni la aceptación
conjunta de todas las funciones desde la tablet. No se presentan como realizadas.

**Play Store sigue solo preparado.** La distribución Flatpak directa no significa
aceptación en Flathub. El paquete YunoHost se mantiene para instalar desde su
repositorio; no se solicitará su inclusión en el catálogo oficial.

## Ensayo de la siguiente publicación sin crear una versión

El mantenimiento posterior comprueba el reparto real de adjuntos de una entrega
ficticia 1.4.17 entre las cuatro distribuciones, con datos mínimos y operaciones
de subida sustituidas por capturas de sus argumentos. Ninguna recibe los fuentes
de Electron. Se comprueba también que una release de dependencias coincidente
solo se consulte y que archivos distintos bloqueen la reutilización.

La comprobación local de la release pública Electron 45.0.0 contrasta el lock,
los índices, las sumas y los digest de sus diez adjuntos sin credenciales ni
subidas. La suite general pasa con 100 pruebas Python, además de Go/JS; las
nueve pruebas del controlador también pasan. No se presenta este ensayo como
una compilación real o una publicación de Headscale Gateway 1.4.17.

## AppArmor de Home Assistant — 18 de noviembre de 2026

Ensayo desechable en Home Assistant OS 18.4, amd64, con la imagen publicada
1.4.17 y una capa que únicamente añade `PYTHONDONTWRITEBYTECODE=1`, igual
que el Dockerfile actualizado. Supervisor instaló el perfil personalizado y
mostró 7/8, protección activa y proceso en enforce. No se tocaron la aplicación
existente, sus datos ni los recursos de la VM.

Comprobador repetible: `tools/check_ha_apparmor.py`, explicado en la documentación
del paquete. Pasaron SSO Ingress desde el origen Supervisor, CSRF, rechazo de
no administradores, panel y recurso JS, PKI, descubrimiento, copia cifrada SQLite
y descarga y exportación cifrada. Dentro del confinamiento pasaron SQLite WAL,
temporales, resolver DNS y apertura multicast; se bloquearon lectura de shadow,
escritura sobre programas y ejecución de shell. El reinicio conservó por suma
la clave maestra y las opciones de la copia de laboratorio.

Un binario de pruebas Go, ejecutado como motor en un contenedor temporal con
el mismo perfil, pasó 14 pruebas principales: TLS local real y renovación,
propiedad y limpieza DNS, restauración con conservación del directorio de la
plataforma, perfiles e identidad VPN. Son pruebas con fixtures; no equivalen
a conectar una Tailnet externa o emitir ACME contra un proveedor real. El ensayo
aarch64 posterior se recoge a continuación. Las denegaciones auditadas intencionales
se distinguen de las de arranque, corregidas sin ampliar acceso a programas.

La verificación general `GOMAXPROCS=2 GOFLAGS=-p=2 bash tools/verify.sh` pasó:
101 pruebas Python, suites Go y JavaScript, vet, compilación, privacidad,
referencia/i18n y manifiesto de instaladores. MkDocs estricto y el comprobador
HTML pasaron con 50 páginas y 3174 enlaces locales. La copia aislada y su imagen
de ensayo se retiraron al terminar; la aplicación habitual conserva su versión,
perfil genérico, datos y estado detenido anteriores. El cambio queda preparado
en fuentes, sin publicar una revisión de los paquetes ya distribuidos.

## AppArmor aarch64 en HAOS emulado — 18 de noviembre de 2026

VM nueva HAOS 18.4 sobre QEMU/TCG, CPU ARM cortex-a72, 2 vCPU y 4 GiB,
con Supervisor 2026.11.0. El kernel confirmó aarch64 y la imagen del Gateway,
arm64. Esta es ejecución del sistema ARM64 completo bajo emulación, no una
prueba sobre hardware ARM físico ni solo una compilación cruzada.

Supervisor cargó el mismo perfil en enforce con protección activa y puntuación
7/8. Pasaron las 14 pruebas principales Go del ensayo amd64, ejecutadas dentro
del perfil: TLS real local y renovación, DNS y propiedad de registros,
restauración, perfiles e identidad. El comprobador de confinamiento pasó SQLite
WAL, temporales, resolver y multicast y bloqueó shadow, escritura sobre programas
y shell. El comprobador del panel pasó Ingress/SSO/CSRF, rechazo no-admin,
PKI, descubrimiento, copia cifrada SQLite, descarga y exportación cifrada.

El reinicio del complemento conservó por suma la clave maestra, la clave de
cifrado de copias y las opciones. Solo aparecieron las tres denegaciones
intencionales de las pruebas negativas. Los datos ficticios se retiraron y se
instaló una copia local limpia con el mismo perfil y arranque automático.
No se modificó ninguna VM existente. La conexión a un Headscale externo y la
emisión ACME contra un proveedor real siguen fuera de este ensayo.

El reinicio completo de esa VM también pasó: cambió la identidad de arranque,
la misma clave SSH siguió permitiendo root sin el disco CONFIG y Gateway arrancó
automáticamente con enforce, protección activa y 7/8. Las sumas de la clave
maestra y las opciones se conservaron. El panel limpio respondió por SSO tras
reiniciar y no aparecieron denegaciones inesperadas. Supervisor quedó sano y
compatible; Core 2026.11.2 dejó disponible el alta inicial para el propietario.
La instalación comprobada usa el puerto web 80, consultado con `ha core info`;
la guía del paquete explica cómo obtener el puerto real antes de publicar HA.
