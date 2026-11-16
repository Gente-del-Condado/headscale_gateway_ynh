//go:build linux && !android

package headscalecontrol

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func diskFixture(t *testing.T) *DiskBackend {
	t.Helper()
	if os.Geteuid() != 0 {
		t.Skip("prueba privilegiada: ejecutar el binario de pruebas en la VM de laboratorio")
	}
	dir := t.TempDir()
	config := filepath.Join(dir, "config.yaml")
	records := filepath.Join(dir, "records.json")
	if e := os.WriteFile(config, []byte(exampleConfig), 0600); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(records, []byte("[]\n"), 0640); e != nil {
		t.Fatal(e)
	}
	return &DiskBackend{spec: Spec{ConfigPath: config, RecordsPath: records, StateDir: dir}, validate: func(context.Context, Snapshot) error { return nil }, restart: func(context.Context) error { return nil }, healthy: func(context.Context) error { return nil }}
}

func TestDiskRejectsFailedValidationWithoutWriting(t *testing.T) {
	b := diskFixture(t)
	before, e := b.Read(context.Background())
	if e != nil {
		t.Fatal(e)
	}
	b.validate = func(context.Context, Snapshot) error { return errors.New("candidato rechazado") }
	after := Snapshot{append(append([]byte(nil), before.Config...), []byte("# cambiado\n")...), before.Records}
	if e = b.Transact(context.Background(), before, after, true, func(string) {}); e == nil {
		t.Fatal("se aceptó la validación fallida")
	}
	current, _ := b.Read(context.Background())
	if !bytes.Equal(current.Config, before.Config) {
		t.Fatal("se escribió antes de validar")
	}
	if _, e = os.Lstat(b.journalPath()); !os.IsNotExist(e) {
		t.Fatal("se dejó un diario sin aplicar")
	}
}

func TestDiskRollsBackConfigurationAndRecordsAfterFailure(t *testing.T) {
	b := diskFixture(t)
	before, e := b.Read(context.Background())
	if e != nil {
		t.Fatal(e)
	}
	restarts, checks := 0, 0
	b.restart = func(context.Context) error { restarts++; return nil }
	b.healthy = func(context.Context) error {
		checks++
		if checks == 1 {
			return errors.New("salud fallida")
		}
		return nil
	}
	after := Snapshot{append(append([]byte(nil), before.Config...), []byte("# cambiado\n")...), []byte("[{\"name\":\"test.example.test\",\"type\":\"A\",\"value\":\"100.64.0.7\"}]\n")}
	if e = b.Transact(context.Background(), before, after, true, func(string) {}); e == nil {
		t.Fatal("se declaró éxito sin salud")
	}
	current, _ := b.Read(context.Background())
	if !bytes.Equal(current.Config, before.Config) || !bytes.Equal(current.Records, before.Records) || restarts != 2 || checks != 2 {
		t.Fatal("recuperación incompleta")
	}
	if _, e = os.Lstat(b.journalPath()); !os.IsNotExist(e) {
		t.Fatal("diario no retirado después de recuperar")
	}
}

func TestDiskRecoversInterruptedCommitAndProtectsExternalEdits(t *testing.T) {
	b := diskFixture(t)
	config, records, e := b.images()
	if e != nil {
		t.Fatal(e)
	}
	after := Snapshot{append(append([]byte(nil), config.Data...), []byte("# candidato\n")...), []byte("[]")}
	entry := journal{BeforeConfig: config, BeforeRecords: records, After: after, Restart: true}
	data, _ := json.Marshal(entry)
	if e = writeImage(b.journalPath(), fileImage{Data: data, Mode: 0600, UID: 0, GID: 0}); e != nil {
		t.Fatal(e)
	}
	modified := config
	modified.Data = after.Config
	if e = writeImage(b.spec.ConfigPath, modified); e != nil {
		t.Fatal(e)
	}
	if e = b.Recover(context.Background()); e != nil {
		t.Fatal(e)
	}
	current, _ := b.Read(context.Background())
	if !bytes.Equal(current.Config, config.Data) {
		t.Fatal("el arranque no recuperó el candidato interrumpido")
	}
	if e = writeImage(b.journalPath(), fileImage{Data: data, Mode: 0600, UID: 0, GID: 0}); e != nil {
		t.Fatal(e)
	}
	modified.Data = []byte("# edición de otro administrador\n")
	if e = writeImage(b.spec.ConfigPath, modified); e != nil {
		t.Fatal(e)
	}
	if e = b.Recover(context.Background()); e == nil {
		t.Fatal("se sobrescribió una edición externa")
	}
	current, _ = b.Read(context.Background())
	if !bytes.Equal(current.Config, modified.Data) {
		t.Fatal("se perdió la edición externa")
	}
}
