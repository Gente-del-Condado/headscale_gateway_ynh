# Headscale Gateway: descargas públicas

Este repositorio distribuye instaladores, fuentes correspondientes, avisos y
sumas de Headscale Gateway. El principal y su historial permanecen privados:
[Forgejo](https://gentedelcondado.es/forgejo/wolfbelmi88/headscale_gateway) →
[espejo GitHub](https://github.com/Gente-del-Condado/headscale_gateway).
GitHub Actions prepara, verifica y publica aquí los archivos de cada entrega.
No hay sincronización de regreso a Forgejo.

## Elegir la descarga

En [Releases](https://github.com/Gente-del-Condado/headscale_gateway_releases/releases)
separa estas funciones:

- **headscale-gateway-linux-…** o paquetes **.deb/.rpm**: Gateway completo, con motor Go y panel web. No son solo la bandeja.
- **headscale-gateway-windows-…** y **darwin-…**: motor y herramientas de la plataforma.
- **gateway-tray-…**: cliente gráfico opcional; se conecta a un Gateway.
- **headscale-gateway-release.apk**: Android con firma estable. Conserva esa firma al actualizar.
- **fdroid-unsigned.apk** y **play.aab**: preparación de canales, no envío a las tiendas.

Los instaladores pequeños de bandeja no requieren unir partes. Los fuentes de
Electron, Chromium y FFmpeg se descargan aparte desde **la misma release**.
Solo el archivo grande de fuentes Chromium se divide en `.part-01`, `.part-02`,
…; une sus partes en orden y comprueba el SHA-256 del JSON antes de extraerlo.
Conserva los avisos y los fuentes correspondientes al redistribuir el programa.

El código propio usa AGPL-3.0-only. El cliente usa bibliotecas de FFmpeg bajo
LGPL-2.1-or-later; sus avisos originales, fuentes exactos y parches de Electron
están disponibles junto a cada descarga, sin cambiar sus licencias.

## Paquetes específicos

- [YunoHost](https://github.com/Gente-del-Condado/headscale_gateway_ynh): paquete y recursos públicos propios.
- [Home Assistant](https://github.com/Gente-del-Condado/headscale_gateway_ha): integración; el servidor se instala desde [Mis_app_ha](https://github.com/Gente-del-Condado/Mis_app_ha).
- [Flatpak](https://github.com/Gente-del-Condado/headscale_gateway_flatpak): manifiesto y paquete del Gateway en sesión de usuario; no implica inclusión en Flathub.

[Manual YunoHost](https://gente-del-condado.github.io/headscale_gateway_ynh/) ·
[Manual Home Assistant](https://gente-del-condado.github.io/headscale_gateway_ha/).
Las instalaciones y actualizaciones son decisiones del administrador; publicar
no modifica datos, credenciales ni servicios de una instalación existente.
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
