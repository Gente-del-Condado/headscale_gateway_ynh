# Headscale Gateway para Home Assistant

Gateway de servicios HTTPS privados sobre Headscale, con nodo Tailscale
integrado, gestión DNS, certificados CA/ACME, panel web, copias de seguridad
y federación entre gateways.

## Instalar y distinguir los paquetes

Añade [Mis_app_ha](https://github.com/Gente-del-Condado/Mis_app_ha) a los
repositorios de aplicaciones de Home Assistant e instala **Headscale Gateway**.
Este complemento ejecuta el servidor Go. La integración de sensores se instala
por separado desde
[headscale_gateway_ha](https://github.com/Gente-del-Condado/headscale_gateway_ha)
y necesita un Gateway al que conectarse.

Las fuentes se mantienen en el principal privado de
[Forgejo](https://gentedelcondado.es/forgejo/wolfbelmi88/headscale_gateway), que
replica en [GitHub](https://github.com/Gente-del-Condado/headscale_gateway).
El compilador público `headscale_gateway_releases` lee una release estable de
Forgejo, prueba su commit exacto y publica esta aplicación en la tienda, conservando
las demás. No edites la copia generada de la tienda.

Necesita un servidor Headscale existente. Para instalarlo desde tu Forgejo
privado, copia `addons/headscale_gateway/` del clon a la carpeta de aplicaciones
locales de Home Assistant. Consulta la [guía completa](DOCS.md): requisitos,
primera configuración, opciones, actualización, copias y resolución de problemas.

Abre el panel con **Abrir interfaz web** y activa **Mostrar en la barra lateral**
para acceder desde el menú. Entrarás con tu sesión administradora de Home
Assistant, sin otra contraseña del Gateway. Las credenciales iniciales son
opcionales y sirven para configurar una cuenta separada para el acceso directo.

El complemento se publica como estable en la tienda de Home Assistant. Consulta
`DOCS.md` para conocer los requisitos de red, las copias y la recuperación.

## Encontrar el portal y la administración

En **Resumen → Estado**, **Dominio principal** aparece primero y enlaza al
portal de servicios de este Gateway. La **URL administrativa** abre el panel;
**Servidor Headscale** corresponde al coordinador VPN. Las direcciones web
completas son enlaces y conservan su puerto y ruta. Se abren en otra pestaña
o en el navegador del dispositivo. Sin un dominio confirmado se muestra
**Pendiente de conexión**, sin crear un enlace ficticio.

El navegador necesita resolver ese DNS, alcanzar la red correspondiente y
confiar en su certificado. Ingress o el SSO de YunoHost permiten administrar
el Gateway, pero no dan por sí solos conectividad del navegador a la Tailnet.
En Android, activa **Conectar aplicaciones** cuando el destino lo requiera.

## Autor y soporte

Autor: **Gente del Condado**. Soporte: [headscale-gateway@gentedelcondado.es](mailto:headscale-gateway@gentedelcondado.es).
[Manual en línea](https://gente-del-condado.github.io/headscale_gateway_ynh/).

El complemento incluye un perfil AppArmor propio en modo estricto, sin permisos
TUN ni NET_ADMIN. En sistemas compatibles con el perfil cargado, la clasificación
comprobada es 7/8. Consulta en `DOCS.md` su alcance y la aceptación de laboratorio.
