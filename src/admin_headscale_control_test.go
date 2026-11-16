package main

import (
	"bytes"
	"context"
	"github.com/gentedelcondado/headscale-gateway/internal/configtransfer"
	"os"
	"strings"
	"testing"
)

func TestDelegatedHeadscaleTokenIsEncryptedRedactedAndOptionalInProfiles(t *testing.T) {
	_, a := portalFixture(t)
	db, e := openCatalog(a.configPath)
	if e != nil {
		t.Fatal(e)
	}
	values := initialSettings()
	token := "hgk_" + strings.Repeat("a", 64)
	values["headscale.control.token"] = token
	values["headscale.control.mode"] = "remote"
	if e = db.ReplaceSettings(values); e != nil {
		t.Fatal(e)
	}
	db.Close()
	raw, e := os.ReadFile(a.configPath)
	if e != nil {
		t.Fatal(e)
	}
	if bytes.Contains(raw, []byte(token)) {
		t.Fatal("el token se guardó en claro")
	}
	settings, e := a.Settings(context.Background())
	if e != nil {
		t.Fatal(e)
	}
	if settings.(map[string]string)["headscale.control.token"] != "" {
		t.Fatal("el token salió hacia el navegador")
	}
	for _, secrets := range []bool{false, true} {
		payload, e := a.ExportConfiguration(context.Background(), secrets, "laboratorio-perfil-seguro")
		if e != nil {
			t.Fatal(e)
		}
		profile, e := configtransfer.Import(payload, "laboratorio-perfil-seguro")
		if e != nil {
			t.Fatal(e)
		}
		if (profile.Settings["headscale.control.mode"] == "remote") != secrets {
			t.Fatal("un perfil sin token activó una delegación remota")
		}
		if (profile.Settings["headscale.control.token"] == token) != secrets {
			t.Fatal("el perfil no respetó la selección de secretos")
		}
	}
}

func TestLocalHeadscaleBindingCannotBeSelectedByPortableSettings(t *testing.T) {
	for _, path := range []string{"", "relative/control.sock", "/tmp/control.sock", "/run/headscale-gateway-control/lab/../other/control.sock", "/run/headscale-gateway-control/lab/not-a-socket"} {
		t.Setenv("HGW_HEADSCALE_CONTROL_SOCKET", path)
		if localHeadscaleControlSocket() != "" {
			t.Fatal("se aceptó un vínculo local fuera del registro", path)
		}
	}
	t.Setenv("HGW_HEADSCALE_CONTROL_SOCKET", "")
	_, a := portalFixture(t)
	cfg := a.runtime.currentConfig()
	cfg.HeadscaleControlMode = "local"
	a.runtime.cfg.Store(&cfg)
	if a.HeadscaleControlIsLocal() {
		t.Fatal("un ajuste de SQLite concedió privilegio local sin instalador")
	}
	if _, e := a.HeadscaleControlInfo(context.Background()); e == nil {
		t.Fatal("el modo local sin vínculo apareció disponible")
	}
}
