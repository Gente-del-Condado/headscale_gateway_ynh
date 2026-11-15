//go:build linux

package main

import (
	"net"
	"os"
	"path/filepath"
)

// Publica solo la dirección loopback para el acceso del menú del paquete nativo.
// systemd crea este directorio para el usuario de servicio. Nunca publica el
// archivo de arranque, SQLite, tokens ni contraseñas, ni acepta una ruta arbitraria.
func publishDesktopAdminAddress(address net.Addr) {
	if os.Getenv("RUNTIME_DIRECTORY") != "/run/headscale-gateway" {
		return
	}
	host, port, err := net.SplitHostPort(address.String())
	if err != nil {
		return
	}
	ip := net.ParseIP(host)
	if ip == nil || !ip.IsLoopback() {
		return
	}
	file, err := os.CreateTemp("/run/headscale-gateway", ".admin-url-")
	if err != nil {
		return
	}
	defer os.Remove(file.Name())
	if err = file.Chmod(0644); err == nil {
		_, err = file.WriteString("http://" + net.JoinHostPort(host, port) + "/admin/\n")
	}
	closeErr := file.Close()
	if err == nil && closeErr == nil {
		_ = os.Rename(file.Name(), filepath.Join("/run/headscale-gateway", "admin-url"))
	}
}
