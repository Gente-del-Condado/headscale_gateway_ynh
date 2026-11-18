# Headscale Gateway para Flatpak

Distribución del **motor Go completo y su panel web**, no solo Gateway-Tray.
La fuente se mantiene en `packaging/flatpak/` del principal privado de
[Forgejo](https://gentedelcondado.es/forgejo/wolfbelmi88/headscale_gateway), se
replica a [GitHub](https://github.com/Gente-del-Condado/headscale_gateway) y
Actions exporta aquí únicamente el paquete. Nunca escribe de vuelta en Forgejo.

## Alcance

Se ejecuta como aplicación de consola en la sesión del usuario. Abre el panel
con la dirección que muestra el proceso, normalmente http://127.0.0.1:9091.
Incluye el mismo motor, API, SQLite, certificados y copias que otras plataformas.
Usa tsnet en espacio de usuario y no pide acceso al TUN, al bus del sistema,
a archivos del host ni a `flatpak-spawn --host`.

Sus datos están aislados en `~/.var/app/es.gentedelcondado.HeadscaleGateway/data/`.
No adopta automáticamente una instalación nativa ni su identidad VPN. Para
migrar utiliza los perfiles o copias cifradas del manual; no ejecutes dos procesos
con la misma base de datos o identidad. No instala una CA en el almacén del host.
Para un servicio de sistema que arranque con Debian o Fedora, utiliza .deb/.rpm.

## Instalación

Descarga el archivo `.flatpak` de la release pública correspondiente, comprueba
su suma e instala:

```sh
flatpak install --user ./headscale-gateway-1.4.18-x86_64.flatpak
flatpak run es.gentedelcondado.HeadscaleGateway
```

Se necesita el runtime Freedesktop declarado en el manifiesto. Una actualización
con el mismo identificador conserva el directorio de datos de Flatpak.

## Estado de Flathub

Este paquete se distribuye directamente, fuera del catálogo Flathub. Sus
[normas actuales](https://docs.flathub.org/docs/for-app-authors/requirements)
excluyen software solo de consola o bandeja y prohíben manifiestos generados o
asistidos por IA para una solicitud. Este manifiesto se prepara con asistencia
IA: no se presenta como apto para solicitar inclusión ni se envía una solicitud.

## Construcción

El manifiesto toma binarios 1.4.18 verificados de los recursos públicos YunoHost.
Los fuentes completos del motor y sus dependencias están en `source.tar.gz`
de esa misma release; los fuentes completos del proyecto se publican aparte.
No reconstruye ni modifica el motor para Flatpak. `flatpak-builder` construye el
paquete dentro de su sandbox; las pruebas se ejecutan en GitHub, no en el Linux
habitual del mantenedor.

[Manual](https://gente-del-condado.github.io/headscale_gateway_ynh/).

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

## Instalación y acceso del escritorio

El menú de KDE, GNOME u otro escritorio contiene **Headscale Gateway**. El primer
arranque explica que el motor seguirá disponible al cerrar el navegador, pide una
cuenta del panel y abre la administración local. Después se confirma el nombre del
dispositivo desde el panel común antes de conectar a Headscale. Las contraseñas se
introducen en diálogos del escritorio y se guardan con el contrato común protegido;
no se pasan como argumentos ni aparecen en registros.

La sesión mantiene una sola instancia con un bloqueo privado y recupera fallos del
motor con reintentos limitados. Pulsar de nuevo el acceso abre el panel existente.
El permiso de segundo plano y arranque al iniciar sesión se solicita mediante el
portal del escritorio. Solo queda activado si el escritorio lo confirma; una
negativa o un portal no compatible deja un aviso en los registros. No se modifica
systemd del host ni se amplían los permisos de archivos o del bus de la aplicación.
Para detenerlo utiliza `flatpak kill es.gentedelcondado.HeadscaleGateway`; para
retirar el arranque automático revisa los permisos de aplicaciones de tu escritorio.

Los datos siguen dentro de los datos privados de Flatpak. Si existe una instalación
anterior, primero detén todas sus instancias; el asistente pide confirmarlo antes
de adoptar la misma SQLite, identidad y credenciales, sin restablecerlas.
