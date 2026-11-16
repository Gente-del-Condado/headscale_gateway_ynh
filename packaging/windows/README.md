# Motor de Windows como servicio

Autor: **Gente del Condado**. Soporte:
[headscale-gateway@gentedelcondado.es](mailto:headscale-gateway@gentedelcondado.es).
[Manual en línea](https://gente-del-condado.github.io/headscale_gateway_ynh/).

Extrae el ZIP del motor correspondiente a tu arquitectura. En PowerShell como
administrador, ejecuta `./Install-Service.ps1` desde la carpeta extraída. Revisa
el resumen antes de continuar; `-WhatIf` permite comprobar el destino sin cambiarlo.
Si tu política de ejecución bloquea el script, revisa su procedencia y aplica la
política de tu equipo; no se desactiva la protección automáticamente.

Se solicita una cuenta local del panel solo al instalar por primera vez. La
contraseña no aparece en la línea de comandos ni se envía a servicios externos.
El servicio nativo usa LocalService, arranca con Windows y se recupera tras fallo.
El menú Inicio contiene **Headscale Gateway**, que abre la administración local
en el navegador, y un enlace al manual. Gateway-Tray sigue siendo opcional.

Confirma o cambia el nombre propuesto del equipo antes de conectar el nodo.
Headscale asigna el nombre definitivo. El instalador no abre el cortafuegos ni
instala certificados CA. Para cambiar la escucha local posteriormente, actualiza
el contrato de arranque y el acceso directo; conserva una dirección loopback.

Actualizar con el mismo instalador conserva `%ProgramData%/Headscale Gateway`:
SQLite, credenciales, claves y datos. Detiene el servicio antes de sustituir el
ejecutable y vuelve a iniciarlo. Reiniciar desde el panel pasa por el SCM y su
recuperación, sin crear un proceso fuera del servicio. Para retirar el servicio,
detenlo y usa `sc.exe delete HeadscaleGateway`; los datos no se borran con ello.

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
