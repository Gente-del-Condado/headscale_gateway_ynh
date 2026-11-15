package main

import (
	"context"
	"errors"

	"github.com/caddyserver/certmagic"
	"github.com/mholt/acmez/v3/acme"
)

// La configuración se aplica antes de construir el emisor. CertMagic llama a
// este callback únicamente al crear una cuenta: las cuentas guardadas siguen
// renovando aunque una instalación antigua carezca de la opción nueva.
func configureACMEAccountConsent(cfg Config) {
	accepted := cfg.ACMEAgreeToTerms
	certmagic.DefaultACME.Agreed = accepted
	certmagic.DefaultACME.NewAccountFunc = func(_ context.Context, _ *certmagic.ACMEIssuer, account acme.Account) (acme.Account, error) {
		if !accepted {
			return account, errors.New("Para crear una cuenta ACME nueva, revisa los términos de la CA y activa acme.agree_to_terms en Certificados")
		}
		return account, nil
	}
}
