//go:build linux && !android

package headscalecontrol

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

func TestLocalFilesRejectLinksAndPreserveMetadata(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.yaml")
	if e := os.WriteFile(path, []byte(exampleConfig), 0640); e != nil {
		t.Fatal(e)
	}
	original, e := readImage(path)
	if e != nil {
		t.Fatal(e)
	}
	next := original
	next.Data = append(append([]byte(nil), original.Data...), []byte("# conservado\n")...)
	if e = writeImage(path, next); e != nil {
		t.Fatal(e)
	}
	actual, e := readImage(path)
	if e != nil {
		t.Fatal(e)
	}
	if actual.UID != original.UID || actual.GID != original.GID || actual.Mode != original.Mode || !bytes.Equal(actual.Data, next.Data) {
		t.Fatal("se perdieron metadatos al guardar")
	}
	link := filepath.Join(dir, "symlink")
	if e = os.Symlink(path, link); e != nil {
		t.Fatal(e)
	}
	if _, e = readImage(link); e == nil {
		t.Fatal("se leyó un enlace simbólico")
	}
	parent := filepath.Join(dir, "parent-link")
	if e = os.Symlink(dir, parent); e != nil {
		t.Fatal(e)
	}
	if e = writeImage(filepath.Join(parent, "escape"), next); e == nil {
		t.Fatal("se escribió a través de una carpeta enlazada")
	}
	hard := filepath.Join(dir, "hard-link")
	if e = os.Link(path, hard); e != nil {
		t.Fatal(e)
	}
	if _, e = readImage(path); e == nil {
		t.Fatal("se aceptó un archivo compartido por enlace duro")
	}
}
