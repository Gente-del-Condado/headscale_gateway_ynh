// Package technitium implements a DNS record management client compatible
// with the libdns interfaces for Technitium DNS Server.
// It uses the Technitium HTTP API (not TSIG) for DNS challenge management.
package technitium

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/libdns/libdns"
)

// Provider facilitates DNS record manipulation with Technitium DNS Server.
type Provider struct {
	// ServerURL is the base URL of the Technitium DNS server,
	// e.g. "http://dns.example.com:5380"
	ServerURL string `json:"server_url"`

	// APIToken is the Technitium API token (created in the web UI under Settings > API).
	// This is used instead of TSIG — all requests are authenticated via this token.
	APIToken string `json:"api_token"`

	// StaleRecordTimeout is how old an _acme-challenge TXT record must be
	// before it is considered stale and automatically cleaned up.
	// Set to 0 to disable stale record cleanup. Default: 15 minutes.
	StaleRecordTimeout time.Duration `json:"stale_record_timeout,omitempty"`

	client *technitiumClient
	mu     sync.Mutex
}

const defaultStaleRecordTimeout = 15 * time.Minute

func (p *Provider) getClient() *technitiumClient {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.client == nil {
		p.client = &technitiumClient{
			serverURL: p.ServerURL,
			apiToken:  p.APIToken,
		}
	}
	return p.client
}

// GetRecords lists all the records in the zone.
func (p *Provider) GetRecords(ctx context.Context, zone string) ([]libdns.Record, error) {
	client := p.getClient()
	return client.getRecords(ctx, zone)
}

// AppendRecords adds records to the zone. It returns the records that were added.
// Before adding _acme-challenge TXT records, it cleans up any stale challenge
// records that are older than StaleRecordTimeout.
func (p *Provider) AppendRecords(ctx context.Context, zone string, records []libdns.Record) ([]libdns.Record, error) {
	client := p.getClient()

	timeout := p.StaleRecordTimeout
	if timeout == 0 {
		timeout = defaultStaleRecordTimeout
	}
	if timeout > 0 {
		for _, rec := range records {
			rr := rec.RR()
			if rr.Type == "TXT" && strings.HasPrefix(rr.Name, "_acme-challenge") {
				fqdn := libdns.AbsoluteName(rr.Name, strings.TrimSuffix(zone, "."))
				fqdn = strings.TrimSuffix(fqdn, ".")
				client.cleanupStaleRecords(ctx, zone, fqdn, timeout)
			}
		}
	}

	var added []libdns.Record
	for _, rec := range records {
		r, err := client.addRecord(ctx, zone, rec)
		if err != nil {
			return added, fmt.Errorf("adding record %v: %w", rec, err)
		}
		added = append(added, r)
	}
	return added, nil
}

// SetRecords sets the records in the zone, either by updating existing records
// or creating new ones. It returns the updated records.
func (p *Provider) SetRecords(ctx context.Context, zone string, records []libdns.Record) ([]libdns.Record, error) {
	client := p.getClient()
	var set []libdns.Record
	for _, rec := range records {
		r, err := client.updateOrCreateRecord(ctx, zone, rec)
		if err != nil {
			return set, fmt.Errorf("setting record %v: %w", rec, err)
		}
		set = append(set, r)
	}
	return set, nil
}

// DeleteRecords deletes the records from the zone. It returns the records that were deleted.
func (p *Provider) DeleteRecords(ctx context.Context, zone string, records []libdns.Record) ([]libdns.Record, error) {
	client := p.getClient()
	var deleted []libdns.Record
	for _, rec := range records {
		err := client.deleteRecord(ctx, zone, rec)
		if err != nil {
			return deleted, fmt.Errorf("deleting record %v: %w", rec, err)
		}
		deleted = append(deleted, rec)
	}
	return deleted, nil
}

// Interface guards
var (
	_ libdns.RecordGetter   = (*Provider)(nil)
	_ libdns.RecordAppender = (*Provider)(nil)
	_ libdns.RecordSetter   = (*Provider)(nil)
	_ libdns.RecordDeleter  = (*Provider)(nil)
)
