# Protecciones por plataforma

El motor Go y el panel mantienen las mismas funciones. Cada paquete aplica el
confinamiento de su sistema; una puntuación AppArmor de Home Assistant no se
traslada a Android o Linux ni acredita por sí sola la seguridad del producto.

## Debian, Fedora y YunoHost

El portal usa una cuenta sin privilegios, permisos privados y un sistema de
archivos de solo lectura salvo sus datos y temporales. systemd elimina sus
capacidades y bloquea nuevos namespaces, memoria simultáneamente escribible y
ejecutable, montaje, depuración y operaciones de administración del núcleo.
Oculta procesos de otros usuarios y protege reloj y nombre del anfitrión.

Se conservan sockets Unix, IPv4, IPv6 y netlink para detectar interfaces,
resolver nombres y comunicarse con el actuador. tsnet funciona en espacio de
usuario; el portal no necesita NET_ADMIN ni acceso al dispositivo TUN.
YunoHost mantiene visible `/home/yunohost.app` en modo de solo lectura y permite
escribir únicamente en los datos de esta aplicación. NSS y el grupo `admins`
siguen formando parte de la validación SSO.

El actuador opcional que administra Headscale pertenece al administrador del
anfitrión y usa otra unidad. No se le aplican a ciegas las capacidades vacías del
portal: debe poder comprobar propietarios y ejecutar Headscale con su usuario.
En Fedora no se desactiva SELinux ni se instala una política permisiva. Este
cambio refuerza systemd; no introduce un dominio SELinux propio.

## Android

El sistema conserva el aislamiento de la aplicación, Android Keystore y los
archivos privados sin copia automática. La firma y las rutas de datos no cambian.
El WebView impide acceso a archivos locales, contenido mixto y errores TLS.
Los enlaces externos se abren en el navegador; importar y exportar usa el selector
de documentos y permisos concedidos por el usuario.

El puente de descargas no acepta un origen declarado como credencial. Solo el
documento superior del panel local recibe una capacidad aleatoria encerrada en
una función JavaScript, sin exponerla en `window`, HTML ni almacenamiento web.
La navegación la revoca y cancela transferencias incompletas. Cada transferencia
requiere además su propio identificador. Una exportación terminada pendiente de
guardar conserva su mecanismo de recuperación. Esto no sustituye las defensas
contra XSS ni concede acceso adicional a la API.

## Flatpak

El manifiesto conserva únicamente `--share=network`: no accede al hogar, SSH,
archivos del anfitrión, TUN ni bus de sistema. Los archivos elegidos pasan por
portales. El acceso de red es necesario para VPN, DNS, ACME y servicios LAN;
también comparte el espacio de red del anfitrión y no equivale a aislar sockets
abstractos Unix. No se solicita `flatpak-spawn --host`.

La comprobación del panel loopback ignora proxies del entorno y no sigue
redirecciones. Se conservan datos privados, bloqueo de instancia, reintentos y
solicitud explícita de permiso de segundo plano. Las restricciones no autorizan
instalar certificados en el almacén del anfitrión.

## Repetir las comprobaciones

Con un binario de pruebas compilado desde `src/`:

```sh
CGO_ENABLED=0 go -C src test -c -o /tmp/gateway.test .
sudo python3 tools/test_systemd_hardening.py --confirm-disposable-lab \
  --template packaging/yunohost/conf/systemd.service --tests /tmp/gateway.test
```

Utiliza únicamente una VM de laboratorio. La herramienta crea una unidad y datos
temporales propios, comprueba rechazos reales, SQLite WAL, NSS, TLS y sockets y
corre pruebas Go de certificados, DNS y restauración. Retira su unidad y datos al
terminar. La variante `--user --lab-root "$PWD/builds"` valida restricciones de
una sesión Fedora con `PrivateUsers`; no equivale a instalar un servicio de
sistema con RPM. Consulta [pruebas Android](ANDROID.md) y la
[validación de la entrega](VERIFICACION_FINAL.md) para resultados y límites.
