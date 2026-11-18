# Aplicaciones de Gente del Condado

![Icono del catálogo](icon.png)

Mi repositorio oficial de aplicaciones para Home Assistant.

[![Añadir a Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FGente-del-Condado%2FMis_app_ha)

[Manual del gestor](https://gente-del-condado.github.io/HA-Private-Git-Manager/) · [Catálogo de integraciones y Forgejo Backup](https://gente-del-condado.github.io/HA-Private-Git-Manager/#componentes)

## Instalación

Pulsa el botón anterior o añade este repositorio desde **Ajustes → Aplicaciones →
Tienda → menú ⋮ → Repositorios**:

```text
https://github.com/Gente-del-Condado/Mis_app_ha
```

Después selecciona la aplicación y sigue su documentación. **JackSignal Installer** se inicia una vez para copiar la integración y se detiene; después debes reiniciar Home Assistant. Las aplicaciones con interfaz web se abren desde su ficha.
La tienda descarga imágenes precompiladas desde GHCR para `amd64` y `aarch64`;
la instalación requiere conexión a Internet. Home Assistant puede mostrar el
progreso de descarga que ofrece Supervisor. JackSignal sigue siendo un instalador
que se ejecuta una vez: no es un servidor permanente.

## Aplicaciones

| Aplicación | Descripción | Arquitecturas |
| --- | --- | --- |
| [JackSignal Installer](jacksignal_installer/README.md) | Instala JackSignal: avisos de Alarmo, apertura/cierre, voz de sensores sin YAML y DLNA solo de audio con prioridades. | `amd64`, `aarch64` |
| [HA Private Git Manager](private_git_manager/README.md) | Gestiona claves SSH y aplicaciones de repositorios GitHub, Forgejo y Gitea desde Home Assistant. | `amd64`, `aarch64` |
| [PiVigia](pivigia/README.md) | Analiza localmente fotos de cámaras recibidas por SMTP y envía avisos por correo o Telegram; incluye RTSP opcional. | `amd64`, `aarch64` |
| [Headscale Gateway](headscale_gateway/README.md) | Ejecuta y administra Headscale Gateway en Home Assistant. | `amd64`, `aarch64` |

[Guía de uso](private_git_manager/DOCS.md) · [Historial de versiones](private_git_manager/CHANGELOG.md)

La integración opcional de sensores de PiVigia para
Home Assistant se instala por separado. Si ya utilizas PiVigia desde otro
repositorio o una carpeta local, añadir esta tienda no migra sus datos ni sustituye
automáticamente aquella instalación.

## Origen y actualizaciones

Los cuatro proyectos se desarrollan primero en Forgejo. GitHub recibe sus
espejos. Los publicadores y las comprobaciones públicas preparan las aplicaciones
en `build-source`; las imágenes se prueban antes de incorporarlas a `main`.
No hay una copia de esta tienda en Forgejo ni sincronización de regreso.

| Aplicación | Origen Forgejo | Espejo GitHub | Carpeta publicada |
| --- | --- | --- | --- |
| Headscale Gateway | [Forgejo](https://gentedelcondado.es/forgejo/wolfbelmi88/headscale_gateway) | [GitHub](https://github.com/Gente-del-Condado/headscale_gateway) | `headscale_gateway/` |
| PiVigia | [Forgejo](https://gentedelcondado.es/forgejo/wolfbelmi88/pivigia) | [GitHub](https://github.com/Gente-del-Condado/pivigia) | `pivigia/` |
| JackSignal | [Forgejo](https://gentedelcondado.es/forgejo/wolfbelmi88/jacksignal) | [GitHub](https://github.com/Gente-del-Condado/jacksignal) | `jacksignal_installer/` |
| Private Git Manager | [Forgejo](https://gentedelcondado.es/forgejo/wolfbelmi88/HA-Private-Git-Manager) | [GitHub](https://github.com/Gente-del-Condado/HA-Private-Git-Manager) | `private_git_manager/` |

Headscale Gateway se prepara desde su release estable de Forgejo. PiVigia y
JackSignal se comprueban desde un SHA exacto de main de Forgejo en runners
públicos de esta tienda, cada hora; sus espejos privados conservan el código.
Private Git Manager mantiene su publicador por cambios en main de GitHub. Los principales de los tres primeros son privados;
la distribución instalable es pública. Los commits de publicación identifican
la revisión de origen. Cada publicador conserva los demás proyectos.

No edites las carpetas generadas: corrige la fuente en el principal de Forgejo.
La publicación no instala automáticamente las actualizaciones en los equipos.

## Imágenes y comprobaciones

[Construcción y pruebas](https://github.com/Gente-del-Condado/Mis_app_ha/actions) ·
[Detalles del controlador](.github/ha-images/README.md).

Cada aplicación tiene una imagen multi arquitectura, con la misma versión que su
`config.yaml`. La tienda solo añade `image:` tras pasar las pruebas nativas de
amd64 y aarch64 y comprobar la descarga sin usuario ni token. Los Dockerfile se
conservan como fuentes; no es necesario compilarlos durante la instalación desde
esta tienda. Las carpetas locales copiadas manualmente siguen su propio recorrido.

| Aplicación | Imagen pública |
| --- | --- |
| Headscale Gateway | `ghcr.io/gente-del-condado/ha-headscale-gateway` |
| JackSignal Installer | `ghcr.io/gente-del-condado/ha-jacksignal-installer` |
| PiVigia | `ghcr.io/gente-del-condado/ha-pivigia` |
| Private Git Manager | `ghcr.io/gente-del-condado/ha-private-git-manager` |

`.images/` registra versiones, fuentes y digests. Si una compilación, prueba o
verificación pública falla, permanece disponible la versión anterior de main.
Las etiquetas ya distribuidas no se reemplazan: los cambios requieren una versión
nueva. Se conservan slugs, opciones, volúmenes y permisos; la primera migración a
imágenes no fuerza actualizaciones ni reinstalaciones en equipos existentes.

El recorrido público de PiVigia y JackSignal entrega también las integraciones
a sus repositorios dedicados y a Mis_componente_ha. El plan evita descargar y
comprobar de nuevo un SHA ya publicado. Un fallo de imágenes queda pendiente
para reintento; un fallo de distribución no se marca como una entrega completa.
Las credenciales de publicación no se entregan a las pruebas ni a los exportadores.
