# Distribución mediante F-Droid

## Tienda propia de Gente del Condado

La tienda pública [Mis_app_fdroid](https://github.com/Gente-del-Condado/Mis_app_fdroid)
distribuye las APK directas ya firmadas, sin recompilarlas ni cambiar su identidad.
Puede utilizarse aunque la aplicación no esté en el catálogo oficial. Sigue las
[instrucciones para añadirla y comprobar la huella](https://github.com/Gente-del-Condado/Mis_app_fdroid#añadir-la-tienda).
Los fuentes de su controlador están en `packaging/fdroid-store/` del principal
de Forgejo; GitHub recoge las releases públicas y publica el índice en Pages.
La clave del índice es distinta de la clave Android. No se usa la APK sin firmar
de la receta que se describe a continuación.

## Solicitud al catálogo oficial

La solicitud [!57374](https://gitlab.com/fdroid/fdroiddata/-/merge_requests/57374)
propuso `1.4.7-android.5` (`10040075`). F-Droid la cerró el 14 de noviembre de
2026 porque exige más de tres meses de mantenimiento. No está aceptada ni
publicada en su catálogo. Esta receta conserva las correcciones para repetir
la validación y preparar una futura solicitud cuando se cumpla esa política.
La receta propone solo la versión actual y fija el commit público completo
`b14a986ae84047b5d407ecc1866bb0ae4b711ca1`, identificado también por la etiqueta
inmutable `source-android-v1.4.7-android.5`. Los fuentes completos están en
`upstream-source` del repositorio público indicado en los metadatos.
No basta con el manifiesto y los binarios del paquete YunoHost de `main`.

El script compila Go desde los fuentes comunes; no descarga APK, AAR ni motores
precompilados del proyecto. El toolchain Go oficial se verifica por SHA-256.
Gradle construye JNI desde los fuentes HEV incluidos con sus licencias. La
variante F-Droid elimina la firma del titular. El wrapper Gradle conserva los
avisos y una suma de distribución fija. Los fuentes Go se descargan según
`go.mod`/`go.sum`, sin cambiar versiones.

La receta pasa localmente `fdroid readmeta`, `rewritemeta`, `lint` y la
compilación con escaneo binario de fdroidserver 2.4.5. Los nueve trabajos del
[primer pipeline](https://gitlab.com/Gente-del-Condado/fdroiddata/-/pipelines/3068810522)
también pasaron. Para repetir la validación:

```sh
fdroid readmeta
fdroid rewritemeta org.headscalegateway.android
fdroid lint org.headscalegateway.android
fdroid build --test --stop --scan-binary org.headscalegateway.android:10040075
```

La compilación local y el CI de la solicitud no equivalen a aceptación ni a una
compilación de distribución en el servidor oficial. Para esta última se utiliza
`fdroid build --server org.headscalegateway.android:10040075` en su entorno.
Revisa los resultados del escáner, sin ignorar carpetas enteras
ni añadir excepciones genéricas para binarios. Los módulos Go pueden incorporar
recursos generados por terceros; conserva sus licencias y resuelve cualquier
objeción del revisor aportando los fuentes o desactivando el recurso afectado.

El `prebuild` elimina únicamente `ndk.dir` del archivo local generado por
fdroidserver: Gradle selecciona el mismo NDK mediante `ndkVersion`. También
convierte las asignaciones antiguas de `namespace` y `ndkVersion` a la sintaxis
explícita, sin cambiar sus valores ni modificar la etiqueta pública. Así se
corrigen CXX5106 y las advertencias de asignación Groovy. El aviso de caché
`.gradle` procede del CI general de fdroiddata y no se modifica desde esta receta.

La ficha localizada está en `android/fastlane/metadata/android/`. Quedan la
evaluación de madurez y las capturas de teléfono para la revisión de inclusión.
El `prebuild` sustituye también `stopForeground(true)` por
`stopForeground(STOP_FOREGROUND_REMOVE)` en ambos servicios. Es la operación
equivalente disponible desde API 24, el mínimo del proyecto, y corrige esas dos
llamadas obsoletas sin modificar los APK ni las etiquetas ya publicados.
El compilador todavía avisa de otras API de compatibilidad de la ventana,
notificaciones, navegación y consulta de redes. La salida detallada se obtiene
con `-Xlint:deprecation`; no se suprimen esas advertencias ni se cambia el ciclo
de vida de la red para silenciarlas. Android Lint sigue sin errores; sus avisos
de compatibilidad, recursos y recomendaciones requieren su revisión específica.

No se declara reproducibilidad
binaria frente a la APK directa: difieren cuatro bibliotecas JNI/HEV. F-Droid
firmará su canal con otra identidad; migrar desde la APK directa exige exportar,
reinstalar e importar. Las actualizaciones automáticas de la receta permanecen
desactivadas hasta validar su regla. Google Play sigue solo preparado.

Referencias: [inclusión](https://f-droid.org/docs/Inclusion_Policy/),
[metadatos](https://f-droid.org/docs/Build_Metadata_Reference/) y
[solicitud](https://f-droid.org/docs/Submitting_to_F-Droid_Quick_Start_Guide/).
