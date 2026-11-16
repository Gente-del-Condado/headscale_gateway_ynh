package headscalecontrol

import (
	"errors"
	"net"
	"net/url"
	"path"
	"regexp"
	"strings"

	"github.com/gentedelcondado/headscale-gateway/internal/network"
)

// Spec pertenece al administrador del anfitrión, fuera de SQLite y de los
// perfiles portables. Solo el instalador privilegiado fija estos recursos.
type Spec struct {
	APIOrigin    string `json:"api_origin,omitempty"`
	Instance     string `json:"instance"`
	AllowedUID   int    `json:"allowed_uid"`
	HeadscaleUID int    `json:"headscale_uid"`
	HeadscaleGID int    `json:"headscale_gid"`
	Binary       string `json:"binary"`
	ConfigPath   string `json:"config_path"`
	RecordsPath  string `json:"records_path,omitempty"`
	StateDir     string `json:"state_dir"`
	SocketPath   string `json:"socket_path"`
	Unit         string `json:"unit"`
	HealthURL    string `json:"health_url"`
	HealthCA     string `json:"health_ca,omitempty"`
}

var unitName = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9_.@-]{0,120}\.service$`)
var instanceName = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,100}$`)

func (s Spec) Validate() error {
	if s.APIOrigin != "" {
		if e := network.ValidateURL(s.APIOrigin); e != nil {
			return errors.New("origen API del coordinador inválido")
		}
	}
	if !instanceName.MatchString(s.Instance) || s.AllowedUID <= 0 || s.HeadscaleUID <= 0 || s.HeadscaleGID <= 0 || s.AllowedUID == s.HeadscaleUID || !unitName.MatchString(s.Unit) {
		return errors.New("registro del controlador Headscale inválido")
	}
	if s.StateDir != path.Join("/var/lib/headscale-gateway-control", s.Instance) || s.SocketPath != path.Join("/run/headscale-gateway-control", s.Instance, "control.sock") {
		return errors.New("estado y socket requieren sus carpetas privadas del controlador")
	}
	for _, name := range []string{s.Binary, s.ConfigPath, s.StateDir, s.SocketPath} {
		if !controllerPath(name) {
			return errors.New("ruta del controlador Headscale inválida")
		}
	}
	for _, name := range []string{s.RecordsPath, s.HealthCA} {
		if name != "" && !controllerPath(name) {
			return errors.New("ruta opcional del controlador Headscale inválida")
		}
	}
	if s.ConfigPath == s.RecordsPath || s.ConfigPath == s.Binary || s.SocketPath == s.ConfigPath || s.SocketPath == s.RecordsPath {
		return errors.New("el controlador no puede compartir archivos de funciones distintas")
	}
	u, e := url.Parse(s.HealthURL)
	if e != nil || u.User != nil || u.RawQuery != "" || u.Fragment != "" || u.Path != "/health" || u.Scheme != "http" && u.Scheme != "https" || net.ParseIP(u.Hostname()) == nil {
		return errors.New("la salud de Headscale requiere una IP local y la ruta /health")
	}
	return nil
}

// Las rutas pertenecen al actuador Linux, aunque un cliente Windows lea o
// valide el contrato. filepath aplicaría las reglas del cliente y rechazaría
// un vínculo Linux válido. Nunca se aceptan rutas Windows ni rutas ambiguas.
func controllerPath(name string) bool {
	return path.IsAbs(name) && path.Clean(name) == name && name != "/" && !strings.ContainsAny(name, "\\\x00\r\n")
}
