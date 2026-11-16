package headscalecontrol

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"net"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
)

func remoteFixture(t *testing.T, handler http.HandlerFunc) (*Client, *http.Transport) {
	t.Helper()
	server := httptest.NewTLSServer(handler)
	t.Cleanup(server.Close)
	u, _ := url.Parse(server.URL)
	roots := x509.NewCertPool()
	roots.AddCert(server.Certificate())
	transport := &http.Transport{TLSClientConfig: &tls.Config{MinVersion: tls.VersionTLS12, RootCAs: roots, ServerName: u.Hostname()}, DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
		return (&net.Dialer{}).DialContext(ctx, "tcp", server.Listener.Addr().String())
	}}
	client, e := NewRemoteClient(transport, server.URL, "delegation-test-only")
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(client.Close)
	return client, transport
}

func TestRemoteClientDoesNotFollowRedirectsOrExposeCredentials(t *testing.T) {
	visited := 0
	other := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { visited++; w.WriteHeader(200) }))
	defer other.Close()
	client, _ := remoteFixture(t, func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer delegation-test-only" {
			t.Error("delegación ausente")
		}
		w.Header().Set("Location", other.URL)
		w.WriteHeader(302)
	})
	if _, e := client.Document(context.Background()); e == nil {
		t.Fatal("se aceptó una redirección")
	}
	if visited != 0 {
		t.Fatal("se enviaron credenciales a un destino redirigido")
	}
	client, _ = remoteFixture(t, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(403)
		_, _ = w.Write([]byte(`{"error":"delegation-test-only"}`))
	})
	if _, e := client.Document(context.Background()); e == nil || strings.Contains(e.Error(), "delegation-test-only") {
		t.Fatalf("error remoto con credenciales: %v", e)
	}
}

func TestRemoteClientRejectsTLSBypassAndUnexpectedDocuments(t *testing.T) {
	client, transport := remoteFixture(t, func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write([]byte(`{"unexpected":true}`)) })
	if _, e := client.Document(context.Background()); e == nil {
		t.Fatal("documento sin revisión aceptado")
	}
	unsafe := transport.Clone()
	unsafe.TLSClientConfig = transport.TLSClientConfig.Clone()
	unsafe.TLSClientConfig.InsecureSkipVerify = true
	origin := strings.TrimSuffix(client.origin, "/api/v1/network/control")
	if _, e := NewRemoteClient(unsafe, origin, "test"); e == nil {
		t.Fatal("TLS inseguro aceptado")
	}
}

func TestRemoteClientRejectsOversizedResponses(t *testing.T) {
	client, _ := remoteFixture(t, func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(strings.Repeat(" ", MaxDocument+1) + `{}`))
	})
	if _, e := client.Document(context.Background()); e == nil {
		t.Fatal("respuesta excesiva aceptada")
	}
}
