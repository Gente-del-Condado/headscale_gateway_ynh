# Mantenimiento del paquete independiente

Headscale Gateway se mantiene para instalarlo y actualizarlo desde
[su repositorio](https://github.com/Gente-del-Condado/headscale_gateway_ynh).
No está en el catálogo oficial y no se solicitará su incorporación.

## Normas utilizadas

Se toman como referencia [example_ynh](https://github.com/YunoHost/example_ynh),
[el formato 2](https://doc.yunohost.org/en/dev/packaging/manifest/),
[los recursos](https://doc.yunohost.org/en/dev/packaging/resources/) y
[los helpers 2.1](https://doc.yunohost.org/dev/packaging/scripts/helpers_v2.1/).
Los recursos de usuario, directorios, permisos, puertos y dependencias los
provisiona YunoHost. El instalador usa `ynh_setup_source` con la arquitectura y
SHA-256 declarados; los ejecutables y fuentes se descargan de una release pública.
La rama principal del paquete público no incluye binarios ni archivos de fuentes.
El logo existente y todos los avisos de terceros se conservan.

La configuración del motor y el secreto entre nginx y el Gateway requieren un
helper específico. El motor verifica NSS y el grupo `admins`, el secreto del
proxy y CSRF: una cabecera o una conexión loopback no acredita un administrador.
La captura de SQLite, secretos e identidad VPN se hace con el servicio detenido,
antes de que el sistema de copias copie el archivo de datos. Estas adaptaciones
se mantienen porque son contratos del Gateway, no funciones inventadas de YunoHost.

## Publicación automática

Forgejo es el origen del proyecto; GitHub lo replica. Tras la revisión y la
seguridad obligatoria, el flujo publica los fuentes completos en `upstream-source`
y prepara una petición con sus sumas. El repositorio público construye recursos
para amd64 y arm64 desde ese commit. La etiqueta `server-vX.Y.Z` se crea primero
en Forgejo: así su espejo conserva la release de GitHub y no la devuelve a borrador
al retirar una etiqueta que solo existiera en la réplica.
Sus sumas deben coincidir con las de los
binarios y fuentes previamente comprobados. Una release existente se verifica
sin reemplazar sus archivos. Solo después de descargar y verificar los tres
recursos se publica la revisión instalable, por Forgejo y su réplica GitHub.
La descarga se comprueba sin credenciales: un borrador no es un recurso público.
Un fallo deja publicada la revisión anterior del instalador.

Los cambios de paquete aumentan `~ynhN`, manteniendo la versión del motor.
Las instalaciones se actualizan explícitamente desde su URL: publicar el
repositorio no cambia el servidor del usuario.

## Rechazo anterior y límites

La solicitud [3722](https://github.com/YunoHost/apps/pull/3722) se cerró el
14 de noviembre de 2026. El revisor indicó falta de adecuación a los estándares
y generación con IA, sin enumerar fallos concretos. Por ello no se atribuyen
motivos específicos adicionales al revisor. La revisión técnica de este paquete
corrige diferencias contrastables: recursos de descarga estándar, separación de
binarios y repositorio instalable y documentación de mantenimiento independiente.

La documentación oficial exige seguir la plantilla y comprender y mantener el
código, también cuando se usa IA. No se oculta esa asistencia ni se presenta el
paquete como aprobado por YunoHost.

## Comprobaciones

Se ejecutan el linter y `package_check` oficiales en una VM desechable con
YunoHost 12.1.41.2, amd64. La batería incluye raíz, subruta, multiinstancia,
copia/restauración, actualización desde la misma revisión, migración desde
`1.4.7~ynh1`, cambio de URL y linter. Los resultados reales se registran con
la entrega, sin asignar un nivel oficial.

El 14 de noviembre de 2026 se comprobó además una actualización real de
`1.4.7~ynh1` a `1.4.7~ynh2` en ese laboratorio: se conservaron el contenido
SQLite de prueba, la clave maestra, las credenciales y el secreto del proxy.
El servicio quedó activo y los archivos privados conservaron sus permisos.
La sesión SSO de un administrador respondió 200, con TLS verificado. La API
del motor rechazó con 403 los accesos anónimos y las cabeceras de identidad
falsificadas, incluso por loopback. Si el permiso principal de YunoHost se
limita a administradores, SSOwat redirige antes al SSO (302) a quien no tiene sesión.

No estar en el catálogo genera avisos de catálogo; no se manipulan para obtener
una puntuación. Compilar arm64 no acredita instalarlo en un dispositivo arm64.
