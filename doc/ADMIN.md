# Headscale Gateway para YunoHost

Compatible con YunoHost 12.1.17 o posterior, en amd64 y arm64. Incluye
instalación en la raíz o en una subruta, varias instancias, panel HTTPS mediante
nginx, servicio systemd, actualización, cambio de URL, copias y restauración.
Necesita un servidor Headscale existente.

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

## Preparación

Ten a mano la URL de Headscale, las credenciales del nodo y un dominio para
los servicios privados. El dominio del portal YunoHost puede ser diferente.
Selecciona el dominio y la ruta del panel al instalar; comprueba que su HTTPS
funciona antes de configurar la VPN. Utiliza una cuenta del grupo `admins`.

Hay dos carpetas diferentes en el proyecto: `packaging/yunohost/` contiene
las plantillas que edita el desarrollador y `yunohost/` es el paquete instalable.
Las actualizaciones deben conservar la carpeta de datos de cada instancia.

## Instalar desde el repositorio público

El [repositorio del paquete](https://github.com/Gente-del-Condado/headscale_gateway_ynh)
contiene el manifiesto en la raíz y descarga recursos para ambas arquitecturas
desde una release pública, con SHA-256 fijado por versión.
No necesitas acceso al repositorio privado del motor:

```bash
sudo yunohost app install https://github.com/Gente-del-Condado/headscale_gateway_ynh
```

Es un paquete independiente mantenido para su uso desde esta URL. No se solicitará
su inclusión en el catálogo oficial. Consulta el estado de validación al final.

## Alternativa de desarrollo desde el repositorio privado

Clona el proyecto desde Forgejo e instala la carpeta `yunohost/`, que ya incluye
los binarios y sus sumas SHA-256 para ambas arquitecturas. El instalador utiliza
igualmente los recursos públicos declarados en el manifiesto:

La dirección SSH del ejemplo es ficticia: sustitúyela por la URL SSH de tu
repositorio, con su usuario SSH, servidor, puerto y propietario reales.

```bash
git clone ssh://git@forgejo.example.net:2222/usuario/headscale-gateway.git "$HOME/headscale-gateway-src"
sudo yunohost app install "$HOME/headscale-gateway-src/yunohost"
```

La clave SSH se configura en el usuario que clona el repositorio. YunoHost
instala desde esa carpeta local, sin necesitar su propio acceso Git a Forgejo.
Consulta `docs/INSTALACION_PRIVADA.md` en el repositorio para el procedimiento
completo.

`packaging/yunohost/` contiene las plantillas, sin los binarios. No se instala
directamente. Para mantener los paquetes, ejecuta en el PC de desarrollo
`python3 tools/prepare_git_install.py` y sube los archivos generados a la misma
rama del repositorio.

## Entrar desde el portal

El paquete incluye el icono cuadrado del proyecto en `doc/logo.png` y lo registra
como logo de la aplicación en administración y portal. La revisión `1.4.6~ynh2`
lo incorpora también al actualizar una instalación anterior. Un logo
personalizado ya configurado se conserva.

Abre **Headscale Gateway** desde el portal de YunoHost con una cuenta del grupo
real `admins`. Entrarás directamente, sin otra contraseña del Gateway.

Se necesita SSOwat 12.1.1 o posterior. SSOwat transmite la identidad verificada
`YNH_USER` y el Gateway comprueba la pertenencia al grupo mediante el sistema
NSS del anfitrión (`getent group admins`) en cada petición. Un usuario normal
del portal no obtiene permisos administrativos aunque se amplíe por error el
permiso de acceso a la aplicación.

Una prueba privada entre nginx y cada instancia impide falsificar la identidad
con una petición local al puerto loopback. El archivo `*-proxy-auth.inc` es
propiedad de root y tiene permisos 0600; el secreto equivalente del arranque
es privado y no se envía al navegador. Se mantiene CSRF y no se crea una cookie
del Gateway reutilizable fuera del portal.

El portal gestiona el inicio y cierre de sesión y su segundo factor de
autenticación. Las cuentas, contraseñas y MFA existentes del Gateway se
conservan para acceso directo. La instalación no solicita otra contraseña.
Puedes configurar las credenciales de acceso directo en **Acceso / Identidad**.

## Primera configuración

1. Abre la aplicación desde el portal y comprueba el acceso al panel.
2. Introduce la URL de Headscale, las credenciales requeridas y un nombre de
   nodo estable. Configura el dominio base y tu proveedor DNS.
3. Aplica la configuración y comprueba el estado de la conexión VPN.
4. Añade un servicio de laboratorio con un backend accesible desde el servidor,
   por ejemplo `http://127.0.0.1:8080` si esa aplicación escucha allí.
5. Abre la URL publicada desde un cliente VPN autorizado. La CA local debe ser
   confiable en ese cliente; alternativamente configura ACME.
6. Crea una copia de seguridad y conserva una forma de recuperación antes de
   publicar servicios que utilices habitualmente.

El acceso al panel desde el portal no demuestra por sí solo que el servicio
publicado sea accesible por VPN: comprueba ambos recorridos.

## Actualizar

Si instalaste desde el repositorio público:

```bash
sudo yunohost app upgrade headscale_gateway --url https://github.com/Gente-del-Condado/headscale_gateway_ynh
```

Si utilizas el clon privado de desarrollo:

```bash
git -C "$HOME/headscale-gateway-src" pull --ff-only &&
sudo yunohost app upgrade headscale_gateway --file "$HOME/headscale-gateway-src/yunohost"
```

Para otra instancia, sustituye `headscale_gateway` por su identificador real,
como `headscale_gateway__2`. Mantén la copia de seguridad automática de YunoHost.
No reemplaces a mano el ejecutable del servicio.

El paquete se desarrolla en el principal privado de Forgejo, que se replica
al espejo privado de GitHub. El compilador público `headscale_gateway_releases`
lee una release estable de Forgejo, comprueba seguridad y plataformas y publica
exclusivamente el paquete YunoHost en `headscale_gateway_ynh`, junto a sus recursos
públicos. No existe un derivado YunoHost en Forgejo ni se escribe de vuelta allí.
Edita `packaging/yunohost/` del principal y regenera `yunohost/`; no edites la
copia pública. Publicar el repositorio no actualiza tu servidor: realiza la
actualización desde YunoHost cuando corresponda.

Después de actualizar, abre el panel, revisa la versión, prueba un servicio y
comprueba que conserva su identidad VPN. Si aparece un error, consulta el
registro de la operación YunoHost antes de intentar una reinstalación.

## Red

El paquete no abre un nuevo puerto público de entrada. El servicio HTTPS LAN
comienza en loopback y el puerto 443 de tsnet pertenece a la identidad VPN
independiente del Gateway. Para publicar servicios en la LAN, configura el
puerto del Gateway y las reglas del anfitrión sin sustituir los puertos 80/443
de nginx. El descubrimiento por multidifusión requiere conectividad LAN.

El dominio HTTPS de YunoHost y el dominio privado de los servicios del Gateway
son ajustes independientes.

## Datos, copias y restauración

Los datos persistentes están en `$data_dir/gateway/`. El directorio padre
permanece escribible para poder sustituir la subcarpeta durante una restauración
completa. Las copias detienen el servicio para conservar juntos SQLite,
`master.key`, certificados e identidad tsnet. También incluyen la configuración
privada de nginx y el secreto de arranque que le corresponde. La captura con el
servicio detenido es específica del Gateway: las declaraciones `ynh_backup`
se ejecutan después del script y por sí solas no congelan SQLite mientras está parado.

Protege las copias, porque contienen credenciales. No ejecutes una identidad
restaurada al mismo tiempo que el nodo original. La desinstalación conserva
los datos salvo que solicites su eliminación mediante la opción de purga.

## Cambiar la dirección web

Cambiar la URL de YunoHost solo cambia el acceso administrativo, no la identidad
VPN ni el dominio privado. Los archivos privados del proxy se mantienen
sincronizados. La ruta administrativa admite letras, números, guiones y guiones
bajos.

Si utilizas OIDC para el acceso directo, actualiza el callback en el proveedor
y en el Gateway a `https://dominio/ruta/admin/auth/oidc/callback`.

## Recuperación

Utiliza primero una cuenta administradora del portal. Para recuperar el acceso
propio del Gateway en una emergencia, detén el servicio y ejecuta el binario
con el usuario Unix de la aplicación, la misma ruta `--db` y `--reset-recovery`.
Vuelve a iniciarlo en una terminal interactiva para obtener el código de un
solo uso, completa la recuperación y arranca otra vez el servicio normal.
No abras la misma base de datos con dos procesos a la vez.

## Estado de validación

Se utilizan el linter y `package_check` oficiales en una VM desechable amd64.
El historial y los resultados por revisión están en
[mantenimiento y validación](CATALOGO.md). Las pruebas SSO verifican la API
protegida además del HTML. No se atribuye una prueba real arm64 a la compilación
de su binario. El nivel del catálogo no certifica este paquete independiente.
Se conservan la licencia del proyecto y los avisos legales originales de terceros.

## Diagnóstico rápido

| Síntoma | Comprobación |
| --- | --- |
| Acceso denegado desde el portal | Pertenencia real a `admins`, versión de SSOwat y consulta NSS |
| 502 al abrir la aplicación | Estado del servicio de la instancia y registro de nginx |
| El servicio publicado falla, pero el panel abre | Conectividad del backend, DNS privado, VPN y ACL |
| Error después de cambiar URL | URL del portal actual, configuración nginx y callback OIDC si se usa |
| Copia o restauración fallida | Registro YunoHost, espacio disponible y permisos de la carpeta de datos |

Para una instancia llamada `headscale_gateway`, consulta el proceso sin cambiarlo:

```bash
sudo systemctl status headscale_gateway --no-pager
sudo journalctl -u headscale_gateway -n 80 --no-pager
```

Sustituye el nombre por el identificador real si hay varias instancias.
Comparte solo el fragmento relevante del error, revisado para excluir secretos.

## Licencia y fuentes

El código propio es software libre bajo **AGPL-3.0-only**. La revisión
`1.4.6~ynh3` incorpora esta licencia y las fuentes del motor en
`sources/source.tar.gz` del directorio instalado, con `SOURCE.md` e instrucciones
de compilación. Se conservan también en la release pública del motor.
`build-manifest.json` registra las sumas de cada archivo. Las licencias de
terceros se conservan en `doc/third_party/` del repositorio y `notices/` de la instalación.

## Autor, soporte y nombre del nodo

Autor: **Gente del Condado**. Soporte:
[headscale-gateway@gentedelcondado.es](mailto:headscale-gateway@gentedelcondado.es).
[Manual en línea](https://gente-del-condado.github.io/headscale_gateway_ynh/).
En una instalación nueva, el panel común pide confirmar o editar el nombre
propuesto antes de conectar a Headscale. La propuesta del instalador no sustituye
esa elección. Headscale asigna el nombre definitivo y resuelve duplicados. Las
actualizaciones conservan el nombre, la identidad, las credenciales y los datos.

## Administración del coordinador Headscale

El motor y el portal comunes incluyen DNS de la Tailnet, restricciones OIDC y
observador de nodos. Para controlar el Headscale del mismo anfitrión, un
administrador debe registrar el ayudante mediante `conf/setup-headscale` del
paquete, con instancia `ynh-IDENTIFICADOR_APP` y las unidades y rutas reales.
El portal conserva su cuenta sin privilegios. Las actualizaciones refrescan el
motor protegido de un controlador ya registrado; las copias no conceden este
privilegio en un anfitrión nuevo. Otros Gateway pueden utilizar una delegación
HTTPS explícita de lectura o escritura. No cambia el DNS-01 ni los certificados
de los servicios. Sigue el [manual del controlador](https://gente-del-condado.github.io/headscale_gateway_ynh/CONTROL_HEADSCALE.html).
