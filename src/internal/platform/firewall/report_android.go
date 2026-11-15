//go:build android

package firewall

import "context"

func inspect(_ context.Context, r Report) Report {
	r.Platform = "android"
	r.Note = "Android no permite comprobar el cortafuegos desde esta aplicación. Este estado no indica que falte un permiso. Si falla el acceso por Wi-Fi, revisa la VPN y las restricciones de la red"
	r.Instructions = []string{"Revisa los ajustes de la aplicación y las restricciones de batería y datos de Android"}
	return r
}
