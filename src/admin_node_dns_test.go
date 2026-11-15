package main

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gentedelcondado/headscale-gateway/internal/admin"
	"github.com/gentedelcondado/headscale-gateway/internal/network"
)

type retirementDNS struct {
	fakeDNS
	readErr, deleteErr error
}

func (f *retirementDNS) GetRecords(context.Context, string, string, bool) ([]DNSRecord, error) {
	return f.records, f.readErr
}
func (f *retirementDNS) DeleteARecord(context.Context, string, string, string) error {
	if f.deleteErr != nil {
		return f.deleteErr
	}
	f.deleted++
	return nil
}

func TestRetiredNodeDNSOwnership(t *testing.T) {
	domain := "tablet.intra.example.net"
	owned := managedDNSCommentForNode(domain)
	provider := &retirementDNS{fakeDNS: fakeDNS{records: []DNSRecord{
		{Name: domain, Type: "A", IP: "100.64.0.8", Comments: owned},
		{Name: "app." + domain, Type: "A", IP: "100.64.0.8", Comments: owned},
		{Name: "manual." + domain, Type: "A", IP: "100.64.0.8", Comments: "manual"},
		{Name: "app.other.intra.example.net", Type: "A", IP: "100.64.0.8", Comments: owned},
		{Name: "_acme-challenge." + domain, Type: "TXT", IP: "100.64.0.8", Comments: owned},
		{Name: "old." + domain, Type: "A", IP: "100.64.0.9", Comments: owned},
	}}}
	cfg := Config{BaseDomain: "intra.example.net", DNSZone: "example.net"}
	node := network.Node{Name: "device", GivenName: "tablet", IPAddresses: []string{"100.64.0.8"}}
	result := cleanupRetiredNodeDNS(context.Background(), provider, cfg, node)
	if provider.deleted != 2 || result.Deleted != 2 || result.Status != "warning" {
		t.Fatalf("unsafe cleanup: %+v, %d", result, provider.deleted)
	}
	provider.deleted = 0
	node.GivenName = "../other"
	if result = cleanupRetiredNodeDNS(context.Background(), provider, cfg, node); result.Status != "warning" || provider.deleted != 0 {
		t.Fatal(result)
	}
}

func TestRetiredNodeDNSFailuresRemainWarnings(t *testing.T) {
	cfg := Config{BaseDomain: "intra.example.net", DNSZone: "example.net"}
	node := network.Node{GivenName: "tablet", IPAddresses: []string{"100.64.0.8"}}
	record := DNSRecord{Name: "tablet.intra.example.net", Type: "A", IP: "100.64.0.8", Comments: managedDNSCommentForNode("tablet.intra.example.net")}
	for _, provider := range []*retirementDNS{
		{readErr: errors.New("token=must-not-leak")},
		{fakeDNS: fakeDNS{records: []DNSRecord{record}}, deleteErr: errors.New("token=must-not-leak")},
	} {
		result := cleanupRetiredNodeDNS(context.Background(), provider, cfg, node)
		if result.Status != "warning" || result.Deleted != 0 {
			t.Fatal(result)
		}
		if result.Message == "" || strings.Contains(result.Message, "token") {
			t.Fatal("missing or unsafe warning")
		}
	}
	if result := cleanupRetiredNodeDNS(context.Background(), nil, cfg, node); result.Status != "warning" {
		t.Fatal(result)
	}
}

func TestRetiredNodeDNSManualCollisionIsNotDeleted(t *testing.T) {
	domain := "tablet.intra.example.net"
	provider := &retirementDNS{fakeDNS: fakeDNS{records: []DNSRecord{
		{Name: domain, Type: "A", IP: "100.64.0.8", Comments: managedDNSCommentForNode(domain)},
		{Name: domain, Type: "A", IP: "100.64.0.8", Comments: "manual"},
	}}}
	result := cleanupRetiredNodeDNS(context.Background(), provider, Config{BaseDomain: "intra.example.net", DNSZone: "example.net"}, network.Node{GivenName: "tablet", IPAddresses: []string{"100.64.0.8"}})
	if result.Status != "warning" || provider.deleted != 0 {
		t.Fatal("ambiguous ownership", result)
	}
}

func TestHeadscaleRetirementOnlyCleansAfterSuccessfulMutation(t *testing.T) {
	for _, action := range []string{"node.delete", "node.expire"} {
		for _, status := range []int{200, 403} {
			t.Run(action+http.StatusText(status), func(t *testing.T) {
				var events []string
				server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
					if r.URL.Path == "/api/v1/node" && r.Method == "GET" {
						events = append(events, "read")
						w.Write([]byte(`{"nodes":[{"id":"7","name":"original","givenName":"tablet","ipAddresses":["100.64.0.8"]}]}`))
						return
					}
					events = append(events, "mutate")
					w.WriteHeader(status)
					w.Write([]byte(`{"node":{"id":"7"}}`))
				}))
				defer server.Close()
				provider := &retirementDNS{fakeDNS: fakeDNS{records: []DNSRecord{{Name: "tablet.intra.example.net", Type: "A", IP: "100.64.0.8", Comments: managedDNSCommentForNode("tablet.intra.example.net")}}}}
				runtime := &gatewayRuntime{}
				runtime.cfg.Store(&Config{BaseDomain: "intra.example.net", DNSZone: "example.net"})
				controller := adminController{runtime: runtime, provider: provider}
				value, err := controller.retireHeadscaleNode(context.Background(), network.HeadscaleAdmin{BaseURL: server.URL, APIKey: "test"}, admin.HeadscaleAction{ID: "7", Action: action})
				if len(events) != 2 || events[0] != "read" || events[1] != "mutate" {
					t.Fatal(events)
				}
				if status == 200 {
					if err != nil || provider.deleted != 1 || value == nil {
						t.Fatal(value, err, provider.deleted)
					}
					response := value.(map[string]json.RawMessage)
					if len(response["node"]) == 0 || len(response["dns_cleanup"]) == 0 {
						t.Fatal("response compatibility lost", response)
					}
				} else if err == nil || provider.deleted != 0 {
					t.Fatal("DNS changed after rejected mutation", err)
				}
			})
		}
	}
}
