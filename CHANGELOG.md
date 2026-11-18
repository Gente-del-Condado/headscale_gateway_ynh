# Cambios de Headscale Gateway

## 1.4.18

- Perfil AppArmor propio para el complemento Home Assistant, en modo estricto,
  con clasificación 7/8 comprobada en HAOS amd64 y aarch64 emulado.
- Restringe ejecución y escritura a los programas y directorios necesarios;
  conserva red LAN, multicast, Ingress, VPN, certificados y datos del Gateway.
- Desactiva la caché de Python sobre los programas de solo lectura.
- Añade aceptación repetible de AppArmor, SSO/CSRF, copias y exportación;
  documenta conservación de claves y opciones tras reiniciar y apagar/encender.
- La guía de Home Assistant consulta el puerto web real de cada instalación.
- Conserva firma Android, licencias y reutilización de fuentes Electron.
  Play Store continúa solo preparado; no se envía ninguna aplicación a la tienda.


## 1.4.17

- Publicación de mantenimiento: conserva el motor y la firma Android existentes.
- Separa los fuentes de Electron de los instaladores y reutiliza el conjunto verificado por lock.
- Actualiza versiones de todos los paquetes y las guías de descarga.

### Comprobación de reutilización y guía de descargas

- Ensayo de una siguiente entrega que no publica versiones ni mezcla archivos de Electron.
- Comprobación pública sin credenciales que omite preparar y subir conjuntos existentes.
- README y manuales vigentes distinguen instaladores, fuentes propios y dependencias.

### Mantenimiento del publicador después de 1.4.16

- Fuentes de Electron y dependencias en una release reutilizable por lock.
- Los instaladores nuevos enlazan los fuentes exactos sin duplicar los archivos grandes.
- Se conservan todos los adjuntos, firmas y URL de la 1.4.16.

## 1.4.16 — publicada

- Corrige la validación de rutas del controlador Headscale en clientes y pruebas
  Windows: el contrato del actuador Linux utiliza siempre rutas POSIX.
- Añade regresión multiplataforma que mantiene el rechazo de rutas inseguras.
- Simplifica la automatización: retira publicadores privados desactivados y el
  publicador antiguo de Forgejo; conserva el compilador público y sus barreras.
- Revisa las guías de desarrollo, agentes, privacidad, paquetes y manual web.
- Añade comprobación de privacidad al flujo de verificación local y documenta
  la limpieza, la firma Android externa y los límites reales de la validación.

## 1.4.15 — origen publicado, distribución bloqueada

- Incorpora al motor Go y al panel compartido la gestión del coordinador Headscale:
  DNS global/dividido, MagicDNS, búsqueda, registros adicionales y restricciones OIDC.
- Añade observación de nodos y delegación TLS de lectura o escritura limitada.
- Separa el actuador privilegiado Linux del usuario del portal; aplica revisión
  previa, control de cambios y recuperación.
- Conserva las funciones existentes, la configuración, los secretos y la identidad.
- El trabajo Windows de GitHub bloqueó la distribución; lo corrige la 1.4.16.

Las versiones anteriores y sus cambios originales se conservan en las etiquetas
Git y las notas de sus releases. La versión declarada no demuestra por sí sola
que todos sus instaladores se hayan publicado: consulta sus comprobaciones.
