# Headscale Gateway: descargas públicas

Este repositorio distribuye instaladores, fuentes correspondientes, avisos y
sumas de Headscale Gateway. El principal y su historial permanecen privados:
[Forgejo](https://gentedelcondado.es/forgejo/wolfbelmi88/headscale_gateway) →
[espejo GitHub](https://github.com/Gente-del-Condado/headscale_gateway).
GitHub Actions prepara, verifica y publica aquí los archivos de cada entrega.
No hay sincronización de regreso a Forgejo.

## Elegir la descarga

Abre la [última release de Gateway](https://github.com/Gente-del-Condado/headscale_gateway_releases/releases/latest)
y elige tu sistema y arquitectura. La release de fuentes de Electron es
independiente y no sustituye «Latest» de la aplicación.

| Quiero | Archivo o destino |
| --- | --- |
| Gateway completo en Debian/Ubuntu | `headscale-gateway_VERSION-1_amd64.deb` o `…_arm64.deb` |
| Gateway completo en Fedora | `headscale-gateway-VERSION-1.x86_64.rpm` o `…aarch64.rpm` |
| Motor en Windows, Linux o macOS | `headscale-gateway-windows-…zip`, `…linux-…tar.gz` o `…darwin-…tar.gz` |
| Gateway completo en Linux mediante Flatpak | `headscale-gateway-VERSION-x86_64.flatpak`; también en [su repositorio](https://github.com/Gente-del-Condado/headscale_gateway_flatpak/releases) |
| Aplicación Android | `headscale-gateway-release.apk`, con firma estable |
| Bandeja opcional de escritorio | `gateway-tray-linux-x64.tar.gz` o `gateway-tray-windows-x64.zip`; se conecta a un Gateway |
| Código del proyecto | `headscale-gateway-fuentes-publicos-VERSION.zip` |
| Fuentes del motor Go | `headscale-gateway-go-sources-VERSION.tar.gz` |
| Fuentes específicos Android | `headscale-gateway-android-sources-VERSION.zip` |
| Comprobar integridad | `SHA256SUMS` de la release correspondiente |

`fdroid-unsigned.apk` y `play.aab` preparan canales de distribución; no son
la APK firmada para instalar normalmente. Play Store sigue solo preparado.
Los JSON de validación son informes técnicos, no instaladores.

## Fuentes de Electron y dependencias

Los archivos `chromium-…`, `electron-…`, `node-v…` y `nan-…` son fuentes de
terceros del runtime de la bandeja. **No necesitas descargarlos para instalar
ni utilizar Gateway.** Para reconstruir o redistribuir la bandeja, usa la
release `desktop-sources-electron-VERSION-HUELLA` enlazada en las notas de tu
entrega y en `legal/PUBLIC-SOURCES.json` del instalador. Incluye los fuentes
exactos, parches, instrucciones `RECONSTRUIR.md`, índice y `SHA256SUMS`.

El publicador reutiliza ese conjunto entre versiones Gateway con el mismo
lock y rechaza incluir otra vez esos archivos entre los instaladores. Si
cambia Electron o alguna revisión del lock, exige otro conjunto verificado.
No retires una release de dependencias mientras haya instaladores que la enlacen.

Los dos instaladores de bandeja son archivos completos: se extraen directamente.
Solo los fuentes Chromium se dividen por tamaño; une sus `.part-01`, `.part-02`,
… en orden y comprueba la suma completa de su `.parts.json` antes de extraer.
La 1.4.16 conserva sus archivos y URL originales; esa duplicación histórica se
mantiene para no romper sus instaladores. Las siguientes entregas no la repiten.

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
