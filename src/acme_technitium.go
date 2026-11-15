package main

import (
	"context"
	"fmt"

	technitium "github.com/gentedelcondado/headscale-gateway/internal/acmednstechnitium"
	"github.com/libdns/libdns"
)

// La API original incluye el token en la URL. Sus errores no deben llegar sin
// filtrar al registrador de CertMagic, que escribe fuera de diagnostics.
type technitiumDNS01Provider struct{ inner *technitium.Provider }

func (p *technitiumDNS01Provider) AppendRecords(ctx context.Context, zone string, records []libdns.Record) ([]libdns.Record, error) {
	result, err := p.inner.AppendRecords(ctx, zone, records)
	return result, safeTechnitiumACMEError(ctx, "publicar", err)
}
func (p *technitiumDNS01Provider) DeleteRecords(ctx context.Context, zone string, records []libdns.Record) ([]libdns.Record, error) {
	result, err := p.inner.DeleteRecords(ctx, zone, records)
	return result, safeTechnitiumACMEError(ctx, "retirar", err)
}
func safeTechnitiumACMEError(ctx context.Context, action string, err error) error {
	if err == nil {
		return nil
	}
	if ctx.Err() != nil {
		return ctx.Err()
	}
	// Se conserva la operación, sin la respuesta ni la URL con credenciales.
	return fmt.Errorf("Technitium DNS-01: no se pudo %s el desafío; revisa red, URL, token y permisos", action)
}
