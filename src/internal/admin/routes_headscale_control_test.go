package admin

import (
	"context"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/gentedelcondado/headscale-gateway/internal/headscalecontrol"
	"github.com/gentedelcondado/headscale-gateway/internal/state"
)

type fakeHeadscaleControl struct {
	fakeHeadscaleManagement
	local bool
	calls int
}

func (f *fakeHeadscaleControl) HeadscaleControlIsLocal() bool { return f.local }
func (f *fakeHeadscaleControl) HeadscaleControlInfo(context.Context) (headscalecontrol.Info, error) {
	return headscalecontrol.Info{Mode: "local", CanWrite: true}, nil
}
func (f *fakeHeadscaleControl) HeadscaleControlDocument(context.Context) (headscalecontrol.Document, error) {
	return headscalecontrol.Document{Revision: strings.Repeat("a", 64)}, nil
}
func (f *fakeHeadscaleControl) HeadscaleControlPreview(context.Context, headscalecontrol.Change) (headscalecontrol.Preview, error) {
	return headscalecontrol.Preview{}, nil
}
func (f *fakeHeadscaleControl) HeadscaleControlApply(context.Context, headscalecontrol.Change) (headscalecontrol.Operation, error) {
	f.calls++
	return headscalecontrol.Operation{ID: strings.Repeat("b", 32)}, nil
}
func (f *fakeHeadscaleControl) HeadscaleControlOperation(context.Context, string) (headscalecontrol.Operation, error) {
	return headscalecontrol.Operation{}, nil
}

func TestHeadscaleDelegationRequiresSpecificScopeAndExplicitExposure(t *testing.T) {
	db, e := state.Open(filepath.Join(t.TempDir(), "state.sqlite"))
	if e != nil {
		t.Fatal(e)
	}
	defer db.Close()
	f := &fakeHeadscaleControl{local: true}
	s, e := New(strings.Repeat("R", 64), f)
	if e != nil {
		t.Fatal(e)
	}
	if e = s.WithState(db); e != nil {
		t.Fatal(e)
	}
	makeToken := func(role string, scopes ...string) string {
		v, _, e := db.NewToken("control-lab", role, scopes, time.Hour)
		if e != nil {
			t.Fatal(e)
		}
		return v
	}
	legacy := makeToken("operator", "network")
	read := makeToken("viewer", "headscale-read")
	write := makeToken("operator", "headscale-read", "headscale-write")
	h := s.Handler()
	call := func(method, path, token, body string) *httptest.ResponseRecorder {
		r := httptest.NewRequest(method, path, strings.NewReader(body))
		r.RemoteAddr = "127.0.0.1:1234"
		if token != "" {
			r.Header.Set("Authorization", "Bearer "+token)
		}
		r.Header.Set("Content-Type", "application/json")
		r.Header.Set("X-Forwarded-User", "admin")
		r.Header.Set("X-Forwarded-For", "127.0.0.1")
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		return w
	}
	for _, token := range []string{legacy, read, write} {
		if w := call("GET", "/api/v1/network/control/document", token, ""); w.Code != 403 {
			t.Fatalf("exposición implícita: %d", w.Code)
		}
	}
	if w := call("POST", "/api/v1/network/control/apply", "", `{}`); w.Code != 401 {
		t.Fatalf("loopback/cabecera acreditó una identidad: %d", w.Code)
	}
	p := s.policy.Get()
	p.TokenHeadscaleRead = true
	p.TokenHeadscaleWrite = true
	if e = s.policy.Update(p); e != nil {
		t.Fatal(e)
	}
	if w := call("GET", "/api/v1/network/control/document", read, ""); w.Code != 200 {
		t.Fatalf("lectura: %d %s", w.Code, w.Body.String())
	}
	if w := call("GET", "/api/v1/network/control/info", read, ""); w.Code != 200 || !strings.Contains(w.Body.String(), `"can_write":false`) {
		t.Fatalf("se anunciaron derechos de escritura al lector: %d %s", w.Code, w.Body.String())
	}
	if w := call("POST", "/api/v1/network/control/apply", read, `{}`); w.Code != 403 {
		t.Fatalf("el lector pudo modificar: %d", w.Code)
	}
	if w := call("POST", "/api/v1/network/control/apply", legacy, `{}`); w.Code != 403 {
		t.Fatalf("el alcance network obtuvo control privilegiado: %d", w.Code)
	}
	if w := call("POST", "/api/v1/network/control/apply", write, `{"path":"/etc/shadow"}`); w.Code != 400 {
		t.Fatalf("ruta arbitraria admitida: %d", w.Code)
	}
	if w := call("POST", "/api/v1/network/control/apply", write, `{}`); w.Code != 202 || f.calls != 1 {
		t.Fatalf("delegación: %d, %d", w.Code, f.calls)
	}
	if w := call("PUT", "/api/v1/config", write, `{}`); w.Code != 403 {
		t.Fatalf("la delegación pudo configurar el Gateway: %d", w.Code)
	}
	if w := call("GET", "/api/v1/auth/settings", write, ""); w.Code != 403 {
		t.Fatalf("la delegación obtuvo identidad: %d", w.Code)
	}
	f.local = false
	if w := call("POST", "/api/v1/network/control/apply", write, `{}`); w.Code != 403 || f.calls != 1 {
		t.Fatalf("delegación transitiva: %d, %d", w.Code, f.calls)
	}
	f.local = true
	auth, e := NewAuthManagerSQLite(db)
	if e != nil {
		t.Fatal(e)
	}
	if e = auth.Update(AuthUpdate{Mode: "local", LocalUsername: "labadmin", LocalPassword: "laboratorio-password-largo"}); e != nil {
		t.Fatal(e)
	}
	s.WithAuth(auth)
	p.TokenHeadscaleRead = false
	p.TokenHeadscaleWrite = false
	if e = s.policy.Update(p); e != nil {
		t.Fatal(e)
	}
	sessionCall := func(role string, withCSRF bool) *httptest.ResponseRecorder {
		login := httptest.NewRequest("GET", "http://gateway.example.test/admin/", nil)
		cookie := httptest.NewRecorder()
		csrf := auth.CreateSessionRole(cookie, login, "lab-user", role)
		r := httptest.NewRequest("POST", "http://gateway.example.test/api/v1/network/control/apply", strings.NewReader(`{}`))
		r.Header.Set("Content-Type", "application/json")
		for _, c := range cookie.Result().Cookies() {
			r.AddCookie(c)
		}
		if withCSRF {
			r.Header.Set("X-CSRF-Token", csrf)
		}
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		return w
	}
	if w := sessionCall("operator", true); w.Code != 403 {
		t.Fatalf("la sesión operator heredó poderes del controlador: %d", w.Code)
	}
	if w := sessionCall("admin", false); w.Code != 401 {
		t.Fatalf("administrador sin CSRF: %d", w.Code)
	}
	if w := sessionCall("admin", true); w.Code != 202 {
		t.Fatalf("el panel legítimo dependió de habilitar Bearer: %d %s", w.Code, w.Body.String())
	}
}
