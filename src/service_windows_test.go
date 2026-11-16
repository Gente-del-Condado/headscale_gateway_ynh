//go:build windows

package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"

	"golang.org/x/sys/windows/svc"
)

func TestWindowsServiceStopsCommonEngine(t *testing.T) {
	previous := processContext
	defer func() { processContext = previous }()
	requests := make(chan svc.ChangeRequest, 1)
	statuses := make(chan svc.Status, 8)
	result := make(chan uint32, 1)
	closed := make(chan struct{})
	handler := gatewayWindowsService{run: func() { <-processContext.Done(); close(closed) }}
	go func() {
		specific, code := handler.Execute(nil, requests, statuses)
		if specific {
			code += 100
		}
		result <- code
	}()
	for {
		if (<-statuses).State == svc.Running {
			break
		}
	}
	requests <- svc.ChangeRequest{Cmd: svc.Stop}
	select {
	case code := <-result:
		if code != 0 {
			t.Fatal(code)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("SCM stop did not stop the engine")
	}
	select {
	case <-closed:
	default:
		t.Fatal("common engine not stopped")
	}
}

// La aceptación que crea servicios solo se ejecuta en el runner Windows
// desechable de GitHub. Nunca instala un servicio al ejecutar go test en un PC.
func TestWindowsServiceInstallerInDisposableRunner(t *testing.T) {
	if os.Getenv("GITHUB_ACTIONS") != "true" || os.Getenv("RUNNER_TEMP") == "" || os.Getenv("RUNNER_ENVIRONMENT") != "github-hosted" {
		t.Skip("requires disposable GitHub Windows runner")
	}
	root := t.TempDir()
	packageDir := filepath.Join(root, "package")
	if err := os.Mkdir(packageDir, 0700); err != nil {
		t.Fatal(err)
	}
	binary := filepath.Join(packageDir, "headscale-gateway.exe")
	build := exec.Command("go", "build", "-p", "2", "-buildvcs=false", "-o", binary, ".")
	if out, err := build.CombinedOutput(); err != nil {
		t.Fatalf("build: %s %v", out, err)
	}
	fixture := filepath.Join(root, "status-links")
	prepare := exec.Command("python", "../tools/prepare_status_links_lab.py", "--output", fixture)
	if out, err := prepare.CombinedOutput(); err != nil {
		t.Fatalf("preparar enlaces: %s %v", out, err)
	}
	cmd := exec.Command("powershell.exe", "-NoProfile", "-NonInteractive", "-File", "../tools/check_windows_service.ps1", "-Package", packageDir, "-Root", root, "-StatusFixture", fixture)
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("SCM acceptance: %s %v", out, err)
	} else {
		t.Log(string(out))
	}
}
