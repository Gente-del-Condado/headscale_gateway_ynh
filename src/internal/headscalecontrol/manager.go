package headscalecontrol

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"sync"
	"time"
)

type Snapshot struct{ Config, Records []byte }

type TransactionError struct{ Recovered bool }

func (e *TransactionError) Error() string {
	if e.Recovered {
		return "cambio rechazado; configuración anterior restaurada"
	}
	return "queda una recuperación local pendiente"
}

// Backend encapsula los privilegios locales. Transact debe guardar un diario
// recuperable antes de escribir y restaurarlo incluso si desaparece el cliente.
// El transporte remoto consume este mismo contrato HTTP; no ejecuta órdenes.
type Backend interface {
	Read(context.Context) (Snapshot, error)
	Transact(context.Context, Snapshot, Snapshot, bool, func(string)) error
}

type Preview struct {
	Document        Document `json:"document"`
	RestartRequired bool     `json:"restart_required"`
	CurrentRevision string   `json:"current_revision"`
}

type Operation struct {
	ID         string     `json:"id"`
	State      string     `json:"state"`
	StartedAt  time.Time  `json:"started_at"`
	FinishedAt *time.Time `json:"finished_at,omitempty"`
	Error      string     `json:"error,omitempty"`
}

type Manager struct {
	backend         Backend
	instance        string
	apiOrigin       string
	recordsWritable bool
	mu              sync.Mutex
	active          bool
	jobs            []Operation
	idle            chan struct{}
}

func NewManager(backend Backend, instance string, recordsWritable bool, apiOrigin ...string) *Manager {
	idle := make(chan struct{})
	close(idle)
	m := &Manager{backend: backend, instance: instance, recordsWritable: recordsWritable, idle: idle}
	if len(apiOrigin) > 0 {
		m.apiOrigin = apiOrigin[0]
	}
	return m
}

func (m *Manager) Document(ctx context.Context) (Document, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.active {
		return Document{}, errors.New("hay un cambio Headscale en curso; consulta su operación antes de cargar otro documento")
	}
	s, e := m.backend.Read(ctx)
	if e != nil {
		return Document{}, errors.New("no se pudo leer la configuración local de Headscale")
	}
	p, e := parse(s.Config, s.Records, m.recordsWritable)
	if e != nil {
		return Document{}, e
	}
	p.document.Instance = m.instance
	if m.apiOrigin != "" {
		p.document.CoordinatorOrigin = m.apiOrigin
	}
	return p.document, nil
}

func (m *Manager) candidate(ctx context.Context, change Change) (Snapshot, Snapshot, Preview, error) {
	before, e := m.backend.Read(ctx)
	if e != nil {
		return Snapshot{}, Snapshot{}, Preview{}, errors.New("no se pudo leer la configuración local de Headscale")
	}
	config, records, restart, e := prepare(before.Config, before.Records, m.recordsWritable, change)
	if e != nil {
		return Snapshot{}, Snapshot{}, Preview{}, e
	}
	p, e := parse(config, records, m.recordsWritable)
	if e != nil {
		return Snapshot{}, Snapshot{}, Preview{}, e
	}
	p.document.Instance = m.instance
	if m.apiOrigin != "" {
		p.document.CoordinatorOrigin = m.apiOrigin
	}
	return before, Snapshot{config, records}, Preview{p.document, restart, change.Revision}, nil
}

func (m *Manager) Preview(ctx context.Context, change Change) (Preview, error) {
	_, _, p, e := m.candidate(ctx, change)
	return p, e
}

// Apply devuelve un identificador antes de reiniciar el coordinador. La tarea
// tiene plazo propio y no hereda la cancelación HTTP: perder la VPN no debe
// interrumpir una restauración ni dejar Headscale en un estado a medias.
func (m *Manager) Apply(ctx context.Context, change Change) (Operation, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.active {
		return Operation{}, errors.New("ya hay un cambio Headscale en curso")
	}
	before, after, preview, e := m.candidate(ctx, change)
	if e != nil {
		return Operation{}, e
	}
	var id [16]byte
	if _, e = rand.Read(id[:]); e != nil {
		return Operation{}, errors.New("no se pudo identificar la operación")
	}
	op := Operation{ID: hex.EncodeToString(id[:]), State: "queued", StartedAt: time.Now().UTC()}
	m.active = true
	m.idle = make(chan struct{})
	if len(m.jobs) >= 16 {
		m.jobs = m.jobs[len(m.jobs)-15:]
	}
	m.jobs = append(m.jobs, op)
	go func() {
		work, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
		defer cancel()
		update := func(state string) {
			m.mu.Lock()
			defer m.mu.Unlock()
			for i := range m.jobs {
				if m.jobs[i].ID == op.ID {
					m.jobs[i].State = state
				}
			}
		}
		err := m.backend.Transact(work, before, after, preview.RestartRequired, update)
		m.mu.Lock()
		defer m.mu.Unlock()
		m.active = false
		close(m.idle)
		now := time.Now().UTC()
		for i := range m.jobs {
			if m.jobs[i].ID == op.ID {
				m.jobs[i].FinishedAt = &now
				if err != nil {
					m.jobs[i].State = "failed"
					m.jobs[i].Error = "El cambio no se completó. Consulta el estado local de recuperación del controlador."
					var transaction *TransactionError
					if errors.As(err, &transaction) {
						if transaction.Recovered {
							m.jobs[i].State = "rolled_back"
							m.jobs[i].Error = "El cambio fue rechazado y se restauró la configuración anterior."
						} else {
							m.jobs[i].State = "recovery_required"
							m.jobs[i].Error = "Headscale requiere recuperación local; el diario se conserva y no se aceptan nuevos cambios."
						}
					}
				} else {
					m.jobs[i].State = "completed"
				}
			}
		}
	}()
	return op, nil
}

func (m *Manager) Wait(ctx context.Context) error {
	m.mu.Lock()
	idle := m.idle
	m.mu.Unlock()
	select {
	case <-idle:
		return nil
	case <-ctx.Done():
		return ctx.Err()
	}
}

func (m *Manager) Operation(id string) (Operation, bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	for _, op := range m.jobs {
		if op.ID == id {
			return op, true
		}
	}
	return Operation{}, false
}

// CoordinatorOrigin no depende del historial de operaciones. Puede consultarse
// durante una aplicación para verificar el vínculo sin impedir su seguimiento.
func (m *Manager) CoordinatorOrigin(ctx context.Context) (string, error) {
	if m.apiOrigin != "" {
		return m.apiOrigin, nil
	}
	snapshot, e := m.backend.Read(ctx)
	if e != nil {
		return "", errors.New("no se pudo verificar la identidad del coordinador")
	}
	p, e := parse(snapshot.Config, snapshot.Records, m.recordsWritable)
	if e != nil {
		return "", e
	}
	return p.document.CoordinatorOrigin, nil
}
