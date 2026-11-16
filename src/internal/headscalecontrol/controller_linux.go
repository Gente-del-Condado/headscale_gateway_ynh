//go:build linux && !android

package headscalecontrol

import (
	"context"
	"errors"
	"flag"
	"io"
	"net"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"golang.org/x/sys/unix"
)

type localIdentity struct{}

// RunController es un modo separado del mismo ejecutable Go. No abre SQLite
// del Gateway, tsnet ni el panel, y solo escucha en un socket Unix privado.
func RunController(arguments []string) error {
	flags := flag.NewFlagSet("headscale-control", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	path := flags.String("spec", "", "registro local root")
	if flags.Parse(arguments) != nil || *path == "" || flags.NArg() != 0 {
		return errors.New("uso: headscale-control --spec /etc/headscale-gateway-control/instancia.json")
	}
	if os.Geteuid() != 0 {
		return errors.New("el ayudante local debe iniciarse mediante su servicio privilegiado")
	}
	spec, e := loadSpec(*path)
	if e != nil {
		return errors.New("no se pudo validar el registro local del controlador")
	}
	backend, e := NewDiskBackend(spec)
	if e != nil {
		return errors.New("no se pudo inicializar el estado privado del controlador")
	}
	lockPath := filepath.Join(spec.StateDir, "controller.lock")
	lock, e := os.OpenFile(lockPath, os.O_RDWR|os.O_CREATE|syscall.O_NOFOLLOW, 0600)
	if e != nil {
		return errors.New("no se pudo abrir el bloqueo del controlador")
	}
	defer lock.Close()
	if e = unix.Flock(int(lock.Fd()), unix.LOCK_EX|unix.LOCK_NB); e != nil {
		return errors.New("ya hay un controlador para esta instancia")
	}
	defer unix.Flock(int(lock.Fd()), unix.LOCK_UN)
	recovery, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	e = backend.Recover(recovery)
	cancel()
	if e != nil {
		return errors.New("recuperación pendiente de Headscale; revisar el diario local antes de continuar")
	}
	// Verificar el destino seleccionado antes de anunciar disponibilidad evita
	// registrar una ruta de salud errónea que impediría comprobar un rollback.
	readiness, cancelReady := context.WithTimeout(context.Background(), time.Minute)
	e = backend.checkHealth(readiness)
	cancelReady()
	if e != nil {
		return errors.New("Headscale no está saludable en el destino registrado")
	}
	if e = ensureRootDir(filepath.Dir(spec.SocketPath), 0711); e != nil {
		return e
	}
	if previous, e := os.Lstat(spec.SocketPath); e == nil {
		if previous.Mode()&os.ModeSocket == 0 {
			return errors.New("la ruta del socket está ocupada por otro tipo de archivo")
		}
		if e = os.Remove(spec.SocketPath); e != nil {
			return errors.New("no se pudo retirar el socket obsoleto")
		}
	} else if !os.IsNotExist(e) {
		return errors.New("no se pudo comprobar el socket local")
	}
	listener, e := net.ListenUnix("unix", &net.UnixAddr{Name: spec.SocketPath, Net: "unix"})
	if e != nil {
		return errors.New("no se pudo abrir el socket del controlador")
	}
	defer listener.Close()
	if e = os.Chown(spec.SocketPath, spec.AllowedUID, -1); e != nil {
		return e
	}
	if e = os.Chmod(spec.SocketPath, 0600); e != nil {
		return e
	}
	manager := NewManager(backend, spec.Instance, spec.RecordsPath != "", spec.APIOrigin)
	handler := manager.Handler()
	server := &http.Server{ReadHeaderTimeout: 3 * time.Second, ReadTimeout: 10 * time.Second, WriteTimeout: 12 * time.Second, IdleTimeout: 20 * time.Second, MaxHeaderBytes: 8192}
	server.ConnContext = func(ctx context.Context, connection net.Conn) context.Context {
		allowed := false
		if socket, ok := connection.(*net.UnixConn); ok {
			if raw, e := socket.SyscallConn(); e == nil {
				_ = raw.Control(func(fd uintptr) {
					if credential, e := unix.GetsockoptUcred(int(fd), unix.SOL_SOCKET, unix.SO_PEERCRED); e == nil {
						allowed = credential.Uid == 0 || credential.Uid == uint32(spec.AllowedUID)
					}
				})
			}
		}
		return context.WithValue(ctx, localIdentity{}, allowed)
	}
	server.Handler = http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Context().Value(localIdentity{}) != true {
			jsonReply(w, 403, map[string]string{"error": "usuario local no autorizado"})
			return
		}
		handler.ServeHTTP(w, r)
	})
	stopped := make(chan error, 1)
	go func() { stopped <- server.Serve(listener) }()
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	select {
	case e = <-stopped:
		if !errors.Is(e, http.ErrServerClosed) {
			return errors.New("el listener del controlador se detuvo")
		}
	case <-ctx.Done():
	}
	shutdown, done := context.WithTimeout(context.Background(), 4*time.Minute)
	defer done()
	_ = server.Shutdown(shutdown)
	return manager.Wait(shutdown)
}
