package technitium

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/netip"
	"net/url"
	"strings"
	"time"

	"github.com/libdns/libdns"
)

type technitiumClient struct {
	serverURL  string
	apiToken   string
	httpClient *http.Client
}

func (c *technitiumClient) http() *http.Client {
	if c.httpClient == nil {
		c.httpClient = &http.Client{Timeout: 30 * time.Second}
	}
	return c.httpClient
}

// ---- Technitium API response types ----

type apiResponse struct {
	Status       string          `json:"status"`
	ErrorMessage string          `json:"errorMessage,omitempty"`
	Response     json.RawMessage `json:"response,omitempty"`
}

type listRecordsResponse struct {
	Zone    zoneInfo    `json:"zone"`
	Records []dnsRecord `json:"records"`
}

type zoneInfo struct {
	Name string `json:"name"`
}

type dnsRecord struct {
	Name         string          `json:"name"`
	Type         string          `json:"type"`
	TTL          int             `json:"ttl"`
	RData        json.RawMessage `json:"rData"`
	LastModified string          `json:"lastModified"`
}

type txtRData struct {
	Text string `json:"text"`
}

type aRData struct {
	IPAddress string `json:"ipAddress"`
}

type aaaaRData struct {
	IPAddress string `json:"ipAddress"`
}

type cnameRData struct {
	CName string `json:"cname"`
}

type mxRData struct {
	Exchange   string `json:"exchange"`
	Preference int    `json:"preference"`
}

type nsRData struct {
	NameServer string `json:"nameServer"`
}

// ---- API helpers ----

