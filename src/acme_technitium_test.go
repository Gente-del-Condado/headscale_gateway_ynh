package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	technitium "github.com/gentedelcondado/headscale-gateway/internal/acmednstechnitium"
	"github.com/libdns/libdns"
)

func TestTechnitiumDNS01DoesNotExposeTokenInProviderErrors(t *testing.T) {
	const secret = "fixture-private-dns-token"
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]string{"status": "error", "errorMessage": "invalid credential " + secret})
	}))
	defer server.Close()
	provider := &technitiumDNS01Provider{inner: &technitium.Provider{ServerURL: server.URL, APIToken: secret, StaleRecordTimeout: -1}}
	records := []libdns.Record{libdns.TXT{Name: "_acme-challenge.pc1", Text: "fixture-challenge"}}
	for _, operation := range []func(context.Context, string, []libdns.Record) ([]libdns.Record, error){provider.AppendRecords, provider.DeleteRecords} {
		_, err := operation(context.Background(), "example.test", records)
		if err == nil || strings.Contains(err.Error(), secret) || strings.Contains(err.Error(), server.URL) {
			t.Fatalf("error inseguro: %v", err)
		}
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := provider.AppendRecords(ctx, "example.test", records); err != context.Canceled {
		t.Fatalf("se perdió la cancelación: %v", err)
	}
}
