package headscalecontrol

import (
	"encoding/json"
	"io"
	"net/http"
)

func jsonReply(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func decodeChange(w http.ResponseWriter, r *http.Request) (Change, bool) {
	var change Change
	if r.Header.Get("Content-Type") != "application/json" {
		jsonReply(w, 415, map[string]string{"error": "se requiere JSON"})
		return change, false
	}
	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, MaxDocument))
	decoder.DisallowUnknownFields()
	if decoder.Decode(&change) != nil {
		jsonReply(w, 400, map[string]string{"error": "cambio Headscale inválido"})
		return change, false
	}
	var more any
	if decoder.Decode(&more) != io.EOF {
		jsonReply(w, 400, map[string]string{"error": "cambio Headscale ambiguo"})
		return change, false
	}
	return change, true
}

// Handler solo se expone por el socket local autenticado por el SO. La API web
// del Gateway añade por separado sesión/CSRF o delegación administrativa.
func (m *Manager) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /identity", func(w http.ResponseWriter, r *http.Request) {
		origin, e := m.CoordinatorOrigin(r.Context())
		if e != nil {
			jsonReply(w, 503, map[string]string{"error": e.Error()})
			return
		}
		jsonReply(w, 200, map[string]string{"coordinator_origin": origin})
	})
	mux.HandleFunc("GET /document", func(w http.ResponseWriter, r *http.Request) {
		value, e := m.Document(r.Context())
		if e != nil {
			jsonReply(w, 503, map[string]string{"error": e.Error()})
			return
		}
		jsonReply(w, 200, value)
	})
	mux.HandleFunc("POST /preview", func(w http.ResponseWriter, r *http.Request) {
		change, ok := decodeChange(w, r)
		if !ok {
			return
		}
		value, e := m.Preview(r.Context(), change)
		if e != nil {
			jsonReply(w, 409, map[string]string{"error": e.Error()})
			return
		}
		jsonReply(w, 200, value)
	})
	mux.HandleFunc("POST /apply", func(w http.ResponseWriter, r *http.Request) {
		change, ok := decodeChange(w, r)
		if !ok {
			return
		}
		value, e := m.Apply(r.Context(), change)
		if e != nil {
			jsonReply(w, 409, map[string]string{"error": e.Error()})
			return
		}
		jsonReply(w, 202, value)
	})
	mux.HandleFunc("GET /operations/{id}", func(w http.ResponseWriter, r *http.Request) {
		value, ok := m.Operation(r.PathValue("id"))
		if !ok {
			jsonReply(w, 404, map[string]string{"error": "operación no disponible en este proceso"})
			return
		}
		jsonReply(w, 200, value)
	})
	return mux
}