func (c *technitiumClient) apiGet(ctx context.Context, path string, params url.Values) (*apiResponse, error) {
	if params == nil {
		params = url.Values{}
	}
	params.Set("token", c.apiToken)

	reqURL := strings.TrimRight(c.serverURL, "/") + path + "?" + params.Encode()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, reqURL, nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.http().Do(req)
	if err != nil {
		return nil, fmt.Errorf("technitium api request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("reading response body: %w", err)
	}

	var apiResp apiResponse
	if err := json.Unmarshal(body, &apiResp); err != nil {
		return nil, fmt.Errorf("decoding response: %w (body: %s)", err, body)
	}
	if apiResp.Status != "ok" {
		return nil, fmt.Errorf("technitium api error: %s", apiResp.ErrorMessage)
	}
	return &apiResp, nil
}

// ---- Record operations ----

func (c *technitiumClient) getRecords(ctx context.Context, zone string) ([]libdns.Record, error) {
	params := url.Values{
		"domain":   {strings.TrimSuffix(zone, ".")},
		"listZone": {"true"},
	}

	apiResp, err := c.apiGet(ctx, "/api/zones/records/get", params)
	if err != nil {
		return nil, err
	}

	var listResp listRecordsResponse
	if err := json.Unmarshal(apiResp.Response, &listResp); err != nil {
		return nil, fmt.Errorf("parsing records response: %w", err)
	}

	var records []libdns.Record
	for _, r := range listResp.Records {
		rec, err := toLibDNS(r, zone)
		if err != nil {
			continue
		}
		records = append(records, rec)
	}
	return records, nil
}

func (c *technitiumClient) addRecord(ctx context.Context, zone string, rec libdns.Record) (libdns.Record, error) {
	params := buildAddParams(zone, rec)
	_, err := c.apiGet(ctx, "/api/zones/records/add", params)
	if err != nil {
		return nil, fmt.Errorf("technitium add record: %w", err)
	}
	return rec, nil
}

func (c *technitiumClient) updateOrCreateRecord(ctx context.Context, zone string, rec libdns.Record) (libdns.Record, error) {
	params := buildAddParams(zone, rec)
	params.Set("overwrite", "true")
	_, err := c.apiGet(ctx, "/api/zones/records/add", params)
	if err != nil {
		return nil, fmt.Errorf("technitium set record: %w", err)
	}
	return rec, nil
}

// cleanupStaleRecords queries for existing TXT records at the given domain
// and deletes any that are older than maxAge. This prevents stale _acme-challenge
// records from accumulating after failed or interrupted ACME challenges.
func (c *technitiumClient) cleanupStaleRecords(ctx context.Context, zone string, domain string, maxAge time.Duration) {
	params := url.Values{
		"domain": {domain},
	}

	apiResp, err := c.apiGet(ctx, "/api/zones/records/get", params)
	if err != nil {
		return // best-effort: if we can't query, skip cleanup
	}

	var listResp listRecordsResponse
	if err := json.Unmarshal(apiResp.Response, &listResp); err != nil {
		return
	}

	now := time.Now()
	for _, r := range listResp.Records {
		if r.Type != "TXT" || r.LastModified == "" {
			continue
		}
		modified, err := time.Parse(time.RFC3339, r.LastModified)
		if err != nil {
			// Technitium uses a format like "2026-04-05T17:04:57.2744853Z"
			// which time.RFC3339Nano handles
			modified, err = time.Parse(time.RFC3339Nano, r.LastModified)
			if err != nil {
				continue
			}
		}
		if now.Sub(modified) > maxAge {
			var rdata txtRData
			if err := json.Unmarshal(r.RData, &rdata); err != nil {
				continue
			}
			_ = c.deleteRecord(ctx, zone, libdns.TXT{
				Name: libdns.RelativeName(strings.TrimSuffix(r.Name, "."), strings.TrimSuffix(zone, ".")),
				Text: rdata.Text,
			})
		}
	}
}

func (c *technitiumClient) deleteRecord(ctx context.Context, zone string, rec libdns.Record) error {
	params := buildDeleteParams(zone, rec)
	_, err := c.apiGet(ctx, "/api/zones/records/delete", params)
	if err != nil {
		return fmt.Errorf("technitium delete record: %w", err)
	}
	return nil
}

// ---- Param builders ----

func buildAddParams(zone string, rec libdns.Record) url.Values {
	rr := rec.RR()
	zone = strings.TrimSuffix(zone, ".")
	name := libdns.AbsoluteName(rr.Name, zone)
	name = strings.TrimSuffix(name, ".")

	params := url.Values{
		"domain": {name},
		"type":   {rr.Type},
		"ttl":    {fmt.Sprintf("%d", int(rr.TTL.Seconds()))},
	}

	switch r := rec.(type) {
	case libdns.TXT:
		params.Set("text", r.Text)
	case libdns.Address:
		params.Set("ipAddress", r.IP.String())
	case libdns.CNAME:
		params.Set("cname", strings.TrimSuffix(r.Target, "."))
	case libdns.MX:
		params.Set("preference", fmt.Sprintf("%d", r.Preference))
		params.Set("exchange", strings.TrimSuffix(r.Target, "."))
	case libdns.NS:
		params.Set("nameServer", strings.TrimSuffix(r.Target, "."))
	default:
		// Fall back to RR.Data for unknown types
		switch rr.Type {
		case "TXT":
			params.Set("text", rr.Data)
		case "A", "AAAA":
			params.Set("ipAddress", rr.Data)
		case "CNAME":
			params.Set("cname", strings.TrimSuffix(rr.Data, "."))
		case "MX":
			parts := strings.SplitN(rr.Data, " ", 2)
			if len(parts) == 2 {
				params.Set("preference", parts[0])
				params.Set("exchange", strings.TrimSuffix(parts[1], "."))
			}
		case "NS":
			params.Set("nameServer", strings.TrimSuffix(rr.Data, "."))
		}
	}
	return params
}

func buildDeleteParams(zone string, rec libdns.Record) url.Values {
	rr := rec.RR()
	zone = strings.TrimSuffix(zone, ".")
	name := libdns.AbsoluteName(rr.Name, zone)
	name = strings.TrimSuffix(name, ".")

	params := url.Values{
		"domain": {name},
		"type":   {rr.Type},
	}

	switch r := rec.(type) {
	case libdns.TXT:
		params.Set("text", r.Text)
	case libdns.Address:
		params.Set("ipAddress", r.IP.String())
	case libdns.CNAME:
		params.Set("cname", strings.TrimSuffix(r.Target, "."))
	case libdns.MX:
		params.Set("preference", fmt.Sprintf("%d", r.Preference))
		params.Set("exchange", strings.TrimSuffix(r.Target, "."))
	case libdns.NS:
		params.Set("nameServer", strings.TrimSuffix(r.Target, "."))
	default:
		switch rr.Type {
		case "TXT":
			params.Set("text", rr.Data)
		case "A", "AAAA":
			params.Set("ipAddress", rr.Data)
		case "CNAME":
			params.Set("cname", strings.TrimSuffix(rr.Data, "."))
		case "MX":
			parts := strings.SplitN(rr.Data, " ", 2)
			if len(parts) == 2 {
				params.Set("preference", parts[0])
				params.Set("exchange", strings.TrimSuffix(parts[1], "."))
			}
		case "NS":
			params.Set("nameServer", strings.TrimSuffix(rr.Data, "."))
		}
	}
	return params
}

// ---- Conversion helpers ----

func toLibDNS(r dnsRecord, zone string) (libdns.Record, error) {
	zone = strings.TrimSuffix(zone, ".")
	name := strings.TrimSuffix(r.Name, ".")
	if strings.HasSuffix(name, "."+zone) {
		name = strings.TrimSuffix(name, "."+zone)
	} else if name == zone {
		name = "@"
	}

	ttl := time.Duration(r.TTL) * time.Second

	switch r.Type {
	case "TXT":
		var rdata txtRData
		if err := json.Unmarshal(r.RData, &rdata); err != nil {
			return nil, err
		}
		return libdns.TXT{Name: name, TTL: ttl, Text: rdata.Text}, nil
	case "A":
		var rdata aRData
		if err := json.Unmarshal(r.RData, &rdata); err != nil {
			return nil, err
		}
		ip, err := netip.ParseAddr(rdata.IPAddress)
		if err != nil {
			return nil, fmt.Errorf("parsing A record IP: %w", err)
		}
		return libdns.Address{Name: name, TTL: ttl, IP: ip}, nil
	case "AAAA":
		var rdata aaaaRData
		if err := json.Unmarshal(r.RData, &rdata); err != nil {
			return nil, err
		}
		ip, err := netip.ParseAddr(rdata.IPAddress)
		if err != nil {
			return nil, fmt.Errorf("parsing AAAA record IP: %w", err)
		}
		return libdns.Address{Name: name, TTL: ttl, IP: ip}, nil
	case "CNAME":
		var rdata cnameRData
		if err := json.Unmarshal(r.RData, &rdata); err != nil {
			return nil, err
		}
		return libdns.CNAME{Name: name, TTL: ttl, Target: rdata.CName + "."}, nil
	case "MX":
		var rdata mxRData
		if err := json.Unmarshal(r.RData, &rdata); err != nil {
			return nil, err
		}
		return libdns.MX{Name: name, TTL: ttl, Preference: uint16(rdata.Preference), Target: rdata.Exchange + "."}, nil
	case "NS":
		var rdata nsRData
		if err := json.Unmarshal(r.RData, &rdata); err != nil {
			return nil, err
		}
		return libdns.NS{Name: name, TTL: ttl, Target: rdata.NameServer + "."}, nil
	default:
		return nil, fmt.Errorf("unsupported record type: %s", r.Type)
	}
}
