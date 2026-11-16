# Cambios de Headscale Gateway

## 1.4.16 — preparada, sin publicar

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
