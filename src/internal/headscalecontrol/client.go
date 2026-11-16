package headscalecontrol

import (
	"bytes"
	"context"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/gentedelcondado/headscale-gateway/internal/network"
	"io"
	"net"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"time"
)

type Client struct {
	http   *http.Client
	origin string
	token  string
}

type HTTPError struct {
	StatusCode int
	Message    string
}

func (e *HTTPError) Error() string {
	if e.Message != "" {
		return e.Message
	}
	return fmt.Sprintf("controlador Headscale: HTTP %d; revisa permisos, estado y revisión del documento", e.StatusCode)
}

// NewLocalClient no interpreta rutas de archivos enviadas desde el navegador.
// El socket procede exclusivamente del registro del instalador/anfitrión.
func NewLocalClient(socket string) *Client {
	transport := &http.Transport{Proxy: nil, DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
		return (&net.Dialer{Timeout: 3 * time.Second}).DialContext(ctx, "unix", socket)
	}}
	return &Client{http: &http.Client{Transport: transport, Timeout: 12 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}, origin: "http://headscale-controller"}
}

// NewRemoteClient exige que el llamante haya construido el transporte privado
// con IP fijada y TLS autenticado. No cambia raíces ni omite comprobaciones.
// Las credenciales se envían solo al origen seleccionado y nunca se redirigen.
func NewRemoteClient(transport *http.Transport, origin, token string) (*Client, error) {
	u, e := url.Parse(origin)
	if e != nil || u.Scheme != "https" || u.Hostname() == "" || u.User != nil || u.RawQuery != "" || u.Fragment != "" || u.Path != "" && u.Path != "/" || transport == nil || transport.TLSClientConfig == nil || transport.TLSClientConfig.InsecureSkipVerify || token == "" || strings.ContainsAny(token, "\r\n") {
		return nil, errors.New("controlador remoto no autorizado")
	}
	if transport.Proxy != nil || transport.DialContext == nil || transport.DialTLSContext != nil || transport.DialTLS != nil || transport.TLSClientConfig.ServerName != u.Hostname() {
		return nil, errors.New("el transporte del controlador debe fijar la IP y verificar su nombre TLS sin proxies")
	}
	return &Client{http: &http.Client{Transport: transport, Timeout: 15 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}, origin: strings.TrimRight(origin, "/") + "/api/v1/network/control", token: token}, nil
}

func (c *Client) call(ctx context.Context, method, path string, input, output any) error {
	var body io.Reader
	if input != nil {
		data, e := json.Marshal(input)
		if e != nil {
			return errors.New("cambio del controlador no serializable")
		}
		body = bytes.NewReader(data)
	}
	req, e := http.NewRequestWithContext(ctx, method, c.origin+path, body)
	if e != nil {
		return errors.New("solicitud del controlador inválida")
	}
	if input != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if c.token != "" {
		req.Header.Set("Authorization", "Bearer "+c.token)
	}
	response, e := c.http.Do(req)
	if e != nil {
		return errors.New("no se pudo conectar con el controlador Headscale")
	}
	defer response.Body.Close()
	if response.StatusCode != 200 && response.StatusCode != 202 {
		value := &HTTPError{StatusCode: response.StatusCode}
		if c.token == "" {
			var local struct {
				Error string `json:"error"`
			}
			if json.NewDecoder(io.LimitReader(response.Body, 4096)).Decode(&local) == nil && len(local.Error) <= 512 {
				value.Message = local.Error
			}
		}
		return value
	}
	data, e := io.ReadAll(io.LimitReader(response.Body, MaxDocument+1))
	if e != nil || len(data) > MaxDocument {
		return errors.New("respuesta del controlador demasiado grande o incompleta")
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	if decoder.Decode(output) != nil {
		return errors.New("respuesta del controlador Headscale no válida")
	}
	var extra any
	if decoder.Decode(&extra) != io.EOF {
		return errors.New("respuesta ambigua del controlador Headscale")
	}
	return nil
}

func (c *Client) Document(ctx context.Context) (Document, error) {
	var value Document
	e := c.call(ctx, "GET", "/document", nil, &value)
	if e == nil {
		raw, err := hex.DecodeString(value.Revision)
		if err != nil || len(raw) != 32 || value.Instance == "" {
			e = errors.New("documento del controlador sin revisión o instancia válida")
		}
	}
	return value, e
}
func (c *Client) Preview(ctx context.Context, change Change) (Preview, error) {
	var value Preview
	e := c.call(ctx, "POST", "/preview", change, &value)
	return value, e
}
func (c *Client) Apply(ctx context.Context, change Change) (Operation, error) {
	var value Operation
	e := c.call(ctx, "POST", "/apply", change, &value)
	return value, e
}

var operationID = regexp.MustCompile(`^[0-9a-f]{32}$`)

func (c *Client) Operation(ctx context.Context, id string) (Operation, error) {
	if !operationID.MatchString(id) {
		return Operation{}, errors.New("identificador de operación inválido")
	}
	var value Operation
	e := c.call(ctx, "GET", "/operations/"+id, nil, &value)
	return value, e
}
func (c *Client) Close() { c.http.CloseIdleConnections() }

func (c *Client) Info(ctx context.Context) (Info, error) {
	var v Info
	e := c.call(ctx, "GET", "/info", nil, &v)
	return v, e
}

func (c *Client) Users(ctx context.Context) (json.RawMessage, error) {
	var v json.RawMessage
	e := c.call(ctx, "GET", "/headscale/users", nil, &v)
	return v, e
}
func (c *Client) PreAuthKeys(ctx context.Context) (json.RawMessage, error) {
	var v json.RawMessage
	e := c.call(ctx, "GET", "/headscale/keys", nil, &v)
	return v, e
}
func (c *Client) Manage(ctx context.Context, action network.HeadscaleAction) (json.RawMessage, error) {
	var v json.RawMessage
	e := c.call(ctx, "POST", "/headscale/action", action, &v)
	return v, e
}
func (c *Client) GetPolicy(ctx context.Context) (network.PolicyDocument, error) {
	var v network.PolicyDocument
	e := c.call(ctx, "GET", "/headscale/policy", nil, &v)
	return v, e
}
func (c *Client) SetPolicy(ctx context.Context, policy, revision string) (network.PolicyDocument, error) {
	var v network.PolicyDocument
	e := c.call(ctx, "PUT", "/headscale/policy", map[string]string{"policy": policy, "revision": revision}, &v)
	return v, e
}
func (c *Client) Nodes(ctx context.Context) (network.Inventory, error) {
	var v network.Inventory
	e := c.call(ctx, "GET", "/headscale/nodes", nil, &v)
	return v, e
}

func (c *Client) Agent(ctx context.Context) (AgentState, error) {
	var v AgentState
	e := c.call(ctx, "GET", "/agent", nil, &v)
	return v, e
}
func (c *Client) SyncAgent(ctx context.Context) (AgentState, error) {
	var v AgentState
	e := c.call(ctx, "POST", "/agent/sync", struct{}{}, &v)
	return v, e
}

func (c *Client) CoordinatorOrigin(ctx context.Context) (string, error) {
	var value struct {
		Origin string `json:"coordinator_origin"`
	}
	e := c.call(ctx, http.MethodGet, "/identity", nil, &value)
	return value.Origin, e
}
