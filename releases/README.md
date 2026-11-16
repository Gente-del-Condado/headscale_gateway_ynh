# Resultados locales de entrega

Esta carpeta es un destino de trabajo, no una fuente ni un repositorio de
copias. Solo este README está versionado. Los instaladores actuales se obtienen
en [las descargas públicas](https://github.com/Gente-del-Condado/headscale_gateway_releases/releases).

La entrega normal se construye en el compilador público de GitHub desde una
release estable de Forgejo. No prepara ni almacena los adjuntos en YunoHost.
Consulta [Publicación](../docs/PUBLICACION.md).

Para una comprobación local puntual, crea una carpeta nueva en `builds/` y sigue
la guía de la plataforma. No renombres binarios antiguos para aparentar otra
versión: los empaquetadores comprueban versión, origen y sumas.

Los fuentes correspondientes de Electron, Chromium y FFmpeg y sus avisos se
conservan junto a los instaladores distribuidos. Una copia histórica que debas
mantener se guarda fuera del árbol de desarrollo, en un archivo protegido.
Las claves de firma y los datos de instalaciones nunca se guardan aquí.

Preparar, compilar o crear un commit local no autoriza publicar. Si se pide
preparar sin subir, no se crean etiquetas, releases ni cambios remotos.
