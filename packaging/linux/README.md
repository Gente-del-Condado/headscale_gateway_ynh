# Gateway completo en Debian y Fedora

Los paquetes `.deb` y `.rpm` incluyen el motor Go, el panel web y las herramientas
auxiliares. Gateway-Tray es un cliente opcional y no es necesario para usar el
servidor. Las descargas y sus fuentes están en
[headscale_gateway_releases](https://github.com/Gente-del-Condado/headscale_gateway_releases/releases).

Instala el archivo de tu arquitectura con `sudo apt install ./headscale-gateway_1.4.14-1_amd64.deb`
o `sudo dnf install ./headscale-gateway-1.4.14-1.x86_64.rpm`.
El paquete crea un usuario de servicio sin acceso interactivo. La primera
instalación no arranca ni expone el panel sin configurar una cuenta:

```sh
sudo -u headscale-gateway headscale-gateway-configure --admin miadministrador
sudo systemctl enable --now headscale-gateway
```

Con el ejemplo anterior, entra en **http://127.0.0.1:9091/admin/** con:

- **Usuario:** `miadministrador`, el valor que elegiste en `--admin`.
- **Contraseña:** la contraseña nueva del panel que creaste en el configurador.

Si `sudo` pide una contraseña, esa es la de tu cuenta de Linux y sirve para
autorizar el comando. Después el configurador pide crear y repetir otra
contraseña para el panel. No es la contraseña del usuario de servicio
`headscale-gateway`, que no tiene inicio de sesión interactivo. Puedes cambiar
`miadministrador` por el nombre que prefieras antes de ejecutar el configurador.
La contraseña del panel se introduce oculta, nunca como argumento.
El configurador muestra al terminar el usuario, la URL y la orden de arranque.
Para el acceso remoto inicial, utiliza un túnel SSH.
Configura Headscale y el resto de opciones desde el panel común del proyecto.

Los datos, identidad VPN, SQLite, claves y arranque se guardan bajo
`/var/lib/headscale-gateway/`. Una actualización reemplaza ejecutables y reinicia
solo un servicio que ya estuviera activo. No recrea cuentas del Gateway ni
sobrescribe los datos. Al desinstalar se detiene el servicio y se conservan sus
datos; eliminarlos requiere una decisión independiente del administrador.

No instala automáticamente el Gateway sobre una instalación manual que use
`/var/lib/headscale-gateway/gateway.sqlite`. Conserva esa instancia y sus copias:
la migración se hace explícitamente, con el servicio anterior detenido, mediante
los perfiles o copias cifradas del manual. No compartas base de datos ni identidad
entre dos procesos. El paquete no modifica la confianza CA del sistema ni SELinux.

Las comprobaciones de instalación, actualización y conservación se ejecutan en
contenedores Debian y Fedora en GitHub. No sustituyen una aceptación real con
systemd, SELinux y la red de tu equipo.

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

## Elegir arquitectura e instalar en Fedora

Comprueba `uname -m`: `x86_64` corresponde al RPM `x86_64` (Debian: `amd64`);
`aarch64` corresponde al RPM `aarch64` (Debian: `arm64`). El RPM ARM no sirve
para un PC Intel/AMD. Si la tienda permanece cargando, utiliza una terminal:
`sudo dnf install ./headscale-gateway-VERSION-1.x86_64.rpm`, sustituyendo VERSION.
DNF muestra la causa concreta si hay un error de arquitectura, dependencias o permisos.
El paquete nativo instala un servicio, no un acceso de bandeja: configura la cuenta
con `headscale-gateway-configure` antes de habilitarlo y abre el panel en el navegador.

## Servicio y menú de aplicaciones

La instalación incluye la unidad systemd y el acceso **Headscale Gateway** del
menú de KDE/GNOME. El acceso abre el navegador con el panel loopback del servicio,
incluido un puerto local personalizado. Si aún no está configurado o activo,
muestra las instrucciones iniciales; no crea credenciales ni eleva permisos por
su cuenta. El paquete no habilita un servicio sin cuenta administrativa. Tras
configurarla y activar la unidad con las órdenes anteriores, el servicio arranca
con el sistema y se reinicia tras un fallo. Cerrar el navegador no lo detiene.
