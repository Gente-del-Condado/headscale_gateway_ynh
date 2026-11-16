# Integración de Headscale Gateway con Home Assistant

Integración opcional de solo lectura: muestra la conexión VPN, el servicio
HTTPS LAN, la configuración pendiente, los servicios activos, el tiempo de
actividad, el origen de los certificados y el dominio de servicios. Consulta
la API cada 30 segundos. Si no puede conectar, las entidades dejan de estar
disponibles; si el token caduca o se revoca, solicita renovar las credenciales.

Esta integración no instala ni arranca el servidor Gateway. Puede consultar
una instalación directa, el complemento de Home Assistant o una instalación
de YunoHost mediante un acceso administrativo alcanzable desde Core.

## Abrir los servicios del Gateway

Esta integración consulta el motor; no contiene su panel. En el panel del
Gateway al que se conecta, abre **Resumen → Estado → Dominio principal**
para visitar el portal de servicios. La URL administrativa es un acceso
diferente. El navegador necesita conectividad y DNS hacia ese destino.

## Instalar desde el repositorio individual

Añade [headscale_gateway_ha](https://github.com/Gente-del-Condado/headscale_gateway_ha)
como repositorio personalizado de tipo **Integración** en HACS/Marketplace.
Instala, reinicia Home Assistant cuando lo solicite y añade **Headscale Gateway**
en **Dispositivos y servicios**. Después sigue la primera conexión de esta guía.
Este repositorio contiene únicamente la integración; necesitas un Gateway activo.

## Compatibilidad comprobada

El 4 de noviembre de 2026 se ejecutaron las mismas 12 pruebas sobre Home
Assistant Core 2026.10.4 y 2026.11.0, con Python 3.14. Ambas versiones pasaron,
incluida la configuración, las siete entidades, reconfiguración y renovación
de credenciales. Una prueba utiliza el cliente HTTP real contra una API local
controlada para verificar caída, recuperación y reautenticación automática
tras un 401, conservando los identificadores de las entidades.

El procedimiento reproducible está en la
[guía de pruebas de plataformas](https://gente-del-condado.github.io/headscale_gateway_ynh/PLATAFORMAS.html).
La prueba de Core no sustituye la comprobación de Ingress o de la VPN en tu
equipo Home Assistant OS. La instalación privada desde Forgejo se conserva.

## Instalar la integración desde Mis_componente_ha

[Mis_componente_ha](https://github.com/Gente-del-Condado/Mis_componente_ha) es un
catálogo público con varias integraciones. Descarga su ZIP desde **Code →
Download ZIP**, extráelo y copia la carpeta
`custom_components/headscale_gateway/` a
`/config/custom_components/headscale_gateway/` en Home Assistant, mediante
Samba, tu editor de archivos o SSH. Reinicia Home Assistant y sigue
**Primera conexión paso a paso** de esta guía.

Para actualizar, descarga de nuevo el catálogo y sustituye esa misma carpeta,
conservando la configuración de Home Assistant. Reinicia después de la copia.
Los enlaces de documentación y de incidencias de la integración son públicos.

Marketplace y HACS esperan una integración por repositorio; Marketplace toma
la primera carpeta de `custom_components/`. Por eso Mis_componente_ha se utiliza
aquí mediante copia selectiva, conservando las otras integraciones del catálogo.
La [estructura oficial](https://contributors.home-assistant.io/marketplace/reference/repository-structure/)
explica este límite. El repositorio individual headscale_gateway_ha, descrito más abajo, ya está
publicado con esa estructura. No añadas el catálogo múltiple como una única
integración en Marketplace.

## Instalar desde Forgejo privado

Desde Home Assistant 2026.11, Marketplace está integrado en **Ajustes →
Marketplace** y sustituye a HACS. En versiones anteriores se utiliza HACS.
Marketplace instala integraciones comunitarias; el complemento que ejecuta el
Gateway se instala por separado desde **Ajustes → Aplicaciones**.

Marketplace y HACS solo admiten repositorios públicos de GitHub. Para conservar
Forgejo privado, copia la integración desde tu clon local:

```bash
mkdir -p /config/custom_components/headscale_gateway &&
cp -a /data/headscale-gateway-src/custom_components/headscale_gateway/. /config/custom_components/headscale_gateway/
```

Reinicia Home Assistant y añade **Headscale Gateway** desde **Dispositivos y
servicios**. Consulta `docs/INSTALACION_PRIVADA.md` en el repositorio para
configurar el acceso SSH y actualizar el clon.

Repite la copia después de `git pull --ff-only` y reinicia Home Assistant para
actualizarla. Los sensores se configuran desde **Dispositivos y servicios**;
no es necesario instalar HACS en Home Assistant 2026.11 o posterior.

## Publicación automática de la integración

El repositorio conserva `hacs.json` y `custom_components/`. Sin embargo,
Marketplace rechaza repositorios que contienen aplicaciones de Home Assistant
OS: no añadas el repositorio principal, que también incluye `addons/`.

GitHub publica la integración individual en
[headscale_gateway_ha](https://github.com/Gente-del-Condado/headscale_gateway_ha),
con `hacs.json`, avisos y este README. Ese es el repositorio que se añade a
HACS/Marketplace. El mismo componente se copia a `Mis_componente_ha` para Private
Git Manager. Este catálogo contiene varias integraciones y no se añade a HACS
como si fuera una única integración.

La fuente se desarrolla en el principal privado de
[Forgejo](https://gentedelcondado.es/forgejo/wolfbelmi88/headscale_gateway), se
replica en [GitHub](https://github.com/Gente-del-Condado/headscale_gateway) y solo
se publica después de superar la calidad. Los publicadores no escriben en
Forgejo. El servidor se distribuye como aplicación en Mis_app_ha; no está
incluido en este repositorio de integración.

Fuentes oficiales consultadas el 13 de noviembre de 2026:
[transición de HACS a Marketplace](https://github.com/hacs/integration/issues/5590),
[funcionamiento de Marketplace](https://contributors.home-assistant.io/marketplace/how-it-works/)
y [estructura de repositorios](https://contributors.home-assistant.io/marketplace/reference/repository-structure/).

## Conexión y permisos

Crea en el Gateway un token delegado con rol `viewer` y ámbito `read`, y habilita
la lectura mediante Bearer. No utilices la credencial de recuperación.

Introduce una URL administrativa HTTPS alcanzable desde Home Assistant Core,
por ejemplo `https://admin.nodo.example.net:8443`, con la publicación del panel
administrativo habilitada. No añadas `/admin/` ni `/api/v1` a esa URL.

El enlace efímero de Ingress y la URL del portal de YunoHost son accesos para
una sesión de navegador, no para este cliente API. Utiliza el dominio HTTPS
administrativo privado del propio Gateway. No se siguen redirecciones hacia
portales de inicio de sesión ni se les reenvía el token Bearer.

## Certificados y credenciales

La verificación TLS está activada de forma predeterminada. Utiliza un certificado
ACME confiable o configura en Core la confianza en la CA emisora. Desactivar
la verificación es una opción explícita para pruebas. HTTP solo se admite con
una IP loopback indicada expresamente.

Los tokens se guardan en las entradas de configuración protegidas de Home
Assistant y no se incluyen en los atributos de los sensores ni en los
resultados de diagnóstico. Reconfigura la integración para cambiar la URL o
la credencial.

## Primera conexión paso a paso

1. Comprueba que puedes abrir el panel del Gateway y que Core alcanza su URL
   administrativa. Si usan máquinas diferentes, `127.0.0.1` no apunta al Gateway.
2. Crea el token delegado de lectura y anótalo de forma privada.
3. Abre **Ajustes → Dispositivos y servicios → Añadir integración** y selecciona
   **Headscale Gateway**.
4. Introduce la URL base, el token y la opción de verificar TLS. Mantén esta
   verificación activada para el uso habitual.
5. Abre el dispositivo creado y comprueba sus siete entidades. Los valores se
   renuevan cada 30 segundos; no hace falta crear sensores YAML adicionales.

## Entidades disponibles

| Clave de la entidad | Qué representa |
| --- | --- |
| `vpn_connected` | Conexión del nodo del Gateway a la VPN |
| `lan_https_active` | Estado del listener HTTPS LAN |
| `setup_required` | Indica que queda configuración inicial pendiente |
| `services_active` | Número de servicios activos |
| `uptime_seconds` | Tiempo de funcionamiento, expresado en segundos |
| `certificate_source` | Procedencia del certificado que comunica el Gateway |
| `domain` | Dominio base configurado para los servicios |

Home Assistant elige el `entity_id` final a partir de los nombres y del registro
local. Utiliza el identificador que muestre tu instalación al crear tarjetas o
automatizaciones. La integración solo observa estos valores; no publica servicios
ni cambia la configuración del Gateway.

## Si no conecta

| Mensaje o síntoma | Acción |
| --- | --- |
| Credenciales no válidas | Comprueba rol `viewer`, ámbito `read`, caducidad y lectura Bearer habilitada |
| No se puede conectar | Revisa DNS y conectividad desde Core; comprueba el certificado y su CA |
| Redirección a un portal | Utiliza el endpoint administrativo del Gateway, no la sesión Ingress/SSO |
| Entidades no disponibles | Comprueba el proceso Gateway; recuperarán sus valores al volver la API |
| Solicitud de reautenticación | Genera un token válido y completa el flujo de renovación de credenciales |

Para cambiar la dirección, utiliza **Reconfigurar** en la integración. Para
actualizar el código, copia la carpeta de la nueva versión y reinicia Core.
Conserva la entrada existente para mantener los identificadores de las entidades.
