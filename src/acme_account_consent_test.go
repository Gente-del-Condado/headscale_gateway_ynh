package main

import (
	"context"
	"path/filepath"
	"testing"
	"time"

	"github.com/caddyserver/certmagic"
	"github.com/gentedelcondado/headscale-gateway/internal/configtransfer"
	"github.com/mholt/acmez/v3/acme"
)

func TestACMEConsentIsLocalAndDoesNotCauseCooldown(t *testing.T) {
	previous := certmagic.DefaultACME
	defer func() { certmagic.DefaultACME = previous }()
	configureACMEAccountConsent(Config{})
	_, err := certmagic.DefaultACME.NewAccountFunc(context.Background(), nil, acme.Account{})
	if err == nil || !acmeRetryTime(err, time.Now()).Until.IsZero() {
		t.Fatal("la aceptación pendiente provoca espera o no se solicita", err)
	}
	configureACMEAccountConsent(Config{ACMEAgreeToTerms: true})
	if _, err = certmagic.DefaultACME.NewAccountFunc(context.Background(), nil, acme.Account{}); err != nil || !certmagic.DefaultACME.Agreed {
		t.Fatal(err)
	}
	password := "fixture consent transfer password"
	profile, err := configtransfer.Export(map[string]string{"acme.agree_to_terms": "true", "domain.base_domain": "example.test"}, false, password)
	if err != nil {
		t.Fatal(err)
	}
	changes, err := portableChanges(profile, password)
	if err != nil {
		t.Fatal(err)
	}
	if _, found := changes["acme.agree_to_terms"]; found {
		t.Fatal("se importó una aceptación de otra instalación")
	}
	path := filepath.Join(t.TempDir(), "gateway.sqlite")
	t.Setenv("GATEWAY_BOOTSTRAP_FILE", "")
	if err = ensureSetupDatabase(path); err != nil {
		t.Fatal(err)
	}
	cfg, err := loadConfig(path)
	if err != nil || cfg.ACMEAgreeToTerms {
		t.Fatal("se aceptaron términos por defecto", err)
	}
	runtime := &gatewayRuntime{}
	runtime.cfg.Store(&cfg)
	controller := adminController{configPath: path, runtime: runtime}
	if err = controller.UpdateSettings(context.Background(), map[string]string{"acme.agree_to_terms": "true"}); err != nil {
		t.Fatal(err)
	}
	cfg, err = loadConfig(path)
	if err != nil || !cfg.ACMEAgreeToTerms {
		t.Fatal("no se conservó la elección local", err)
	}
}
