# Gente del Condado · Tienda F-Droid propia

Repositorio Android de **Gente del Condado**, independiente del catálogo oficial
de F-Droid. Distribuye las APK originales de nuestras releases públicas, con la
misma firma del desarrollador. No exige que una aplicación esté aceptada en
f-droid.org y no representa una aprobación de ese catálogo.

## Añadir la tienda

En F-Droid abre **Ajustes → Repositorios → Añadir repositorio** y pega:

```text
https://gente-del-condado.github.io/Mis_app_fdroid/fdroid/repo?fingerprint=6A108C3A2C7C29CBFCE56C9031E7E4B41644D75D1AB08E95622F840026E2AAD9
```

Comprueba que el nombre sea **Gente del Condado** y que la huella SHA-256 sea:

```text
6A108C3A2C7C29CBFCE56C9031E7E4B41644D75D1AB08E95622F840026E2AAD9
```

La [página del repositorio](https://gente-del-condado.github.io/Mis_app_fdroid/fdroid/repo/)
incluye el código QR. Tras añadirlo, actualiza los índices y busca la aplicación.
F-Droid pedirá los permisos de instalación que correspondan; esta tienda no
concede instalación silenciosa ni sustituye los permisos de Android.

## Aplicaciones

| Aplicación | Identificador | Procedencia |
| --- | --- | --- |
| Headscale Gateway | `org.headscalegateway.android` | [Releases públicas](https://github.com/Gente-del-Condado/headscale_gateway_releases/releases) |

Para Headscale Gateway se usa **`headscale-gateway-release.apk`**, no la APK sin
firmar de la receta del catálogo oficial, una APK de laboratorio ni el AAB de Play.
Una instalación directa con la misma firma puede actualizarse sin desinstalar ni
borrar datos. Una instalación firmada por otro distribuidor requiere estudiar su
migración; una coincidencia de nombre no hace compatibles dos firmas distintas.

Los [fuentes completos](https://github.com/Gente-del-Condado/headscale_gateway_ynh/tree/upstream-source)
y las licencias siguen disponibles. [Manual de Android](https://gente-del-condado.github.io/headscale_gateway_ynh/ANDROID_USO.html).
Play Store permanece solo preparado; este flujo no envía aplicaciones allí.

El icono del catálogo se mantiene como PNG en
`metadata/org.headscalegateway.android/en-US/images/icon.png`, reutilizando el
icono existente del proyecto. El generador lo incorpora al índice y comprueba
su archivo y suma antes de publicar; no modifica el icono ni la firma de la APK.

## Origen y publicación automática

Las fuentes de esta tienda se mantienen en `packaging/fdroid-store/` del principal
privado de [Forgejo](https://gentedelcondado.es/forgejo/wolfbelmi88/headscale_gateway).
Este repositorio público recibe solo su automatización y metadatos. No recibe
el historial privado ni devuelve cambios a Forgejo.

El recorrido es **Forgejo → compilador público GitHub → APK publicada → esta
tienda → GitHub Pages**. La tienda consulta las releases públicas cada hora,
en el minuto 43 UTC, y también al actualizar su controlador. GitHub puede retrasar
las programaciones. Si no hay cambios, omite generación y despliegue; renueva el
índice semanalmente. No recompila las aplicaciones.

Antes de publicar valida SHA-256 de la release, firma real de la APK, paquete,
versión y ausencia de depuración. Solo admite los orígenes y certificados
fijados en `store.json`. Conserva las dos versiones estables más recientes por
aplicación. Los índices v1 y v2 se firman con una identidad propia y se comprueban
antes del despliegue. Un fallo bloquea la actualización del sitio existente.

## Mantener o añadir una aplicación

Edita `store.json` primero en Forgejo. Cada aplicación necesita su identificador,
repositorio público, nombres de la APK directa y su informe verificable, licencia,
manual, fuentes y huella de firma. La release debe aportar `SHA256SUMS` y el
informe JSON de identidad. No se incorporan APK encontradas al azar ni claves
nuevas sin revisión. No se modifica la firma original de ninguna APK.

```sh
python3 -B -m unittest discover -s automation -p 'test_*.py'
python3 automation/sync.py --plan --work /tmp/fdroid-store-check
```

La generación requiere fdroidserver 2.4.5, JDK 17, SDK Android con build-tools
35.0.0 y el secreto de Actions **FDROID_REPO_SIGNING_BUNDLE**. Ese secreto contiene
solo la identidad del índice: nunca la firma privada de las aplicaciones. Se
conserva una copia privada fuera de Git para recuperación. No crear otra clave
si se pierde el acceso a Actions: cambiaría la identidad de la tienda.

GitHub Pages debe usar **GitHub Actions** como origen. El workflow utiliza
`GITHUB_TOKEN` para publicar Pages; no necesita un token personal ni acceso al
principal privado. Solo se sube `site/`, que excluye claves, contraseñas y
configuración privada. `LICENSE` cubre esta automatización; cada aplicación
conserva su licencia y sus fuentes correspondientes.

Autor: **Gente del Condado**. Soporte: [headscale-gateway@gentedelcondado.es](mailto:headscale-gateway@gentedelcondado.es).

Referencias: [repositorios propios F-Droid](https://f-droid.org/en/docs/Setup_an_F-Droid_App_Repo/)
y [firmas del índice y de APK](https://f-droid.org/en/docs/Signing_Process/).
