package technitium

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/libdns/libdns"
)

func newTestServer(t *testing.T, handler http.HandlerFunc) (*httptest.Server, *Provider) {
	t.Helper()
	srv := httptest.NewServer(handler)
	p := &Provider{
		ServerURL: srv.URL,
		APIToken:  "test-token",
	}
	return srv, p
}

func TestGetRecords(t *testing.T) {
	srv, p := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/zones/records/get" {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		q := r.URL.Query()
		if q.Get("token") != "test-token" {
			t.Error("token not passed")
		}
		if q.Get("domain") != "example.com" {
			t.Errorf("unexpected domain: %s", q.Get("domain"))
		}

		resp := map[string]any{
			"status": "ok",
			"response": map[string]any{
				"zone": map[string]any{"name": "example.com"},
				"records": []map[string]any{
					{
						"name": "_acme-challenge.example.com",
						"type": "TXT",
						"ttl":  300,
						"rData": map[string]any{
							"text": "challengetoken123",
						},
					},
				},
			},
		}
		json.NewEncoder(w).Encode(resp)
	})
	defer srv.Close()

	records, err := p.GetRecords(context.Background(), "example.com.")
	if err != nil {
		t.Fatalf("GetRecords error: %v", err)
	}
	if len(records) != 1 {
		t.Fatalf("expected 1 record, got %d", len(records))
	}
	txt, ok := records[0].(libdns.TXT)
	if !ok {
		t.Fatalf("expected libdns.TXT, got %T", records[0])
	}
	if txt.Text != "challengetoken123" {
		t.Errorf("unexpected text: %s", txt.Text)
	}
}

func TestAppendRecords(t *testing.T) {
	addCalled := false
	srv, p := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api/zones/records/get":
			// Stale record cleanup query — return empty records
			json.NewEncoder(w).Encode(map[string]any{
				"status": "ok",
				"response": map[string]any{
					"zone":    map[string]any{"name": "example.com"},
					"records": []any{},
				},
			})
		case "/api/zones/records/add":
			q := r.URL.Query()
			if q.Get("token") != "test-token" {
				t.Error("token not passed")
			}
			if q.Get("domain") != "_acme-challenge.example.com" {
				t.Errorf("unexpected domain: %s", q.Get("domain"))
			}
			if q.Get("type") != "TXT" {
				t.Errorf("unexpected type: %s", q.Get("type"))
			}
			if q.Get("text") != "challengetoken" {
				t.Errorf("unexpected text: %s", q.Get("text"))
			}
			if q.Get("ttl") != "300" {
				t.Errorf("unexpected ttl: %s", q.Get("ttl"))
			}
			addCalled = true
			json.NewEncoder(w).Encode(map[string]any{"status": "ok"})
		default:
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
	})
	defer srv.Close()

	records := []libdns.Record{
		libdns.TXT{
			Name: "_acme-challenge",
			Text: "challengetoken",
			TTL:  300 * time.Second,
		},
	}

	added, err := p.AppendRecords(context.Background(), "example.com.", records)
	if err != nil {
		t.Fatalf("AppendRecords error: %v", err)
	}
	if len(added) != 1 {
		t.Fatalf("expected 1 added record, got %d", len(added))
	}
	if !addCalled {
		t.Error("add API was not called")
	}
}

func TestAppendRecords_CleansStaleRecords(t *testing.T) {
	staleTime := time.Now().Add(-15 * time.Minute).UTC().Format(time.RFC3339Nano)
	deleteCalled := false

	srv, p := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api/zones/records/get":
			json.NewEncoder(w).Encode(map[string]any{
				"status": "ok",
				"response": map[string]any{
					"zone": map[string]any{"name": "example.com"},
					"records": []map[string]any{
						{
							"name":         "_acme-challenge.example.com",
							"type":         "TXT",
							"ttl":          120,
							"rData":        map[string]any{"text": "old-stale-token"},
							"lastModified": staleTime,
						},
					},
				},
			})
		case "/api/zones/records/delete":
			q := r.URL.Query()
			if q.Get("text") == "old-stale-token" {
				deleteCalled = true
			}
			json.NewEncoder(w).Encode(map[string]any{"status": "ok"})
		case "/api/zones/records/add":
			json.NewEncoder(w).Encode(map[string]any{"status": "ok"})
		}
	})
	defer srv.Close()

	records := []libdns.Record{
		libdns.TXT{
			Name: "_acme-challenge",
			Text: "new-challenge-token",
			TTL:  120 * time.Second,
		},
	}

	_, err := p.AppendRecords(context.Background(), "example.com.", records)
	if err != nil {
		t.Fatalf("AppendRecords error: %v", err)
	}
	if !deleteCalled {
		t.Error("stale record was not deleted")
	}
}

func TestDeleteRecords(t *testing.T) {
	called := false
	srv, p := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/zones/records/delete" {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		q := r.URL.Query()
		if q.Get("token") != "test-token" {
			t.Error("token not passed")
		}
		if q.Get("domain") != "_acme-challenge.example.com" {
			t.Errorf("unexpected domain: %s", q.Get("domain"))
		}
		if q.Get("type") != "TXT" {
			t.Errorf("unexpected type: %s", q.Get("type"))
		}
		if q.Get("text") != "challengetoken" {
			t.Errorf("expected text param for TXT delete, got: %s", q.Get("text"))
		}
		called = true
		json.NewEncoder(w).Encode(map[string]any{"status": "ok"})
	})
	defer srv.Close()

	records := []libdns.Record{
		libdns.TXT{
			Name: "_acme-challenge",
			Text: "challengetoken",
			TTL:  300 * time.Second,
		},
	}

	deleted, err := p.DeleteRecords(context.Background(), "example.com.", records)
	if err != nil {
		t.Fatalf("DeleteRecords error: %v", err)
	}
	if len(deleted) != 1 {
		t.Fatalf("expected 1 deleted record, got %d", len(deleted))
	}
	if !called {
		t.Error("API was not called")
	}
}

func TestSetRecords(t *testing.T) {
	called := false
	srv, p := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/zones/records/add" {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		q := r.URL.Query()
		if q.Get("token") != "test-token" {
			t.Error("token not passed")
		}
		if q.Get("domain") != "_acme-challenge.example.com" {
			t.Errorf("unexpected domain: %s", q.Get("domain"))
		}
		if q.Get("type") != "TXT" {
			t.Errorf("unexpected type: %s", q.Get("type"))
		}
		if q.Get("text") != "newtoken" {
			t.Errorf("unexpected text: %s", q.Get("text"))
		}
		if q.Get("overwrite") != "true" {
			t.Errorf("expected overwrite=true, got: %s", q.Get("overwrite"))
		}
		called = true
		json.NewEncoder(w).Encode(map[string]any{"status": "ok"})
	})
	defer srv.Close()

	records := []libdns.Record{
		libdns.TXT{
			Name: "_acme-challenge",
			Text: "newtoken",
			TTL:  300 * time.Second,
		},
	}

	set, err := p.SetRecords(context.Background(), "example.com.", records)
	if err != nil {
		t.Fatalf("SetRecords error: %v", err)
	}
	if len(set) != 1 {
		t.Fatalf("expected 1 set record, got %d", len(set))
	}
	if !called {
		t.Error("API was not called")
	}
}

func TestAPIError(t *testing.T) {
	srv, p := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(map[string]any{
			"status":       "error",
			"errorMessage": "invalid token",
		})
	})
	defer srv.Close()

	_, err := p.GetRecords(context.Background(), "example.com.")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}
