package main

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"errors"
	"net"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/gentedelcondado/headscale-gateway/internal/headscalecontrol"
	"github.com/gentedelcondado/headscale-gateway/internal/pki"
)

// El enlace privilegiado local pertenece al instalador, nunca a un perfil
// importado ni a un formulario web. Todos los sistemas comparten el cliente
// remoto; el ayudante de actuación local se ejecuta en Linux.
func localHeadscaleControlSocket() string {
	if runtime.GOOS != "linux" {
		return ""
	}
	path := os.Getenv("HGW_HEADSCALE_CONTROL_SOCKET")
	if !filepath.IsAbs(path) || filepath.Clean(path) != path || !strings.HasPrefix(path, "/run/headscale-gateway-control/") || filepath.Base(path) != "control.sock" {
		return ""
	}
	return path
}

func (a *adminController) HeadscaleControlIsLocal() bool {
	return a.runtime.currentConfig().HeadscaleControlMode == "local" && localHeadscaleControlSocket() != ""
}

func sameControlPeer(origin, endpoint string) bool {
	u, e := pki.PeerURL(origin)
	if e != nil {
		return false
	}
	v, e := pki.PeerURL(endpoint)
	if e != nil {
		return false
	}
	return strings.TrimPrefix(u.Hostname(), "admin.") == strings.TrimPrefix(v.Hostname(), "admin.")
}

func (a *adminController) headscaleControlClient(ctx context.Context) (*headscalecontrol.Client, error) {
	cfg := a.runtime.currentConfig()
	switch cfg.HeadscaleControlMode {
	case "local":
		socket := localHeadscaleControlSocket()
		if socket == "" {
			return nil, errors.New("el instalador del anfitrión no ha registrado un controlador Headscale local")
		}
		client := headscalecontrol.NewLocalClient(socket)
		origin, e := client.CoordinatorOrigin(ctx)
		if e != nil || strings.TrimRight(cfg.HeadscaleURL, "/") != strings.TrimRight(origin, "/") {
			client.Close()
			return nil, errors.New("la URL Headscale del Gateway no coincide con el coordinador registrado; revisa el vínculo local")
		}
		return client, nil
	case "remote":
		if e := validateHeadscaleControlConfig(cfg); e != nil {
			return nil, e
		}
		store, e := pki.NewStore(cfg.DataDir)
		if e != nil {
			return nil, errors.New("almacén de confianza del controlador no disponible")
		}
		anchor, e := store.Get(cfg.HeadscaleControlFingerprint)
		if e != nil || !anchor.Approved || time.Now().After(anchor.Expires) || !sameControlPeer(cfg.HeadscaleControlOrigin, anchor.Endpoint) {
			return nil, errors.New("se requiere una CA aprobada y vinculada al Gateway controlador")
		}
		u, _ := url.Parse(cfg.HeadscaleControlOrigin)
		planning, cancel := context.WithTimeout(ctx, 5*time.Second)
		defer cancel()
		var hints []string
		vpn := a.networkServer()
		if vpn != nil {
			if local, e := vpn.LocalClient(); e == nil {
				if status, e := local.Status(planning); e == nil && status != nil {
					expected := strings.TrimPrefix(u.Hostname(), "admin.")
					for _, peer := range status.Peer {
						if peer == nil {
							continue
						}
						dnsName := strings.TrimSuffix(peer.DNSName, ".")
						if expected == dnsName || expected == strings.Split(dnsName, ".")[0]+"."+cfg.BaseDomain {
							for _, ip := range peer.TailscaleIPs {
								hints = append(hints, ip.String())
							}
						}
					}
				}
			}
		}
		targets, e := pki.Plan(planning, cfg.HeadscaleControlOrigin, hints)
		if e != nil {
			return nil, errors.New("el controlador no tiene una dirección privada verificada")
		}
		roots, _ := x509.SystemCertPool()
		if roots == nil {
			roots = x509.NewCertPool()
		}
		if !roots.AppendCertsFromPEM([]byte(anchor.PEM)) {
			return nil, errors.New("CA del controlador inválida")
		}
		transport := &http.Transport{Proxy: nil, TLSClientConfig: &tls.Config{MinVersion: tls.VersionTLS12, RootCAs: roots, ServerName: u.Hostname()}, MaxConnsPerHost: 2}
		transport.DialContext = func(ctx context.Context, _, _ string) (net.Conn, error) {
			for _, target := range targets {
				address, _ := url.Parse(target.Origin)
				port := address.Port()
				if port == "" {
					port = "443"
				}
				attempt, cancel := context.WithTimeout(ctx, 2*time.Second)
				var connection net.Conn
				var e error
				if target.Network == "Tailnet" {
					if vpn != nil {
						connection, e = vpn.Dial(attempt, "tcp", net.JoinHostPort(target.IP, port))
					} else {
						e = errors.New("VPN no disponible")
					}
				} else {
					connection, e = (&net.Dialer{Timeout: 2 * time.Second}).DialContext(attempt, "tcp", net.JoinHostPort(target.IP, port))
				}
				cancel()
				if e == nil {
					return connection, nil
				}
			}
			return nil, errors.New("ninguna dirección privada del controlador es accesible")
		}
		return headscalecontrol.NewRemoteClient(transport, cfg.HeadscaleControlOrigin, cfg.HeadscaleControlToken)
	default:
		return nil, errors.New("administración del coordinador Headscale desactivada")
	}
}

