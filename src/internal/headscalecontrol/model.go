// Package headscalecontrol administra una instancia Headscale mediante un
// contrato común. El panel nunca recibe el archivo completo ni sus secretos.
package headscalecontrol

import (
	"errors"
	"net/mail"
	"net/netip"
	"net/url"
	"strings"
)

type Info struct {
	Mode                  string `json:"mode"`
	LocalAvailable        bool   `json:"local_available"`
	LocalController       bool   `json:"local_controller"`
	RemoteTokenConfigured bool   `json:"remote_token_configured"`
	CanWrite              bool   `json:"can_write"`
	CanSyncAgent          bool   `json:"can_sync_agent"`
}

// DNS describe los ajustes del coordinador, no los registros DNS-01 del Gateway.
type DNS struct {
	MagicDNS         bool   `json:"magic_dns" yaml:"magic_dns"`
	BaseDomain       string `json:"base_domain" yaml:"base_domain"`
	OverrideLocalDNS bool   `json:"override_local_dns" yaml:"override_local_dns"`
	Nameservers      struct {
		Global []string            `json:"global" yaml:"global"`
		Split  map[string][]string `json:"split" yaml:"split"`
	} `json:"nameservers" yaml:"nameservers"`
	SearchDomains []string `json:"search_domains" yaml:"search_domains"`
}

// Restrictions no contiene issuer, client_id, client_secret ni credenciales IdP.
type Restrictions struct {
	AllowedDomains []string `json:"allowed_domains" yaml:"allowed_domains"`
	AllowedGroups  []string `json:"allowed_groups" yaml:"allowed_groups"`
	AllowedUsers   []string `json:"allowed_users" yaml:"allowed_users"`
}

type Record struct {
	Name  string `json:"name" yaml:"name"`
	Type  string `json:"type" yaml:"type"`
	Value string `json:"value" yaml:"value"`
}

type Document struct {
	CoordinatorOrigin string        `json:"coordinator_origin"`
	Revision          string        `json:"revision"`
	DNS               DNS           `json:"dns"`
	OIDC              *Restrictions `json:"oidc,omitempty"`
	Records           []Record      `json:"records"`
	RecordsWritable   bool          `json:"records_writable"`
	Instance          string        `json:"instance"`
}

// Change solo admite campos tipados. Rutas, órdenes, unidades y secretos quedan
// fijados por el instalador local y nunca se toman de una solicitud remota.
type Change struct {
	Revision string        `json:"revision"`
	DNS      *DNS          `json:"dns,omitempty"`
	OIDC     *Restrictions `json:"oidc,omitempty"`
	Records  *[]Record     `json:"records,omitempty"`
}

func Domain(value string) bool {
	if len(value) > 253 || value != strings.ToLower(value) || !strings.Contains(value, ".") {
		return false
	}
	for _, label := range strings.Split(value, ".") {
		if len(label) == 0 || len(label) > 63 || label[0] == '-' || label[len(label)-1] == '-' {
			return false
		}
		for _, r := range label {
			if !(r >= 'a' && r <= 'z' || r >= '0' && r <= '9' || r == '-') {
				return false
			}
		}
	}
	return true
}

func resolver(value string) bool {
	if ip, e := netip.ParseAddr(value); e == nil {
		return ip.Zone() == "" && !ip.IsUnspecified() && !ip.IsMulticast()
	}
	u, e := url.Parse(value)
	return e == nil && u.Scheme == "https" && u.Hostname() != "" && u.User == nil && u.Fragment == "" && len(value) <= 2048
}

func (d DNS) Validate() error {
	if d.BaseDomain != "" && !Domain(d.BaseDomain) || d.MagicDNS && d.BaseDomain == "" {
		return errors.New("dominio base de MagicDNS inválido")
	}
	if d.OverrideLocalDNS && len(d.Nameservers.Global) == 0 {
		return errors.New("el DNS global necesita al menos un resolutor para sustituir al DNS local")
	}
	if len(d.Nameservers.Global) > 32 || len(d.Nameservers.Split) > 64 || len(d.SearchDomains) > 32 {
		return errors.New("demasiados ajustes DNS")
	}
	check := func(values []string) bool {
		seen := map[string]bool{}
		for _, v := range values {
			if !resolver(v) || seen[v] {
				return false
			}
			seen[v] = true
		}
		return len(values) <= 32
	}
	if !check(d.Nameservers.Global) {
		return errors.New("resolutores globales inválidos o repetidos")
	}
	for domain, values := range d.Nameservers.Split {
		if !Domain(domain) || len(values) == 0 || !check(values) {
			return errors.New("regla Split DNS inválida")
		}
	}
	seen := map[string]bool{}
	for _, domain := range d.SearchDomains {
		if !Domain(domain) || seen[domain] {
			return errors.New("dominio de búsqueda inválido o repetido")
		}
		seen[domain] = true
	}
	return nil
}

func (r Restrictions) Validate() error {
	if len(r.AllowedDomains) > 128 || len(r.AllowedGroups) > 128 || len(r.AllowedUsers) > 256 {
		return errors.New("demasiadas restricciones OIDC")
	}
	for _, d := range r.AllowedDomains {
		if !Domain(d) {
			return errors.New("dominio OIDC inválido")
		}
	}
	for _, u := range r.AllowedUsers {
		a, e := mail.ParseAddress(u)
		if e != nil || a.Address != u || a.Name != "" {
			return errors.New("usuario OIDC: se requiere una dirección de correo completa")
		}
	}
	for _, list := range [][]string{r.AllowedDomains, r.AllowedGroups, r.AllowedUsers} {
		seen := map[string]bool{}
		for _, v := range list {
			if v == "" || strings.TrimSpace(v) != v || len(v) > 320 || strings.ContainsAny(v, "\r\n\x00") || seen[v] {
				return errors.New("restricción OIDC vacía, repetida o inválida")
			}
			seen[v] = true
		}
	}
	return nil
}

func ValidateRecords(records []Record) error {
	if len(records) > 1000 {
		return errors.New("demasiados registros MagicDNS")
	}
	seen := map[string]bool{}
	for _, r := range records {
		ip, e := netip.ParseAddr(r.Value)
		if !Domain(r.Name) || e != nil || ip.Zone() != "" || ip.IsUnspecified() || ip.IsMulticast() || r.Type != "A" && r.Type != "AAAA" || r.Type == "A" && !ip.Is4() || r.Type == "AAAA" && !ip.Is6() {
			return errors.New("registro MagicDNS inválido: solo nombres completos y direcciones A/AAAA")
		}
		key := r.Name + "/" + r.Type + "/" + r.Value
		if seen[key] {
			return errors.New("registro MagicDNS repetido")
		}
		seen[key] = true
	}
	return nil
}
