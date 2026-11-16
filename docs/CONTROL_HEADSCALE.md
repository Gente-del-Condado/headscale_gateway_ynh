# Administrar Headscale desde Gateway

El motor Go y el portal compartido incorporan **Headscale → Coordinador / Ajustes**.
La misma interfaz sirve en Linux, Windows, Android, Home Assistant y YunoHost.
El controlador que modifica el servicio Headscale se registra explícitamente en
su anfitrión Linux; los demás Gateway pueden utilizar una delegación remota.
Instalar el paquete YunoHost no activa ese privilegio automáticamente.

La gestión existente de servicios, proxy, certificados, DNS-01, copias, usuarios,
nodos, rutas, claves de registro y ACL se conserva. Los ajustes DNS siguientes
pertenecen a la Tailnet: no sustituyen los registros de Technitium ni alteran los
certificados de cada Gateway. Conserva Headplane hasta comprobar la nueva gestión
con tu configuración; evita editar el mismo archivo simultáneamente desde ambos.

## Funciones

- MagicDNS, dominio base, resolutores globales, Split DNS y dominios de búsqueda.
- Sustituir los resolutores locales de los clientes que aceptan DNS de la Tailnet.
- Registros adicionales A y AAAA: archivo dinámico autorizado sin reinicio;
  registros incluidos directamente en YAML de solo lectura.
- Restricciones OIDC por dominios de correo, grupos y usuarios, conservando el
  proveedor, sus credenciales y el resto de la configuración.
- Usuarios y claves de registro con caducidad, reutilización, condición efímera,
  etiquetas y revocación. El secreto se muestra solo al crear la clave.
- Observador opcional que reutiliza tsnet del controlador para consultar sistema,
  versión del cliente y conectividad. No instala agentes en los demás nodos.

Las listas OIDC configuradas se combinan mediante **Y**. Dentro de la lista de
los grupos permitidos basta pertenecer a uno. Vaciar una lista desactiva ese filtro.
No concede el rol administrador del Gateway, no revoca nodos ya registrados y no
invalida claves de registro existentes. Conserva un acceso administrativo al
anfitrión para recuperar una restricción errónea.

## Registrar el controlador local

Requiere systemd, un Headscale con SQLite y cuentas de servicio distintas para
Headscale y Gateway, ambas sin privilegios. La validación aislada se ha diseñado
para Headscale 0.29. No admite configurar desde el portal rutas, órdenes ni unidades
arbitrarias. Selecciona los valores reales del anfitrión como administrador:

```sh
sudo headscale-gateway-setup-headscale \
  --instance native \
  --gateway-binary /usr/libexec/headscale-gateway/headscale-gateway \
  --gateway-unit headscale-gateway.service \
  --headscale-unit headscale.service \
  --headscale-binary /usr/bin/headscale \
  --config /etc/headscale/config.yaml \
  --health-url http://127.0.0.1:8080/health \
  --restart-gateway
```

La URL Headscale configurada en el Gateway debe coincidir con `server_url` del
coordinador seleccionado. Si utilizas intencionadamente otro origen API para
esa misma instancia, regístralo mediante `--api-origin`. El vínculo se comprueba
también durante el seguimiento de las operaciones para evitar mezclar ajustes
de un coordinador con nodos de otro.

La IP de salud debe pertenecer al anfitrión y alcanzar directamente el Headscale
seleccionado. Usa HTTPS si ese listener lo requiere y añade `--health-ca` con su
CA local cuando no utilice una CA pública. Nunca se omite la verificación TLS ni
se siguen redirecciones. Añade `--records /ruta/records.json` solo si ese archivo
ya existe y coincide con `dns.extra_records_path` del YAML. No combines
`extra_records` y `extra_records_path`: Headscale no lo admite. El instalador no
migra ni vacía registros existentes.

