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
Actions prueba la revisión y publica esta aplicación en la tienda, conservando
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
