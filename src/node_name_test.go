package main

import (
	"context"
	"github.com/gentedelcondado/headscale-gateway/internal/configtransfer"
	"path/filepath"
	"testing"
)

func TestNodeNameConfirmationBeforeFirstVPN(t *testing.T) {
	t.Setenv("GATEWAY_BOOTSTRAP_FILE", "")
	path := filepath.Join(t.TempDir(), "gateway.sqlite")
	if err := ensureSetupDatabase(path); err != nil {
		t.Fatal(err)
	}
	cfg, err := loadConfig(path)
	if err != nil || !cfg.NodeNamePending || !validRequestedNodeName(cfg.NodeName) || setupReason(cfg) == nil {
		t.Fatal(cfg.NodeName, cfg.NodeNamePending, err)
	}
	runtime := &gatewayRuntime{}
	runtime.cfg.Store(&cfg)
	controller := adminController{configPath: path, runtime: runtime}
	if err = controller.UpdateSettings(context.Background(), map[string]string{"headscale.node_name": "tablet-casa"}); err != nil {
		t.Fatal(err)
	}
	cfg, err = loadConfig(path)
	if err != nil || cfg.NodeNamePending || cfg.NodeName != "tablet-casa" {
		t.Fatal(cfg, err)
	}
	// La propuesta no modifica el nombre que fija la carpeta de identidad.
	stable, err := stateHostname(path, nil, "original-device")
	if err != nil {
		t.Fatal(err)
	}
	if err = controller.UpdateSettings(context.Background(), map[string]string{"headscale.node_name": "tablet-new"}); err != nil {
		t.Fatal(err)
	}
	again, err := stateHostname(path, nil, "different-device")
	if err != nil || stable != again {
		t.Fatal("identity changed", again, err)
	}
}

func TestConfigurationProfileDoesNotReplaceDeviceName(t *testing.T) {
	password := "fixture password for profile"
	profile, err := configtransfer.Export(map[string]string{"headscale.node_name": "other-device", "headscale.url": "https://headscale.example.test"}, false, password)
	if err != nil {
		t.Fatal(err)
	}
	changes, err := portableChanges(profile, password)
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := changes["headscale.node_name"]; ok {
		t.Fatal("profile replaced the device name")
	}
	if changes["headscale.url"] != "https://headscale.example.test" {
		t.Fatal(changes)
	}
}

func TestRequestedNodeNameAndLegacyCompatibility(t *testing.T) {
	for _, name := range []string{"", "PC", "-pc", "pc-", "pc.example.net", "../pc", "pc--1"} {
		if validRequestedNodeName(name) {
			t.Fatal(name)
		}
	}
	for _, name := range []string{"pc", "pc-1", "tablet-casa"} {
		if !validRequestedNodeName(name) {
			t.Fatal(name)
		}
	}
	path := filepath.Join(t.TempDir(), "gateway.sqlite")
	db, err := openCatalog(path)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	settings := initialSettings()
	if err = db.ReplaceSettings(settings); err != nil {
		t.Fatal(err)
	}
	cfg, err := configFromSettings(path, settings, db)
	if err != nil || cfg.NodeNamePending {
		t.Fatal("legacy installation must not request confirmation", err)
	}
}