El registro root queda en `/etc/headscale-gateway-control/`. El servicio
`headscale-gateway-control-INSTANCIA.service` ejecuta una copia del motor propiedad
de root, separada del ejecutable modificable por la cuenta de la aplicación.
El portal conserva su usuario sin privilegios. Se comunica mediante un socket
Unix privado con comprobación del UID; no se abre un puerto administrativo nuevo.

En el panel, selecciona **Configuración → Control de Headscale → Controlador local
instalado**, guarda y reinicia el Gateway. Conserva la URL y clave API Headscale
que ya utilizas para usuarios, nodos y claves. No se generan credenciales nuevas
ni se cambia la identidad VPN durante el registro del controlador.

### YunoHost

La herramienta se incluye como `conf/setup-headscale` en el paquete publicado.
Desde una copia comprobada de ese paquete, ejecútala con `sudo python3`, usando
`--instance ynh-headscale_gateway`, `--gateway-unit headscale_gateway.service` y
el binario instalado `/var/www/headscale_gateway/headscale-gateway`. Adapta el
identificador si tienes varias instancias. Selecciona la unidad, usuario y rutas
reales del Headscale instalado: no presupongas que está en `/etc/headscale`.

La actualización del paquete renueva la copia root del motor cuando encuentra
ese registro local. La restauración en el mismo anfitrión lo conserva y refresca.
Una copia del Gateway no concede privilegios automáticamente en otro servidor:
allí registra de nuevo el controlador después de restaurar Headscale. Las copias
del Gateway no sustituyen una copia independiente de la base, configuración y
claves de Headscale.

## Delegar en otro Gateway

1. En el controlador, habilita la URL administrativa de la Tailnet
   (`admin.domain_mode=tailnet`) y utiliza su origen `https://admin.NODO.DOMINIO`.
   La URL de YunoHost con SSO y una ruta como `/gateway/` conserva su acceso de
   sesión; no sirve como origen de esta delegación Bearer. Activa explícitamente
   la exposición Bearer del módulo en
   **API / Permisos**: lectura de Headscale y, solo si lo necesitas, escritura.
2. Crea un token de rol `viewer` con `headscale-read` para consultar, o de rol
   `operator` con `headscale-read` y `headscale-write` para gestionar. Usa una
   caducidad apropiada. Los tokens antiguos de «Red» no heredan estos permisos.
3. En el Gateway cliente, aprueba y verifica la CA del controlador en **CA y
   confianza**. Esa confianza TLS por sí sola no autoriza la administración.
4. Selecciona **Otro Gateway autorizado**; introduce su origen HTTPS privado sin
   rutas, la huella SHA-256 de la CA aprobada y el token delegado. Guarda y reinicia.

El token se almacena cifrado y no se devuelve al navegador. Solo se conecta con
el origen aprobado mediante direcciones privadas y TLS verificado; no se siguen
redirecciones ni se utilizan proxies del entorno. Un controlador remoto no puede
reenviar la delegación a un tercer Gateway. Revoca el token en el controlador para
retirar el acceso. El token no concede configuración del Gateway, identidad ni MFA.
Los servicios y comprobaciones de conectividad del Gateway cliente siguen usando
su propia conexión VPN.

## Revisar, aplicar y recuperar

Cada formulario prepara un cambio tipado sobre una revisión de los archivos.
**Revisar** muestra únicamente los campos admitidos y su impacto. **Aplicar** inicia
una operación identificada; cerrar el navegador no cancela una escritura iniciada.
Una revisión antigua se rechaza para evitar sobrescribir una edición posterior.

Antes de tocar el coordinador, `headscale configtest` se ejecuta sin privilegios
sobre una copia temporal con base y claves nuevas. Nunca abre la base activa ni
su identidad Noise/DERP. DNS y OIDC requieren reinicio real de Headscale: SIGHUP
no recarga esos apartados en Headscale 0.29. Los registros dinámicos no lo requieren.

El ayudante guarda un diario root antes de escribir, conserva propietarios,
permisos y contexto SELinux, y comprueba `/health` después de aplicar. Si falla,
restaura el estado anterior. Si no puede recuperarlo, conserva el diario y bloquea
nuevas operaciones para una recuperación local. Si detecta una modificación ajena
no la sobrescribe. No elimines `/var/lib/headscale-gateway-control/` durante una
recuperación pendiente.

