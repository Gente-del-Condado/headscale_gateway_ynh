# 1.4.14

- Dominio principal destacado y enlaces directos HTTP/HTTPS en Resumen/Estado del panel común.
- Conserva el foco al refrescar el estado; Android abre también los enlaces HTTP LAN mediante un toque explícito.
- README y manuales distinguen portal de servicios, administración y servidor Headscale; las versiones documentales Android y Play se verifican automáticamente.

# 1.4.13

- Certificados: conserva CertMagic y DNS-01 sin cargar el servidor Caddy; mantiene TXT ajenos y protege los tokens en errores de ACME.
- Confirmación del nombre propuesto antes del primer registro en Headscale, con identidad conservada al actualizar.
- Limpieza DNS al caducar o eliminar nodos, con avisos separados si falla el proveedor.
- Autor, soporte y manual unificados; servicios nativos y accesos del escritorio mejorados.

# 1.4.12

- Android cierra explícitamente el adaptador VPN aunque el sistema mantenga
  enlazado VpnService. Desconectar aplicaciones conserva el motor del Gateway.
- Estado de desconexión visible y espera nativa acotada; permite reconectar.
- Conserva las correcciones de presentación y el registro PKI de 1.4.10/1.4.11.

# 1.4.11

- Descubrimiento y descarga de CA como registro de estados con colores y detalles
  técnicos desplegables; resumen y progreso junto a los botones.
- Distingue un Gateway registrado o con CA disponible de un nodo sin confirmar.
  Un puerto cerrado o un timeout no demuestran que el nodo no ejecute Gateway.
- Evita búsquedas y descargas simultáneas y conserva la aprobación manual.
- Incluye las correcciones de los indicadores Android, LAN y fechas de 1.4.10.

## 1.4.10

- La descarga de CA informa de éxitos y errores e indica cómo revisar un HTTP 404.

- El resumen distingue un cortafuegos sin comprobar de una regla LAN ausente.
- CA y confianza no muestra una fecha ficticia cuando aún no hay verificación.
- Android consulta su propio proceso VPN mediante las API del sistema; conserva
  la firma y los datos al actualizar.

# 1.4.9

- Publicación completa desde releases estables de Forgejo, con compilación y comprobaciones en GitHub.
- Descargas públicas del motor y la bandeja, paquetes Debian/Fedora y Flatpak del Gateway completo.
- Android conserva su firma estable; APK directo, APK F-Droid sin firma y AAB de Play preparado.
- Guías de instalación y publicación actualizadas. Las entregas anteriores conservan sus archivos y etiquetas.

# 1.4.8

- Guías y enlaces actualizados a los repositorios actuales.
- Documentadas las publicaciones directas desde GitHub tras las pruebas y la separación entre servidor e integración.
- Nueva entrega con los fuentes y avisos correspondientes, sin modificar las anteriores.

# 1.4.7

- Versión común del motor, complemento, paquete YunoHost y clientes de escritorio y Android.
- Documentación de instalación, privacidad, firmas y canales actualizada en ambos manuales públicos.
- Preparación del catálogo YunoHost y publicación de los fuentes completos sin historial privado.
- Se conservan los controles de seguridad previos a la publicación automática en Mis_app_ha.

# 1.4.6

- Actualización de Caddy a 2.11.5, go-jose a 4.1.6 y QUIC a 0.63.0 para corregir las alertas de seguridad de sus dependencias.
- Actualización de glob y minimatch en las herramientas de empaquetado de la bandeja.
- Compilación con Go 1.27.4 y actualización de x/net y compress para incorporar correcciones de HTTP, TLS y compresión.
- Renovación del inventario y los avisos de licencia de las dependencias actualizadas.

# 1.4.5

- Envío y recuperación manual de perfiles y copias cifradas en repositorios privados de Forgejo.
- Icono y logotipo del complemento en la tienda de Home Assistant.
- Publicación automática del complemento en Mis_app_ha a partir de la rama principal.

# 1.4.4

- Guías de instalación independientes de otros proyectos.
- Direcciones SSH ficticias en los ejemplos, con instrucciones para sustituirlas por las del repositorio propio.

# 1.4.3

- Corrección del enlace «Abrir interfaz web»: la ruta de entrada es relativa a Ingress.
- Se evita la doble barra que redirigía a `/admin/` fuera de Home Assistant y podía producir un 404.
- La prueba de contenedor construye el enlace desde el manifiesto y comprueba el recorrido por un proxy simulado.

# 1.4.2

- Corrección del arranque: la API de Supervisor no devuelve el campo `panel_admin`.
- La opción `ingress_panel` solo controla la barra lateral y no bloquea el arranque si está desactivada.
- Se conserva la verificación del administrador, del proxy y de CSRF en cada petición.
- Pruebas actualizadas para reproducir la respuesta real de Supervisor.

# 1.4.1

- Documentación de instalación, uso, actualización y recuperación en español.
- Guías de Home Assistant, YunoHost e integración de entidades unificadas con el repositorio privado.
- Descripción predeterminada del complemento en español, sin cambios funcionales.

# 1.4.0

- Motor común de sesiones delegadas para Home Assistant y el portal de YunoHost.
- Prueba privada del proxy obligatoria al delegar autenticación por loopback.
- Se conservan la sesión administradora de Ingress y la protección CSRF.

# 1.3.0

- Acceso directo desde Ingress con la sesión administradora de Home Assistant.
- Verificación del proxy, del identificador de usuario y del grupo administrador en cada petición.
- Protección CSRF sin crear una cookie de acceso reutilizable fuera de Ingress.
- Cuenta inicial opcional reservada al acceso directo.

# 1.2.1

- Instrucciones de acceso al panel y a la barra lateral al arrancar en Home Assistant.
- El puerto interno reservado al proxy deja de anunciarse como enlace para el navegador.
- Comprobación del panel incrustado, los recursos, la cuenta inicial y las sesiones mediante Ingress.

# 1.2.0

- Un único servidor HTTP, registro de rutas, contrato de arranque y autenticación.
- Inicialización compartida por los instaladores, sin seleccionar una variante de la aplicación.
- Versión común y estructura estándar de integración HACS en el repositorio principal.
- Conservación de la identidad VPN en las instalaciones y migraciones.

# 1.1.0

- Primer empaquetado experimental para Home Assistant OS.
