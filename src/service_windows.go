//go:build windows

package main

import (
	"context"
	"errors"
	"fmt"
	"os"
	"regexp"
	"sync/atomic"
	"time"

	"github.com/gentedelcondado/headscale-gateway/internal/diagnostics"
	"golang.org/x/sys/windows/svc"
	"golang.org/x/sys/windows/svc/eventlog"
)

var windowsServiceActive atomic.Bool
var windowsServiceRestart = make(chan struct{}, 1)

// El SCM conserva la supervisión: detener cancela el contexto común y espera
// el cierre de HTTP, SQLite y tsnet. Reiniciar desde el panel termina con un
// código recuperable; nunca crea un segundo proceso al margen del servicio.
type gatewayWindowsService struct {
	name string
	run  func()
}

func (h gatewayWindowsService) Execute(_ []string, requests <-chan svc.ChangeRequest, statuses chan<- svc.Status) (bool, uint32) {
	serviceStartupEvent(h.name, false, "SCM_HANDLER")
	statuses <- svc.Status{State: svc.StartPending}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	processContext = ctx
	done := make(chan struct{})
	go func() { defer close(done); serviceStartupEvent(h.name, false, "ENGINE_BEGIN"); h.run() }()
	current := svc.Status{State: svc.Running, Accepts: svc.AcceptStop | svc.AcceptShutdown}
	statuses <- current
	restart := false
	for {
		select {
		case <-done:
			return true, 1
		case <-windowsServiceRestart:
			restart = true
		case request := <-requests:
			switch request.Cmd {
			case svc.Interrogate:
				statuses <- current
				continue
			case svc.Stop, svc.Shutdown:
			default:
				continue
			}
		}
		break
	}
	statuses <- svc.Status{State: svc.StopPending, WaitHint: 30000}
	cancel()
	select {
	case <-done:
		if restart {
			return true, 1
		}
		return false, 0
	case <-time.After(30 * time.Second):
		return true, 2
	}
}

func platformServiceEntrypoint(name string, run func()) (bool, error) {
	if windowsServiceActive.Load() {
		return false, nil
	}
	if !regexp.MustCompile(`^[A-Za-z0-9_-]{1,64}$`).MatchString(name) {
		return true, errors.New("nombre del servicio Windows inválido")
	}
	// La conexión al SCM valida este modo y rechaza un arranque de consola
	// sin ejecutar el motor. No se deduce la autorización del proceso padre.
	windowsServiceActive.Store(true)
	serviceStartupEvent(name, false, "SCM_CONNECT")
	err := svc.Run(name, gatewayWindowsService{name: name, run: run})
	if err != nil {
		serviceStartupEvent(name, true, fmt.Sprintf("SCM_ERROR: %v (%#v)", err, err))
	}
	return true, err
}

// Estos eventos no contienen argumentos ni configuración. Permiten diagnosticar
// el arranque incluso antes de disponer del registro persistente del motor.
func serviceStartupEvent(name string, failed bool, phase string) {
	if name == "" {
		return
	}
	if logger, err := eventlog.Open(name); err == nil {
		message := diagnostics.Redact(fmt.Sprintf("Headscale Gateway: %s; pid=%d", phase, os.Getpid()))
		if failed {
			_ = logger.Error(1, message)
		} else {
			_ = logger.Info(2, message)
		}
		_ = logger.Close()
	}
}
