# Estado de desarrollo y siguiente entrega

## 1.4.16: preparación local

Esta revisión prepara la continuidad del proyecto y corrige el fallo de Windows
que bloqueó la entrega 1.4.15. **No está autorizada su subida ni publicación**.
No se ha creado una etiqueta o release 1.4.16 ni se han cambiado las tiendas,
los repositorios de distribución o las páginas públicas.

Incluye:

- Contrato de rutas del controlador Linux validado como POSIX también desde
  Windows; pruebas de regresión sin omitir esa plataforma.
- Retirada de workflows privados desactivados y del publicador antiguo de
  Forgejo. El compilador público sigue siendo el único publicador.
- Guía inicial para un desarrollador nuevo, instrucciones de agentes actualizadas,
  mapa de fuentes, README de paquetes y flujo de publicación coherentes.
- Comprobación local de privacidad integrada en `tools/verify.sh` y reglas de
  Gitleaks que distinguen las sumas de los manifiestos de las credenciales.
- Retirada de laboratorios, cachés y entregas antiguas del árbol de trabajo.
  Los originales y diagnósticos privados se conservan fuera del proyecto;
  la firma estable Android y el historial Git permanecen intactos.

Las comprobaciones locales completadas se registran en
[Validación](VERIFICACION_FINAL.md): motor y suites generales, auditorías Go/npm,
Windows bajo Wine, paquetes, exportación y manual estricto. Los informes completos de mantenimiento son
locales y no se publican si contienen datos de instalaciones.

## Situación de 1.4.15

La etiqueta estable de Forgejo y el espejo GitHub contienen los cambios del
motor común: DNS de la Tailnet, restricciones OIDC, observador y control local
o delegado de Headscale. La publicación de instaladores quedó bloqueada por
[el fallo del trabajo Windows](https://github.com/Gente-del-Condado/headscale_gateway_releases/actions/runs/43784256540/job/133056107526).
No se presenta aquella ejecución como una distribución completada.

La causa era `filepath.Join` y `filepath.IsAbs` aplicando reglas Windows a las
rutas del actuador Linux. La 1.4.16 utiliza el contrato POSIX del destino y sigue
rechazando rutas relativas, ambiguas, Windows y caracteres de control.

La APK 1.4.15 se compiló con la firma existente y se instaló en la tablet. La
prueba posterior de instalación limpia y conexión entre la tablet y la VM se
**detuvo por petición del usuario**. En esa VM se instalaron Dex y Headscale;
la configuración nueva del Gateway, Technitium y la integración Dex adicional
no quedaron completadas. No se reanudan por el hecho de continuar el desarrollo.

## Qué debe hacer el siguiente mantenedor

1. Leer este estado, `AGENTS.md`, la guía inicial y `git status`; no asumir que
   una rama o una versión local ya está publicada.
2. Repetir las comprobaciones del cambio que vaya a realizar. No hace falta una
   VM ni credenciales productivas para modificar la documentación o ejecutar Go.
3. Para retomar las pruebas detenidas, acordar expresamente el alcance y utilizar
   identidades aisladas. No cambiar recursos de VM ni importar claves productivas.
4. Publicar 1.4.16 únicamente cuando el usuario lo pida; entonces seguir
   [PUBLICACION.md](PUBLICACION.md), comprobar réplica y CI y no mover la etiqueta 1.4.15.

La autenticación OIDC del Gateway y las restricciones OIDC de Headscale son
funciones distintas. Configurar el laboratorio Dex/Technitium no es una
condición para ejecutar el motor común ni una función ya validada en esta entrega.
