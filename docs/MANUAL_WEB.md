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

El principal privado de Forgejo se replica al espejo privado de GitHub. El
compilador público `headscale_gateway_releases` obtiene la release estable y
construye el manual desde sus fuentes, valida los enlaces y publica el mismo
HTML en `gh-pages` de estos dos destinos:

- [Manual YunoHost](https://gente-del-condado.github.io/headscale_gateway_ynh/).
- [Manual Home Assistant](https://gente-del-condado.github.io/headscale_gateway_ha/).

En ambos repositorios, **Settings → Pages** debe utilizar `gh-pages`, carpeta
`/`. El principal privado no necesita Pages. El publicador conserva el historial
de `gh-pages`, no sustituye `main` del paquete y utiliza `PUBLICATION_TOKEN`
limitado a los destinos públicos. No escribe en Forgejo.

El controlador tiene además una actualización documental que toma las guías
del `main` de Forgejo y las combina con los fuentes de una release completada.
Su código vive en `packaging/releases/`; consulta [PUBLICACION.md](PUBLICACION.md).
Los pull requests y las comprobaciones locales no publican ni reciben el token.

**Preparar sin subir** significa editar las fuentes, compilar en local y revisar
el HTML. No actualiza las webs públicas ni autoriza un push a sus ramas. Para
publicar después, sigue el recorrido autorizado de la entrega; no uses recetas
antiguas con claves de escritura a repositorios derivados de Forgejo.

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

## Guías de descarga vigentes

El controlador conserva copias derivadas de los README del principal, descargas
y escritorio y de las guías de publicación y licencias. `manual-current.yml`
las superpone al árbol de documentación de la última entrega completada y vuelve
a validar el manual. Así ambas webs explican los fuentes reutilizables sin
recompilar ni reemplazar los instaladores. Las fuentes editables permanecen en
este principal; esas copias no se editan por separado.
