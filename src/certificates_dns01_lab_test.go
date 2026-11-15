package main

import (
	"bytes"
	"context"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/sha256"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/json"
	"encoding/pem"
	"io"
	"math/big"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/caddyserver/certmagic"
	"github.com/miekg/dns"
	"go.uber.org/zap"
)

// ACME real contra Pebble, DNS autoritativo local y API Technitium simulada.
// Todos los certificados, claves, dominios y registros son exclusivos del ensayo.
func TestTechnitiumACMELabIssueRenewAndCleanTXT(t *testing.T) {
	binary := os.Getenv("HGW_PEBBLE_BIN")
	if binary == "" {
		t.Skip("usar bash tools/check_acme_dns01.sh para el laboratorio ACME")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Second)
	defer cancel()
	dir := t.TempDir()
	const zone = "example.test."
	const challenge = "_acme-challenge.pc1.example.test."
	var mu sync.Mutex
	records := map[string][]string{challenge: {"manual-keep"}}
	added, deleted := 0, 0
	udp, err := net.ListenPacket("udp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	dnsAddress := udp.LocalAddr().String()
	tcp, err := net.Listen("tcp", dnsAddress)
	if err != nil {
		udp.Close()
		t.Fatal(err)
	}
	handler := dns.HandlerFunc(func(w dns.ResponseWriter, r *dns.Msg) {
		answer := new(dns.Msg)
		answer.SetReply(r)
		answer.Authoritative = true
		for _, q := range r.Question {
			name := strings.ToLower(q.Name)
			soa := &dns.SOA{Hdr: dns.RR_Header{Name: zone, Rrtype: dns.TypeSOA, Class: dns.ClassINET, Ttl: 1}, Ns: "ns.example.test.", Mbox: "admin.example.test.", Serial: 1, Refresh: 60, Retry: 60, Expire: 300, Minttl: 1}
			switch q.Qtype {
			case dns.TypeSOA:
				if name == zone {
					answer.Answer = append(answer.Answer, soa)
				} else {
					answer.Ns = append(answer.Ns, soa)
				}
			case dns.TypeTXT:
				mu.Lock()
				for _, v := range records[name] {
					answer.Answer = append(answer.Answer, &dns.TXT{Hdr: dns.RR_Header{Name: name, Rrtype: dns.TypeTXT, Class: dns.ClassINET, Ttl: 1}, Txt: []string{v}})
				}
				mu.Unlock()
			case dns.TypeA:
				answer.Answer = append(answer.Answer, &dns.A{Hdr: dns.RR_Header{Name: name, Rrtype: dns.TypeA, Class: dns.ClassINET, Ttl: 1}, A: net.ParseIP("100.64.0.55")})
			}
		}
		_ = w.WriteMsg(answer)
	})
	udpServer := &dns.Server{PacketConn: udp, Handler: handler}
	tcpServer := &dns.Server{Listener: tcp, Handler: handler}
	go func() { _ = udpServer.ActivateAndServe() }()
	go func() { _ = tcpServer.ActivateAndServe() }()
	defer udpServer.Shutdown()
	defer tcpServer.Shutdown()
	api := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		q := r.URL.Query()
		if q.Get("token") != "fixture-dns-token" {
			http.Error(w, "bad token", 403)
			return
		}
		mu.Lock()
		defer mu.Unlock()
		result := map[string]any{"status": "ok"}
		switch r.URL.Path {
		case "/api/zones/records/get":
			var list []map[string]any
			for name, values := range records {
				for _, v := range values {
					item := map[string]any{"name": strings.TrimSuffix(name, "."), "type": "TXT", "ttl": 1, "rData": map[string]string{"text": v}}
					item["lastModified"] = time.Now().UTC().Format(time.RFC3339Nano)
					if v == "manual-keep" {
						item["lastModified"] = time.Now().Add(-time.Hour).UTC().Format(time.RFC3339Nano)
					}
					list = append(list, item)
				}
			}
			result["response"] = map[string]any{"zone": map[string]string{"name": strings.TrimSuffix(zone, ".")}, "records": list}
		case "/api/zones/records/add", "/api/zones/records/delete":
			name := dns.Fqdn(q.Get("domain"))
			v := q.Get("text")
			if v == "manual-keep" {
				t.Error("se intentó borrar o sobrescribir un TXT manual antiguo")
			}
			if name != challenge || q.Get("type") != "TXT" || v == "" || v == "manual-keep" {
				http.Error(w, "outside challenge ownership", 400)
				return
			}
			if strings.HasSuffix(r.URL.Path, "/add") {
				records[name] = append(records[name], v)
				added++
			} else {
				found := false
				for i, current := range records[name] {
					if current == v {
						records[name] = append(records[name][:i], records[name][i+1:]...)
						deleted++
						found = true
						break
					}
				}
				if !found {
					t.Error("el proveedor intentó borrar un TXT inexistente")
				}
			}
		default:
			http.Error(w, "unknown API", 404)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(result)
	}))
	defer api.Close()
	// La CA HTTPS del laboratorio solo se confía en este cliente de prueba.
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	template := &x509.Certificate{SerialNumber: big.NewInt(1), Subject: pkix.Name{CommonName: "ACME lab HTTPS"}, NotBefore: time.Now().Add(-time.Minute), NotAfter: time.Now().Add(time.Hour), IsCA: true, BasicConstraintsValid: true, KeyUsage: x509.KeyUsageCertSign | x509.KeyUsageDigitalSignature, ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}, IPAddresses: []net.IP{net.ParseIP("127.0.0.1")}}
	der, err := x509.CreateCertificate(rand.Reader, template, template, &key.PublicKey, key)
	if err != nil {
		t.Fatal(err)
	}
	certPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der})
	keyDER, err := x509.MarshalPKCS8PrivateKey(key)
	if err != nil {
		t.Fatal(err)
	}
	certPath, keyPath := filepath.Join(dir, "https.crt"), filepath.Join(dir, "https.key")
	if err = os.WriteFile(certPath, certPEM, 0600); err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(keyPath, pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: keyDER}), 0600); err != nil {
		t.Fatal(err)
	}
	first, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	second, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		first.Close()
		t.Fatal(err)
	}
	acmeAddress, managementAddress := first.Addr().String(), second.Addr().String()
	first.Close()
	second.Close()
	settings := map[string]any{"pebble": map[string]any{"listenAddress": acmeAddress, "managementListenAddress": managementAddress, "certificate": certPath, "privateKey": keyPath, "httpPort": 5002, "tlsPort": 5001, "retryAfter": map[string]int{"authz": 1, "order": 1}, "profiles": map[string]any{"default": map[string]any{"description": "isolated test", "validityPeriod": 86400}}}}
	configPath := filepath.Join(dir, "pebble.json")
	raw, _ := json.Marshal(settings)
	if err = os.WriteFile(configPath, raw, 0600); err != nil {
		t.Fatal(err)
	}
	var logs bytes.Buffer
	command := exec.CommandContext(ctx, binary, "-config", configPath, "-dnsserver", dnsAddress)
	command.Env = append(os.Environ(), "PEBBLE_VA_NOSLEEP=1", "PEBBLE_AUTHZREUSE=0", "PEBBLE_WFE_NONCEREJECT=0")
	command.Stdout = &logs
	command.Stderr = &logs
	if err = command.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() {
		cancel()
		_ = command.Wait()
		if t.Failed() {
			text := logs.String()
			if len(text) > 6000 {
				text = text[len(text)-6000:]
			}
			t.Log(text)
		}
	}()
	roots := x509.NewCertPool()
	roots.AppendCertsFromPEM(certPEM)
	client := &http.Client{Transport: &http.Transport{TLSClientConfig: &tls.Config{RootCAs: roots}}, Timeout: time.Second}
	acmeURL := "https://" + acmeAddress + "/dir"
	ready := false
	for attempt := 0; attempt < 100; attempt++ {
		r, e := client.Get(acmeURL)
		if e == nil {
			io.Copy(io.Discard, r.Body)
			r.Body.Close()
			if r.StatusCode == 200 {
				ready = true
				break
			}
		}
		time.Sleep(50 * time.Millisecond)
	}
	if !ready {
		t.Fatal("Pebble no abrió el directorio ACME local")
	}
	r, err := client.Get("https://" + managementAddress + "/roots/0")
	if err != nil {
		t.Fatal(err)
	}
	issuerPEM, err := io.ReadAll(r.Body)
	r.Body.Close()
	if err != nil || r.StatusCode != 200 {
		t.Fatal("no se obtuvo la raíz emitida por Pebble", err)
	}
	issuerRoots := x509.NewCertPool()
	if !issuerRoots.AppendCertsFromPEM(issuerPEM) {
		t.Fatal("raíz ACME inválida")
	}
	previous := certmagic.DefaultACME
	defer func() { certmagic.DefaultACME = previous }()
	if err = configureACMEDNS(Config{ACMEDNSProvider: "technitium", ACMEAgreeToTerms: true, ProviderDNSURL: api.URL, ProviderDNSToken: "fixture-dns-token"}); err != nil {
		t.Fatal(err)
	}
	solver, ok := certmagic.DefaultACME.DNS01Solver.(*certmagic.DNS01Solver)
	if !ok {
		t.Fatal("no se configuró DNS-01")
	}
	if !certmagic.DefaultACME.DisableHTTPChallenge || !certmagic.DefaultACME.DisableTLSALPNChallenge {
		t.Fatal("se activó un desafío distinto de DNS-01")
	}
	solver.Resolvers = []string{dnsAddress}
	solver.PropagationTimeout = 10 * time.Second
	storage := &certmagic.FileStorage{Path: filepath.Join(dir, "storage")}
	var managed *certmagic.Config
	cache := certmagic.NewCache(certmagic.CacheOptions{GetConfigForCert: func(certmagic.Certificate) (*certmagic.Config, error) { return managed, nil }, Logger: zap.NewNop()})
	defer cache.Stop()
	managed = certmagic.New(cache, certmagic.Config{Storage: storage, Logger: zap.NewNop()})
	issuerTemplate := certmagic.ACMEIssuer{CA: acmeURL, TestCA: acmeURL, Email: "fixture@example.test", TrustedRoots: roots, DNS01Solver: solver, DisableHTTPChallenge: true, DisableTLSALPNChallenge: true, CertObtainTimeout: 30 * time.Second}
	issuer := certmagic.NewACMEIssuer(managed, issuerTemplate)
	managed.Issuers = []certmagic.Issuer{issuer}
	accountKeys := func() map[string][32]byte {
		paths, err := storage.List(ctx, "acme", true)
		if err != nil {
			t.Fatal(err)
		}
		keys := map[string][32]byte{}
		for _, path := range paths {
			if strings.HasSuffix(path, ".key") {
				value, err := storage.Load(ctx, path)
				if err != nil {
					t.Fatal(err)
				}
				keys[path] = sha256.Sum256(value)
			}
		}
		if len(keys) == 0 {
			t.Fatal("no se guardó la clave de cuenta ACME")
		}
		return keys
	}
	for _, name := range []string{"pc1.example.test", "*.pc1.example.test"} {
		if err = managed.ObtainCertSync(ctx, name); err != nil {
			t.Fatal("emisión DNS-01", name, err)
		}
		load := func() *x509.Certificate {
			certBytes, e := storage.Load(ctx, certmagic.StorageKeys.SiteCert(issuer.IssuerKey(), name))
			if e != nil {
				t.Fatal(e)
			}
			privateBytes, e := storage.Load(ctx, certmagic.StorageKeys.SitePrivateKey(issuer.IssuerKey(), name))
			if e != nil {
				t.Fatal(e)
			}
			pair, e := tls.X509KeyPair(certBytes, privateBytes)
			if e != nil {
				t.Fatal(e)
			}
			leaf, e := x509.ParseCertificate(pair.Certificate[0])
			if e != nil {
				t.Fatal(e)
			}
			intermediates := x509.NewCertPool()
			for _, part := range pair.Certificate[1:] {
				cert, e := x509.ParseCertificate(part)
				if e != nil {
					t.Fatal(e)
				}
				intermediates.AddCert(cert)
			}
			host := strings.Replace(name, "*.", "service.", 1)
			if _, e = leaf.Verify(x509.VerifyOptions{Roots: issuerRoots, Intermediates: intermediates, DNSName: host}); e != nil {
				t.Fatal("certificado o nombre inválido", e)
			}
			return leaf
		}
		before := load()
		accountsBefore := accountKeys()
		// Una instalación anterior sin la opción nueva conserva su cuenta: la
		// renovación no vuelve a aceptar términos ni a crear una identidad ACME.
		configureACMEAccountConsent(Config{ACMEAgreeToTerms: false})
		issuer = certmagic.NewACMEIssuer(managed, issuerTemplate)
		managed.Issuers = []certmagic.Issuer{issuer}
		if err = managed.RenewCertSync(ctx, name, true); err != nil {
			t.Fatal("renovación DNS-01", name, err)
		}
		accountsAfter := accountKeys()
		if len(accountsBefore) != len(accountsAfter) {
			t.Fatal("se recreó la cuenta ACME")
		}
		for name, hash := range accountsBefore {
			if accountsAfter[name] != hash {
				t.Fatal("se sustituyó la clave de cuenta ACME")
			}
		}
		if before.SerialNumber.Cmp(load().SerialNumber) == 0 {
			t.Fatal("la renovación no sustituyó el certificado")
		}
	}
	// Sin cuenta previa ni aceptación explícita, devuelve una decisión pendiente
	// y nunca intenta pedir una respuesta por stdin dentro del servicio.
	emptyStorage := &certmagic.FileStorage{Path: filepath.Join(dir, "no-consent")}
	noConsent := certmagic.New(cache, certmagic.Config{Storage: emptyStorage, Logger: zap.NewNop()})
	noConsent.Issuers = []certmagic.Issuer{certmagic.NewACMEIssuer(noConsent, issuerTemplate)}
	if err := noConsent.ObtainCertSync(ctx, "pc2.example.test"); err == nil || !strings.Contains(err.Error(), "acme.agree_to_terms") {
		t.Fatalf("alta sin aceptación no bloqueada: %v", err)
	}
	mu.Lock()
	defer mu.Unlock()
	if added < 4 || added != deleted || len(records[challenge]) != 1 || records[challenge][0] != "manual-keep" {
		t.Fatalf("limpieza incorrecta: creados=%d eliminados=%d restantes=%v", added, deleted, records[challenge])
	}
	// Las claves de cuenta y certificados quedan en el almacén temporal; nunca
	// se instala la CA de ensayo ni se escriben registros en el proveedor real.
	if _, err = os.Stat(storage.Path); err != nil {
		t.Fatal(err)
	}
	t.Log("ACME_DNS01_OK: emisión y renovación de nodo y wildcard, cadena TLS válida, TXT propios retirados y TXT manual conservado")
}
