# Validación y límites

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
