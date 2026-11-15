package diagnostics

import (
	"bytes"
	"errors"
	"io"
	"strings"
	"testing"
)

type brokenConsole struct{}

func (brokenConsole) Write([]byte) (int, error) { return 0, errors.New("no console") }

func TestMissingConsoleStillWritesRedactedPersistentLog(t *testing.T) {
	var persistent bytes.Buffer
	writer := redactedWriter{io.MultiWriter(optionalConsoleWriter{brokenConsole{}}, &persistent)}
	input := []byte("startup password=fixture-secret message=ready")
	if n, err := writer.Write(input); err != nil || n != len(input) {
		t.Fatalf("write: %d %v", n, err)
	}
	if got := persistent.String(); strings.Contains(got, "fixture-secret") || !strings.Contains(got, "message=ready") {
		t.Fatalf("persistent redaction: %q", got)
	}
	failed := redactedWriter{io.MultiWriter(optionalConsoleWriter{brokenConsole{}}, brokenConsole{})}
	if _, err := failed.Write(input); err == nil {
		t.Fatal("persistent error was swallowed")
	}
}
