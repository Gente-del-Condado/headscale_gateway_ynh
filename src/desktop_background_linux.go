//go:build linux

package main

import (
	"context"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/gentedelcondado/headscale-gateway/internal/diagnostics"
	"github.com/godbus/dbus/v5"
)

// El portal decide y solicita consentimiento. No escribe autostart en el host
// ni solicita acceso al sistema de archivos o al bus completo desde el sandbox.
func requestDesktopBackground(ctx context.Context) {
	if os.Getenv("FLATPAK_ID") != "es.gentedelcondado.HeadscaleGateway" || os.Getenv("GATEWAY_DESKTOP_BACKGROUND") != "1" {
		return
	}
	ctx, cancel := context.WithTimeout(ctx, 5*time.Minute)
	defer cancel()
	connection, err := dbus.ConnectSessionBus()
	if err != nil {
		desktopBackgroundWarning()
		return
	}
	defer connection.Close()
	token := fmt.Sprintf("hgw%d", time.Now().UnixNano())
	unique := strings.TrimPrefix(connection.Names()[0], ":")
	path := dbus.ObjectPath("/org/freedesktop/portal/desktop/request/" + strings.ReplaceAll(unique, ".", "_") + "/" + token)
	options := []dbus.MatchOption{dbus.WithMatchSender("org.freedesktop.portal.Desktop"), dbus.WithMatchObjectPath(path), dbus.WithMatchInterface("org.freedesktop.portal.Request"), dbus.WithMatchMember("Response")}
	if err = connection.AddMatchSignal(options...); err != nil {
		desktopBackgroundWarning()
		return
	}
	defer connection.RemoveMatchSignal(options...)
	signals := make(chan *dbus.Signal, 1)
	connection.Signal(signals)
	defer connection.RemoveSignal(signals)
	request := connection.Object("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")
	var handle dbus.ObjectPath
	err = request.CallWithContext(ctx, "org.freedesktop.portal.Background.RequestBackground", 0, "", map[string]dbus.Variant{
		"handle_token": dbus.MakeVariant(token),
		"reason":       dbus.MakeVariant("Mantener los servicios privados del Gateway disponibles al cerrar el navegador e iniciar sesión"),
		"autostart":    dbus.MakeVariant(true),
		"commandline":  dbus.MakeVariant([]string{"headscale-gateway-launcher", "--background"}),
	}).Store(&handle)
	if err != nil || handle != path {
		desktopBackgroundWarning()
		return
	}
	select {
	case signal := <-signals:
		var response uint32
		var values map[string]dbus.Variant
		if signal == nil || dbus.Store(signal.Body, &response, &values) != nil || response != 0 {
			desktopBackgroundWarning()
			return
		}
		background, _ := values["background"].Value().(bool)
		autostart, _ := values["autostart"].Value().(bool)
		if !background || !autostart {
			desktopBackgroundWarning()
			return
		}
		diagnostics.Emit("gateway", diagnostics.InfoLevel, "HGW-DESKTOP-BACKGROUND-OK", "El escritorio ha autorizado segundo plano y arranque de sesión del Gateway")
	case <-ctx.Done():
		_ = connection.Object("org.freedesktop.portal.Desktop", handle).Call("org.freedesktop.portal.Request.Close", dbus.FlagNoReplyExpected).Err
		desktopBackgroundWarning()
	}
}

func desktopBackgroundWarning() {
	diagnostics.Emit("gateway", diagnostics.Warn, "HGW-DESKTOP-BACKGROUND-PENDING", "El escritorio no ha confirmado el arranque automático y segundo plano; revisa los permisos de la aplicación Flatpak")
}
