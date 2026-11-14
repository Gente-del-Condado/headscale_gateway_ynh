#!/bin/bash
# shellcheck disable=SC1091,SC2154,SC2034
# YunoHost inyecta los ajustes y las funciones auxiliares en el entorno del script.

hgw_check_sso() {
    local version
    version="$(dpkg-query -W -f='${Version}' ssowat)"
    dpkg --compare-versions "$version" ge 12.1.1 || ynh_die "Actualiza SSOwat a la versión 12.1.1 o posterior antes de habilitar el acceso desde el portal"
    getent group admins >/dev/null || ynh_die "El grupo admins de YunoHost no está disponible mediante NSS"
}

hgw_install_binary() {
    # El recurso oficial selecciona la arquitectura y comprueba SHA-256.
    # La configuración privada se conserva también al sustituir el ejecutable.
    if [[ -e "$install_dir/startup.json" || -L "$install_dir/startup.json" ]]; then
        hgw_restore_startup_permissions
    fi
    ynh_setup_source --dest_dir="$install_dir" --full_replace --keep="startup.json"
    ynh_setup_source --dest_dir="$install_dir/sources" --source_id=build_sources
    chmod 0750 "$install_dir/headscale-gateway"
    cp -a ../doc/third_party "$install_dir/notices"
    chown -R "$app:$app" "$install_dir"
    if [[ -f "$install_dir/startup.json" ]]; then hgw_restore_startup_permissions; fi
}

hgw_configure() {
    local args=(--app "$app" --install-dir "$install_dir" --data-dir "$data_dir"
        --port "$port" --lan-port "$port_lan" --path "$path"
        --proxy-include "/etc/nginx/conf.d/$domain.d/$app-proxy-auth.inc")
    python3 ../conf/configure.py "${args[@]}"
    chown root:root "/etc/nginx/conf.d/$domain.d/$app-proxy-auth.inc"
    chmod 0600 "/etc/nginx/conf.d/$domain.d/$app-proxy-auth.inc"
    chown --no-dereference "$app:$app" "$install_dir/startup.json"
    chown -R "$app:$app" "$data_dir"
    chmod 0700 "$data_dir" "$data_dir/gateway"
    if [[ -f "$data_dir/initial-admin.json" ]]; then
        chmod 0600 "$data_dir/initial-admin.json"
    fi
}

hgw_register_service() {
    yunohost service add "$app" --description="Gateway HTTPS privado para Headscale" --log="$data_dir/gateway/logs/gateway.log"
}

hgw_restore_startup_permissions() {
    # YunoHost puede normalizar permisos al recuperar el directorio instalado.
    # Este archivo contiene el secreto del proxy y el motor solo admite 0600.
    [[ -f "$install_dir/startup.json" && ! -L "$install_dir/startup.json" ]] || ynh_die "La configuración de arranque restaurada no es un archivo normal"
    chmod 0600 "$install_dir/startup.json"
    chown --no-dereference "$app:$app" "$install_dir/startup.json"
}

hgw_install_logo() {
    local logo="${1:-../doc/logo.png}" current_logo default_logo
    current_logo="$(yunohost user permission info "$app.main" --output-as json --quiet |
        python3 -c 'import json, sys; print(json.load(sys.stdin).get("logo_hash") or "")')"
    default_logo="$(sha256sum "$logo")"
    default_logo="${default_logo%% *}"
    # Conserva un logo personalizado. Registrar de nuevo el logo propio también
    # repone su PNG en la caché global al restaurar en otro servidor YunoHost.
    if [[ -z "$current_logo" || "$current_logo" == "$default_logo" ]]; then
        yunohost user permission update "$app.main" --logo="$logo"
    fi
}
