package headscalecontrol

import (
	"bytes"
	"strings"
	"testing"
)

const exampleConfig = `# Coordinador de laboratorio
server_url: https://control.example.test
dns:
  magic_dns: true
  base_domain: intra.example.test
  override_local_dns: false
  nameservers:
    global: [1.1.1.1]
    split:
      intra.example.test: [100.64.0.2]
  search_domains: [intra.example.test]
  extra_records_path: /var/lib/headscale/records.json
oidc:
  issuer: https://identity.example.test
  client_id: coordinator
  client_secret: SECRET-OIDC-DO-NOT-EXPOSE
  scope: [openid, profile, email, groups]
  allowed_groups: [vpn-users]
database:
  type: sqlite
  sqlite:
    path: /var/lib/headscale/db.sqlite
noise:
  private_key_path: /var/lib/headscale/noise.key
`

func TestDocumentPreservesCoordinatorSecretsAndUnrelatedFields(t *testing.T) {
	config := []byte(exampleConfig)
	records := []byte("[]\n")
	p, e := parse(config, records, true)
	if e != nil {
		t.Fatal(e)
	}
	dns := p.document.DNS
	dns.Nameservers.Global = []string{"9.9.9.9"}
	dns.OverrideLocalDNS = true
	before := p.document.OIDC
	restrictions := *before
	restrictions.AllowedUsers = []string{"alice@example.test"}
	next, unchanged, restart, e := prepare(config, records, true, Change{Revision: p.document.Revision, DNS: &dns, OIDC: &restrictions})
	if e != nil {
		t.Fatal(e)
	}
	if !restart || !bytes.Equal(unchanged, records) {
		t.Fatal("se perdió la decisión de reinicio o se modificaron registros ajenos")
	}
	for _, value := range []string{"SECRET-OIDC-DO-NOT-EXPOSE", "/var/lib/headscale/db.sqlite", "/var/lib/headscale/noise.key", "/var/lib/headscale/records.json", "# Coordinador de laboratorio", "scope: [openid, profile, email, groups]"} {
		if !bytes.Contains(next, []byte(value)) {
			t.Errorf("se perdió un valor o comentario ajeno: %s", value)
		}
	}
	result, e := parse(next, records, true)
	if e != nil {
		t.Fatal(e)
	}
	if result.document.DNS.Nameservers.Global[0] != "9.9.9.9" || result.document.OIDC.AllowedUsers[0] != "alice@example.test" {
		t.Fatal("el cambio no se aplicó")
	}
	if result.document.Revision == p.document.Revision {
		t.Fatal("la revisión debe cambiar")
	}
}

func TestRecordsAreIndependentAndRevisioned(t *testing.T) {
	config := []byte(exampleConfig)
	records := []byte("[]\n")
	p, _ := parse(config, records, true)
	values := []Record{{Name: "fotos.pc1.intra.example.test", Type: "A", Value: "100.64.0.3"}}
	next, result, restart, e := prepare(config, records, true, Change{Revision: p.document.Revision, Records: &values})
	if e != nil || restart || !bytes.Equal(next, config) {
		t.Fatalf("los registros dinámicos no requieren reiniciar: %v", e)
	}
	if _, _, _, e = prepare(config, result, true, Change{Revision: p.document.Revision, Records: &values}); e == nil {
		t.Fatal("se aceptó una revisión obsoleta")
	}
	if _, _, _, e = prepare(config, records, false, Change{Revision: p.document.Revision, Records: &values}); e == nil {
		t.Fatal("se editaron registros de solo lectura")
	}
}

func TestRejectAmbiguousYAMLWithoutLeakingSecrets(t *testing.T) {
	for _, config := range []string{
		"dns: {magic_dns: true}\ndns: {client_secret: SECRET-OIDC-DO-NOT-EXPOSE}",
		"dns: &copy {magic_dns: true}\nother: *copy",
		exampleConfig + "\n---\nclient_secret: SECRET-OIDC-DO-NOT-EXPOSE",
		"dns: [ SECRET-OIDC-DO-NOT-EXPOSE",
	} {
		_, e := parse([]byte(config), nil, false)
		if e == nil || strings.Contains(e.Error(), "SECRET-OIDC") {
			t.Fatalf("error ausente o con secretos: %v", e)
		}
	}
}

func TestValidateHeadscaleInputs(t *testing.T) {
	p, _ := parse([]byte(exampleConfig), nil, false)
	for _, bad := range []string{"https://user:secret@resolver.example.test/dns-query", "http://resolver.example.test/dns-query", "javascript:alert(1)", "0.0.0.0", "224.0.0.1"} {
		d := p.document.DNS
		d.Nameservers.Global = []string{bad}
		if d.Validate() == nil {
			t.Errorf("resolutor inseguro aceptado: %s", bad)
		}
	}
	d := p.document.DNS
	d.OverrideLocalDNS = true
	d.Nameservers.Global = nil
	if d.Validate() == nil {
		t.Fatal("override sin resolutor")
	}
	r := Restrictions{AllowedGroups: []string{"admins\nclient_secret: secret"}}
	if r.Validate() == nil {
		t.Fatal("grupo con salto de línea")
	}
	d = p.document.DNS
	d.BaseDomain = "control.example.test"
	if _, _, _, e := prepare([]byte(exampleConfig), nil, false, Change{Revision: p.document.Revision, DNS: &d}); e == nil {
		t.Fatal("dominio de control utilizado como dominio MagicDNS")
	}
	if ValidateRecords([]Record{{"*.intra.example.test", "A", "100.64.0.3"}}) == nil {
		t.Fatal("se prometió un comodín MagicDNS no soportado")
	}
}

func TestNoOpDoesNotRewriteOrRestartHeadscale(t *testing.T) {
	p, err := parse([]byte(exampleConfig), []byte("[]\n"), true)
	if err != nil {
		t.Fatal(err)
	}
	for _, change := range []Change{
		{Revision: p.document.Revision, DNS: &p.document.DNS},
		{Revision: p.document.Revision, OIDC: p.document.OIDC},
		{Revision: p.document.Revision, Records: &p.document.Records},
	} {
		if _, _, restart, err := prepare([]byte(exampleConfig), []byte("[]\n"), true, change); err == nil || restart {
			t.Fatal("un cambio vacío no debe reescribir ni reiniciar Headscale")
		}
	}
}

func TestDNSDefaultsMatchHeadscaleBeforeEditing(t *testing.T) {
	config := []byte("server_url: https://control.example.test\ndns:\n  base_domain: intra.example.test\n  nameservers:\n    global: [1.1.1.1]\n")
	p, e := parse(config, nil, false)
	if e != nil {
		t.Fatal(e)
	}
	if !p.document.DNS.MagicDNS || !p.document.DNS.OverrideLocalDNS {
		t.Fatal("se perdieron los valores predeterminados efectivos de Headscale")
	}
	dns := p.document.DNS
	dns.SearchDomains = []string{"intra.example.test"}
	next, _, _, e := prepare(config, nil, false, Change{Revision: p.document.Revision, DNS: &dns})
	if e != nil {
		t.Fatal(e)
	}
	changed, e := parse(next, nil, false)
	if e != nil || !changed.document.DNS.OverrideLocalDNS || !changed.document.DNS.MagicDNS {
		t.Fatal("editar dominios de búsqueda cambió el DNS efectivo", e)
	}
}
