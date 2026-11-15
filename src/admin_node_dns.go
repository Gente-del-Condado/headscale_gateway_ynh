package main

import (
	"context"
	"encoding/json"
	"net/netip"
	"strings"
	"time"

	"github.com/gentedelcondado/headscale-gateway/internal/admin"
	"github.com/gentedelcondado/headscale-gateway/internal/diagnostics"
	"github.com/gentedelcondado/headscale-gateway/internal/network"
)

type nodeDNSCleanup struct {
	Status  string `json:"status"`
	Deleted int    `json:"deleted"`
	Message string `json:"message"`
}

// retireHeadscaleNode toma la identidad del servidor antes de borrarla. Nunca
// usa nombres/IP aportados por el navegador. El fallo DNS no se presenta como
// fallo de una eliminación que Headscale ya confirmó: devuelve un aviso separado.
func (a *adminController) retireHeadscaleNode(ctx context.Context, h network.HeadscaleAdmin, cmd admin.HeadscaleAction) (any, error) {
	a.runtime.transitionMu.Lock()
	defer a.runtime.transitionMu.Unlock()
	cfg := a.runtime.currentConfig()
	inventory, inventoryErr := network.List(ctx, h.BaseURL, h.APIKey)
	var node *network.Node
	for i := range inventory.Nodes {
		if inventory.Nodes[i].ID == cmd.ID {
			node = &inventory.Nodes[i]
			break
		}
	}
	var raw json.RawMessage
	var err error
	if cmd.Action == "node.expire" {
		raw, err = h.ExpireNode(ctx, cmd.ID)
	} else {
		raw, err = h.DeleteNode(ctx, cmd.ID)
	}
	if err != nil {
		return nil, err
	}
	result := nodeDNSCleanup{Status: "warning", Message: "DNS pendiente: no se pudo obtener la identidad del nodo antes de retirarlo. Revisa los registros manualmente."}
	if inventoryErr == nil && node != nil {
		// Se usa un contexto independiente, acotado y posterior al éxito en
		// Headscale: cerrar el navegador no cancela a mitad la limpieza DNS.
		dnsCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), 15*time.Second)
		defer cancel()
		// Cerrar el navegador no cancela; detener el motor sí interrumpe la petición.
		stopOnShutdown := context.AfterFunc(processContext, cancel)
		defer stopOnShutdown()
		result = cleanupRetiredNodeDNS(dnsCtx, a.provider, cfg, *node)
	}
	level := diagnostics.InfoLevel
	if result.Status == "warning" {
		level = diagnostics.Warn
	}
	diagnostics.Emit("admin", level, "HGW-HS-DNS-CLEANUP", "%s; registros A eliminados=%d", result.Message, result.Deleted)
	// Conserva los campos originales de Headscale para los clientes existentes.
	// La información DNS es adicional, no sustituye la respuesta de la operación.
	fields := make(map[string]json.RawMessage)
	if err := json.Unmarshal(raw, &fields); err != nil || fields == nil {
		fields = map[string]json.RawMessage{"result": raw}
	}
	fields["dns_cleanup"], _ = json.Marshal(result)
	return fields, nil
}

// cleanupRetiredNodeDNS exige nombre definitivo, zona, marca exacta y una IP
// del inventario Headscale. Los registros manuales, de otro nodo o de otra IP
// no se borran. No toca TXT de ACME, CNAME, certificados ni claves.
func cleanupRetiredNodeDNS(ctx context.Context, provider DNSProvider, cfg Config, node network.Node) nodeDNSCleanup {
	result := nodeDNSCleanup{Status: "warning", Message: "DNS pendiente: configura un proveedor con permisos de lectura y borrado para la zona del nodo."}
	if provider == nil {
		return result
	}
	name := node.GivenName
	if name == "" {
		name = node.Name
	}
	base := strings.TrimSuffix(strings.ToLower(strings.TrimSpace(cfg.BaseDomain)), ".")
	zone := strings.TrimSuffix(strings.ToLower(strings.TrimSpace(cfg.DNSZone)), ".")
	if !validRequestedNodeName(name) || base == "" || zone == "" {
		result.Message = "DNS pendiente: no se puede determinar con seguridad el dominio del nodo."
		return result
	}
	domain := name + "." + base
	if !isGatewayDomain(domain, zone) {
		result.Message = "DNS pendiente: el nodo queda fuera de la zona DNS configurada."
		return result
	}
	ips := map[netip.Addr]bool{}
	for _, value := range node.IPAddresses {
		if ip, err := netip.ParseAddr(value); err == nil && ip.Is4() {
			ips[ip] = true
		}
	}
	if len(ips) == 0 {
		result.Message = "DNS pendiente: el nodo no tiene una IPv4 verificable en Headscale."
		return result
	}
	records, err := provider.GetRecords(ctx, domain, cfg.DNSZone, true)
	if err != nil {
		result.Message = "DNS pendiente: no se pudieron consultar los registros. Revisa la conexión y los permisos de lectura del proveedor."
		return result
	}
	review := false
	seen := map[string]bool{}
	for _, record := range records {
		host := strings.TrimSuffix(strings.ToLower(strings.TrimSpace(record.Name)), ".")
		if record.Type != "A" || strings.TrimSpace(record.Comments) != managedDNSCommentForNode(domain) || !isGatewayDomain(host, domain) {
			continue
		}
		ip, err := netip.ParseAddr(strings.TrimSpace(record.IP))
		if err != nil || !ips[ip] {
			review = true
			result.Message = "DNS pendiente: hay registros marcados del nodo cuya IP no coincide con Headscale; se conservan para revisión."
			continue
		}

		// Un RR duplicado/manual con la misma clave no permite atribuir el
		// borrado a una única propiedad en todos los proveedores.
		collision := false
		for _, other := range records {
			otherHost := strings.TrimSuffix(strings.ToLower(strings.TrimSpace(other.Name)), ".")
			otherIP, _ := netip.ParseAddr(strings.TrimSpace(other.IP))
			if other.Type == "A" && otherHost == host && otherIP == ip && strings.TrimSpace(other.Comments) != managedDNSCommentForNode(domain) {
				collision = true
				break
			}
		}
		if collision {
			review = true
			result.Message = "DNS pendiente: un registro gestionado coincide con un registro manual; se conserva para revisión."
			continue
		}
		key := host + "/" + ip.String()
		if seen[key] {
			continue
		}
		seen[key] = true
		if err := provider.DeleteARecord(ctx, cfg.DNSZone, host, ip.String()); err != nil {
			result.Message = "DNS pendiente: no se pudo completar el borrado. Revisa la conexión y los permisos de eliminación del proveedor. La operación en Headscale ya se completó."
			return result
		}
		result.Deleted++
	}
	if review {
		return result
	}
	result.Status = "complete"
	result.Message = "Limpieza DNS completada: solo se retiran registros A marcados del nodo y con su IP. Los registros manuales y de otros nodos se conservan."
	if result.Deleted == 0 {
		result.Status = "none"
		result.Message = "No se encontraron registros A gestionados para la identidad actual del nodo. Los registros manuales o con nombres anteriores requieren revisión."
	}
	return result
}
