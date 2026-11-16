package headscalecontrol

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"
)

type fakeBackend struct {
	mu               sync.Mutex
	snapshot         Snapshot
	started, release chan struct{}
	fail             bool
}

func (b *fakeBackend) Read(context.Context) (Snapshot, error) {
	b.mu.Lock()
	defer b.mu.Unlock()
	return Snapshot{append([]byte(nil), b.snapshot.Config...), append([]byte(nil), b.snapshot.Records...)}, nil
}
func (b *fakeBackend) Transact(ctx context.Context, before, after Snapshot, restart bool, notify func(string)) error {
	notify("validating")
	close(b.started)
	select {
	case <-b.release:
	case <-ctx.Done():
		return ctx.Err()
	}
	if b.fail {
		notify("rolling_back")
		return errors.New("SECRET-ROOT-ERROR")
	}
	b.mu.Lock()
	b.snapshot = after
	b.mu.Unlock()
	notify("checking")
	return nil
}

func TestOperationSurvivesClientCancellationAndSerializesChanges(t *testing.T) {
	b := &fakeBackend{snapshot: Snapshot{[]byte(exampleConfig), []byte("[]")}, started: make(chan struct{}), release: make(chan struct{})}
	m := NewManager(b, "headscale-lab", true)
	d, e := m.Document(context.Background())
	if e != nil {
		t.Fatal(e)
	}
	dns := d.DNS
	dns.Nameservers.Global = []string{"9.9.9.9"}
	change := Change{Revision: d.Revision, DNS: &dns}
	ctx, cancel := context.WithCancel(context.Background())
	op, e := m.Apply(ctx, change)
	if e != nil {
		t.Fatal(e)
	}
	<-b.started
	cancel()
	if origin, e := m.CoordinatorOrigin(context.Background()); e != nil || origin != "https://control.example.test" {
		t.Fatal("no se pudo verificar el coordinador mientras se aplicaba un cambio", e)
	}
	if _, e = m.Apply(context.Background(), change); e == nil {
		t.Fatal("se aceptaron cambios concurrentes")
	}
	close(b.release)
	deadline := time.Now().Add(time.Second)
	for time.Now().Before(deadline) {
		result, _ := m.Operation(op.ID)
		if result.State == "completed" {
			return
		}
		time.Sleep(time.Millisecond)
	}
	t.Fatal("la cancelación del cliente interrumpió la tarea")
}

func TestOperationDoesNotPublishBackendSecrets(t *testing.T) {
	b := &fakeBackend{snapshot: Snapshot{[]byte(exampleConfig), []byte("[]")}, started: make(chan struct{}), release: make(chan struct{}), fail: true}
	m := NewManager(b, "headscale-lab", true)
	d, _ := m.Document(context.Background())
	dns := d.DNS
	dns.MagicDNS = false
	op, e := m.Apply(context.Background(), Change{Revision: d.Revision, DNS: &dns})
	if e != nil {
		t.Fatal(e)
	}
	close(b.release)
	deadline := time.Now().Add(time.Second)
	for time.Now().Before(deadline) {
		result, _ := m.Operation(op.ID)
		if result.State == "failed" {
			if result.Error == "" || result.Error == "SECRET-ROOT-ERROR" {
				t.Fatal("error sin sanear")
			}
			return
		}
		time.Sleep(time.Millisecond)
	}
	t.Fatal("la tarea no terminó")
}

func TestRootBindingOverridesPublishedOriginWithoutChangingHeadscale(t *testing.T) {
	b := &fakeBackend{snapshot: Snapshot{[]byte(exampleConfig), []byte("[]")}}
	m := NewManager(b, "lab", true, "http://127.0.0.1:8080")
	doc, e := m.Document(context.Background())
	if e != nil || doc.CoordinatorOrigin != "http://127.0.0.1:8080" {
		t.Fatal("no se conservó el enlace del instalador", e)
	}
	if origin, e := m.CoordinatorOrigin(context.Background()); e != nil || origin != doc.CoordinatorOrigin {
		t.Fatal("identidad incoherente", e)
	}
	if string(b.snapshot.Config) != exampleConfig {
		t.Fatal("el enlace modificó el coordinador")
	}
}
