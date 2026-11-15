# Gateway completo en Debian y Fedora

Los paquetes `.deb` y `.rpm` incluyen el motor Go, el panel web y las herramientas
auxiliares. Gateway-Tray es un cliente opcional y no es necesario para usar el
servidor. Las descargas y sus fuentes están en
[headscale_gateway_releases](https://github.com/Gente-del-Condado/headscale_gateway_releases/releases).

Instala el archivo de tu arquitectura con `sudo apt install ./headscale-gateway_1.4.9-1_amd64.deb`
o `sudo dnf install ./headscale-gateway-1.4.9-1.x86_64.rpm`.
El paquete crea un usuario de servicio sin acceso interactivo. La primera
instalación no arranca ni expone el panel sin configurar una cuenta:

```sh
sudo -u headscale-gateway headscale-gateway-configure --admin miadministrador
sudo systemctl enable --now headscale-gateway
```

La contraseña se introduce oculta, nunca como argumento. El panel inicial escucha
en http://127.0.0.1:9091; utiliza un túnel SSH para el acceso remoto inicial.
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