func (a *adminController) HeadscaleControlInfo(ctx context.Context) (headscalecontrol.Info, error) {
	cfg := a.runtime.currentConfig()
	mode := cfg.HeadscaleControlMode
	if mode == "" {
		mode = "disabled"
	}
	value := headscalecontrol.Info{Mode: mode, LocalAvailable: localHeadscaleControlSocket() != "", LocalController: a.HeadscaleControlIsLocal(), RemoteTokenConfigured: cfg.HeadscaleControlToken != "", CanWrite: a.HeadscaleControlIsLocal()}
	value.CanSyncAgent = cfg.HeadscaleAgentEnabled
	if mode == "local" {
		client, e := a.headscaleControlClient(ctx)
		if e != nil {
			value.CanWrite = false
			value.CanSyncAgent = false
			return value, e
		}
		client.Close()
	}
	if mode == "remote" {
		client, e := a.headscaleControlClient(ctx)
		if e != nil {
			return value, e
		}
		defer client.Close()
		upstream, e := client.Info(ctx)
		if e != nil {
			return value, e
		}
		value.CanWrite = upstream.CanWrite
		value.CanSyncAgent = upstream.CanSyncAgent
	}
	return value, nil
}
func (a *adminController) HeadscaleControlDocument(ctx context.Context) (headscalecontrol.Document, error) {
	c, e := a.headscaleControlClient(ctx)
	if e != nil {
		return headscalecontrol.Document{}, e
	}
	defer c.Close()
	return c.Document(ctx)
}
func (a *adminController) HeadscaleControlPreview(ctx context.Context, change headscalecontrol.Change) (headscalecontrol.Preview, error) {
	c, e := a.headscaleControlClient(ctx)
	if e != nil {
		return headscalecontrol.Preview{}, e
	}
	defer c.Close()
	return c.Preview(ctx, change)
}
func (a *adminController) HeadscaleControlApply(ctx context.Context, change headscalecontrol.Change) (headscalecontrol.Operation, error) {
	c, e := a.headscaleControlClient(ctx)
	if e != nil {
		return headscalecontrol.Operation{}, e
	}
	defer c.Close()
	return c.Apply(ctx, change)
}
func (a *adminController) HeadscaleControlOperation(ctx context.Context, id string) (headscalecontrol.Operation, error) {
	c, e := a.headscaleControlClient(ctx)
	if e != nil {
		return headscalecontrol.Operation{}, e
	}
	defer c.Close()
	return c.Operation(ctx, id)
}
