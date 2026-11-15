# Editar y publicar el manual web

El manual se genera con MkDocs a partir de Markdown. Los textos se pueden leer
en Forgejo, GitHub o un editor. El resultado es una carpeta HTML estática con
navegación, búsqueda y capturas. Sus recursos se sirven desde la misma carpeta.

## Preparar el entorno

Desde la raíz del proyecto, crea un entorno virtual en la carpeta de resultados.

```bash
python3 -m venv builds/docs-env
builds/docs-env/bin/python -m pip install -r requirements-docs.txt
builds/docs-env/bin/python -m mkdocs build --strict
python3 tools/check_manual.py builds/manual
```

En Windows, el ejecutable del entorno es `builds\docs-env\Scripts\python.exe`.
La versión de MkDocs está fijada en `requirements-docs.txt`. Las dependencias de
la documentación se instalan en ese entorno independiente.

Abre `builds/manual/index.html` en el navegador. Para revisar cambios en vivo,
arranca el servidor local de MkDocs.

```bash
builds/docs-env/bin/python -m mkdocs serve --dev-addr 127.0.0.1:8000
```

Visita `http://127.0.0.1:8000/`. Usa Ctrl+C para detener el servidor. La web también
se puede copiar completa a cualquier alojamiento estático, incluso bajo una
subruta. La búsqueda utiliza un índice local y funciona al abrir los HTML.

## Dónde editar cada cosa

| Cambio | Archivo fuente |
| --- | --- |
| Portada y recorrido de inicio | `docs/index.md`, `docs/PRIMEROS_PASOS.md` |
| Manual funcional | `docs/USO_COMPLETO.md` y guías específicas de `docs/` |
| Complemento Home Assistant | `packaging/homeassistant/DOCS.md` |
| Integración de entidades | `packaging/hacs/README.md` |
| YunoHost | `packaging/yunohost/doc/ADMIN.md` y `doc/` |
| Android | `android/README.md`, `docs/ANDROID.md` |
| Mapa y orden del menú | `mkdocs.yml` |
| Colores, espacios y adaptación móvil | `tools/manual_theme/assets/manual.css` |
| Plantilla HTML | `tools/manual_theme/main.html` |
| Búsqueda y menú móvil | `tools/manual_theme/assets/manual.js` |
| Incorporación de fuentes e índice | `tools/manual_hooks.py` |
| Guía para programadores e IA | `CONTRIBUTING.md`, `AGENTS.md` |

Las páginas virtuales de plataforma se crean durante la compilación. La web y
el paquete instalado toman su contenido de la misma fuente. Los TXT utilizados
por los paquetes se presentan también como páginas navegables.

Al añadir una guía, crea el Markdown, incorpora su entrada a `nav` en
`mkdocs.yml` y enlázala desde el recorrido correspondiente. Usa enlaces relativos,
textos alternativos en las imágenes y un solo título de primer nivel por página.
Las capturas se mantienen según [CAPTURAS.md](CAPTURAS.md).

## GitHub Pages

El principal privado `headscale_gateway` de Forgejo se replica al principal
privado de GitHub. Después de superar **Calidad multiplataforma**, **Manual web**
construye el HTML, comprueba sus enlaces y lo publica directamente en `gh-pages`
de los dos repositorios públicos:

- [Manual YunoHost](https://gente-del-condado.github.io/headscale_gateway_ynh/).
- [Manual Home Assistant](https://gente-del-condado.github.io/headscale_gateway_ha/).

Ambas webs contienen el mismo manual. En cada destino, **Settings → Pages**
debe publicar desde la rama `gh-pages`, carpeta `/`. El principal no necesita
Pages ni permisos `pages: write` o `id-token: write`. Tampoco utiliza las antiguas
claves de escritura en Forgejo ni las variables `PUBLISH_DOCS` y
`PUBLISH_PUBLIC_DOCS`. La credencial es `PUBLICATION_TOKEN`, limitada a Contents
en las distribuciones públicas; consulta [Publicación](PUBLICACION.md).

Los pull requests solo construyen y comprueban el manual, sin acceder a esa
credencial. La publicación toma el SHA que superó las pruebas y descarta
revisiones que ya no sean main al comenzar. Conserva el historial de gh-pages;
no modifica la rama del paquete ni incluye el historial privado.

Al renombrar repositorios, actualiza los enlaces a Pages: GitHub no redirige
los sitios de proyecto aunque sí redirija la URL del repositorio.

## Alojarlo junto a Forgejo

El mismo resultado se puede servir desde un directorio estático configurado por
el administrador del servidor. Primero ejecuta la compilación y comprueba la
carpeta `builds/manual/`. Publica su contenido conservando las rutas relativas.
Si el manual es privado, configura la autenticación del alojamiento antes de
compartir la dirección. El acceso al repositorio y el acceso a esa web tienen
su configuración propia.

## Comprobaciones de una actualización

```bash
builds/docs-env/bin/python -m mkdocs build --strict
python3 tools/check_manual.py builds/manual
```

Comprueba también el aspecto en un navegador de escritorio y uno estrecho,
el menú mediante teclado, una búsqueda y los ejemplos. Las pruebas de enlaces
verifican los archivos y fragmentos internos del HTML generado. Las referencias
a servicios externos deben revisarse cuando cambien los procedimientos que describen.