El seguimiento del navegador consulta el resultado y nunca vuelve a enviar una
mutación por perder la conexión. El historial de operaciones es acotado y reside
en el proceso; tras reiniciarlo puede desaparecer su identificador. En ese caso,
lee el estado actual antes de repetir un cambio. El diario de recuperación sí es
persistente y se procesa antes de aceptar operaciones al arrancar.

## Observador y límites

Activa **Sincronizar información de nodos** en Configuración. El panel actualiza
el resultado de la sincronización sin necesitar una recarga manual y suspende
las consultas del observador cuando su apartado deja de estar visible. Actualiza cada minuto
mediante la API Headscale y `WhoIs` de tsnet, respetando las ACL y la visibilidad del
controlador. Si un nodo no es visible, conserva el último dato con su fecha y lo
marca como antiguo; nunca presenta una versión antigua como una observación nueva.
La identidad se correlaciona con el ID y la clave pública del nodo. Un nodo
eliminado o recreado no hereda datos del anterior. Se limita a 512 observaciones y
muestra cuántos nodos quedan fuera del límite. No expone tokens de notificaciones,
identificadores de registros ni el objeto completo Hostinfo.

No gestiona todavía el alta inicial de un proveedor OIDC ni sus secretos. El
editor ACL existente conserva los modos admitidos por la API Headscale; una
política almacenada en archivo requiere administración de ese archivo en el
anfitrión. Este módulo no convierte Headscale en un servicio distribuido ni cambia
la arquitectura de certificados del Gateway.

Para revocar el vínculo local:

```sh
sudo headscale-gateway-setup-headscale --instance native --disable
```

Se detiene el ayudante y se retira el vínculo del servicio Gateway; reinicia ese
Gateway para actualizar su entorno. Se conservan Headscale, sus datos, el registro
y cualquier diario de recuperación. La desinstalación de los paquetes revoca los
vínculos correspondientes sin borrar los datos del coordinador.

## API del módulo

Las rutas comparten autenticación de sesión, rol y CSRF con el portal. Bearer
requiere además exposición explícita y los alcances del módulo. Solo un Gateway
con vínculo local activo acepta delegaciones entrantes.

| Método y ruta bajo `/api/v1/network/control` | Permiso Bearer | Contenido |
| --- | --- | --- |
| `GET /info` | `headscale-read` | Modo y capacidades efectivas para ese token |
| `GET /document` | `headscale-read` | Revisión, DNS, filtros OIDC y registros admitidos |
| `POST /preview` | `headscale-write` | Propuesta sin escritura ni reinicio |
| `POST /apply` | `headscale-write` | Acepta una operación; responde `202` con su ID |
| `GET /operations/{id}` | `headscale-read` | Estado, fechas y error saneado de la operación |
| `GET /agent` | `headscale-read` | Observaciones, antigüedad y límites |
| `POST /agent/sync` | `headscale-write` | Solicita sincronización, sin esperar a terminar |
| `GET /headscale/users` | `headscale-read` | Usuarios del coordinador |
| `GET /headscale/keys` | `headscale-read` | Claves de registro sin secretos |
| `GET /headscale/nodes` | `headscale-read` | Inventario de nodos |
| `POST /headscale/action` | `headscale-write` | Catálogo cerrado de acciones existentes |
| `GET /headscale/policy` | `headscale-read` | Política ACL existente |
| `PUT /headscale/policy` | `headscale-write` | Actualización ACL admitida por la API Headscale |

Las propuestas incluyen `revision` y al menos uno de `dns`, `oidc` o `records`.
Cada apartado enviado reemplaza sus campos tipados completos; omitir un apartado
lo conserva. No se aceptan campos desconocidos. Una revisión antigua, un cambio
vacío, una operación activa o un candidato inválido se rechazan con `409`.
El documento nunca contiene el YAML completo, credenciales OIDC ni rutas locales.

