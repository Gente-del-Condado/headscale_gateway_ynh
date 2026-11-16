# Herramientas de mantenimiento

Ejecuta las herramientas desde la raíz del proyecto. No necesitas conocer todos
los scripts para empezar: sigue [la guía inicial](../docs/EMPEZAR_DESARROLLO.md).

| Necesidad | Herramienta |
| --- | --- |
| Verificar estructura y privacidad | `check_repository.py`, `check_privacy.py` |
| Ejecutar la regresión general | `verify.sh` o `verify.ps1` |
| Cambiar la versión común | `set_version.py` |
| Generar y comprobar instaladores Git | `prepare_git_install.py` |
| Referencia y traducciones | `reference_catalog.py`, `extract_i18n.py`, `check_i18n.py` |
| Manual web | `manual_hooks.py`, `check_manual.py`; receta en `docs/MANUAL_WEB.md` |
| Exportar fuentes revisados | `repository_archive.py` |
| Preparar un panel local aislado | `configure.py` |
| Compilar motor, Android o paquetes | `build_release.py`, `build_android_*.py`, `package_*.py` |
| Comprobar despliegue aislado | `check_deployment.py`, `preflight_local.sh` |
| Publicadores de destinos concretos | `publish_*.py`; los llama el controlador público |

Los publicadores no son el primer paso de una contribución: requieren destinos,
permisos y autorización de publicación. El controlador vigente está en
`packaging/releases/automation/`; las recetas antiguas de publicación privada
se retiraron del árbol actual y siguen disponibles en sus etiquetas históricas.

Las herramientas `test_android_*.py`, `check_windows_service.ps1` y las de
aceptación necesitan dispositivos o entornos aislados preparados expresamente.
No se ejecutan contra instalaciones productivas ni se obtienen permisos nuevos
por estar un equipo conectado. Los datos y las claves de prueba se guardan fuera
del clon; `builds/` se utiliza para resultados reproducibles sin secretos.