Ejemplo de registros, usando la revisión obtenida inmediatamente antes:

```json
{
  "revision": "REVISION_SHA256_DEL_DOCUMENTO",
  "records": [
    {"name": "fotos.pc1.intra.example.test", "type": "A", "value": "100.64.0.7"}
  ]
}
```

El identificador de operación tiene 32 caracteres hexadecimales. Los estados son
`queued`, `validating`, `applying`, `restarting`, `checking`, `rolling_back` y los
terminales `completed`, `failed`, `rolled_back` o `recovery_required`.
`finished_at` identifica el resultado terminal. Un ID desconocido devuelve `404`;
no implica que el cambio no se haya aplicado. No reintentes automáticamente
`POST /apply` después de perder una respuesta.

Una actualización no reactiva un vínculo desactivado. Para reactivarlo de forma
explícita utiliza `--refresh --enable`, seleccionando de nuevo el binario del
Gateway, y reinicia el Gateway para cargar su vínculo.

La retirada de un paquete suspende el vínculo (`--detach`) y conserva la selección
local. Restaurar una copia YunoHost en ese anfitrión solicita `--reattach`; esto
no anula una revocación explícita hecha con `--disable`. Una instalación nueva o
una actualización ordinaria no recuperan por su cuenta un vínculo suspendido.

Al exportar un perfil sin secretos se conserva el destino remoto, pero el modo
de control queda desactivado: podrás introducir un token y activarlo de forma
explícita en destino. Los perfiles con secretos conservan la delegación cifrada;
la CA del controlador también debe aprobarse en el almacén de confianza local.

Registra un único controlador local por instancia de Headscale. Los demás
Gateway utilizan el modo remoto. No edites simultáneamente esos mismos campos
desde Headplane u otro editor: la revisión detecta cambios previos, pero no
sustituye la coordinación entre administradores durante una aplicación.

## Validación de esta entrega

La revisión 1.4.15 se comprobó el 16 de noviembre de 2026 con Headscale 0.29.7
y YunoHost 12.1.42 en una segunda instancia aislada del Gateway. Se verificaron:

- Instalación del paquete 1.4.14 y actualización a 1.4.15, conservando SQLite,
  credenciales cifradas, clave maestra, CA privada e identidad VPN.
- Copia YunoHost, eliminación de la instancia de prueba y restauración real: se
  recuperan los datos y el vínculo local, sin reiniciar la instancia original.
- DNS global/dividido, búsqueda, restricciones OIDC y registros dinámicos;
  revisión previa, conflicto de revisión, rechazo de candidatos y rollback.
- Registro OIDC real con un proveedor ficticio: usuario autorizado aceptado y
  usuario fuera de las restricciones rechazado. Claves de registro de un solo
  uso, reutilizables y efímeras, con creación, revocación y listado sin secretos.
- Delegación entre dos Gateway por la Tailnet con TLS verificado; token de
  lectura sin capacidad de escritura y token de escritura limitado al módulo.
- Panel autenticado mediante SSO, controles de sesión/CSRF/alcances, observador
  de nodos y presentación de escritorio y móvil en navegador real.
- Reactivación, revocación explícita, retirada y restauración del vínculo del
  controlador; diario de recuperación y protección frente a cambios externos.

Las suites Go, Python y JavaScript y la compilación estricta del manual forman
parte de la comprobación local. Se comprobaron también la compilación Windows
y los motores Android ARM64 y x86_64. Esto no equivale a una nueva aceptación
completa del instalador Windows ni de la APK en un dispositivo físico.

El actuador local requiere Linux con systemd, Headscale 0.29 y SQLite. El modo
remoto utiliza el motor común en todas las plataformas. Los datos del observador
pueden no estar disponibles para nodos desconectados o sin respuesta WhoIs; se
muestra su antigüedad y no se inventa información. La gestión ACL conserva las
limitaciones de la API Headscale: el archivo de políticas local no se convierte
a modo base de datos automáticamente.
