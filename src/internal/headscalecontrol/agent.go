package headscalecontrol

import (
	"crypto/sha256"
	"encoding/hex"
	"time"

	"github.com/gentedelcondado/headscale-gateway/internal/network"
)

// NodeMetadata es una proyección deliberada de Hostinfo: no incluye tokens de
// notificaciones, identificadores de registros, entorno ni preferencias remotas.
type NodeMetadata struct {
	OS            string `json:"os,omitempty"`
	OSVersion     string `json:"os_version,omitempty"`
	ClientVersion string `json:"client_version,omitempty"`
	Distro        string `json:"distro,omitempty"`
	DistroVersion string `json:"distro_version,omitempty"`
	DeviceModel   string `json:"device_model,omitempty"`
}

type AgentNode struct {
	ID         string       `json:"id"`
	Name       string       `json:"name"`
	Identity   string       `json:"identity"`
	Online     bool         `json:"online"`
	Available  bool         `json:"available"`
	ObservedAt *time.Time   `json:"observed_at,omitempty"`
	Metadata   NodeMetadata `json:"metadata"`
}

type AgentState struct {
	TotalNodes        int         `json:"total_nodes"`
	OmittedNodes      int         `json:"omitted_nodes"`
	Enabled           bool        `json:"enabled"`
	Running           bool        `json:"running"`
	IntervalSeconds   int         `json:"interval_seconds"`
	SyncedAt          *time.Time  `json:"synced_at,omitempty"`
	AttemptedAt       *time.Time  `json:"attempted_at,omitempty"`
	ConsecutiveErrors int         `json:"consecutive_errors"`
	Error             string      `json:"error,omitempty"`
	Partial           bool        `json:"partial"`
	Stale             bool        `json:"stale"`
	Nodes             []AgentNode `json:"nodes"`
	Missing           []string    `json:"missing"`
}

func nodeIdentity(node network.Node) string {
	if node.PublicKey == "" {
		return ""
	}
	sum := sha256.Sum256([]byte(node.ID + ":" + node.PublicKey))
	return hex.EncodeToString(sum[:])
}

// MergeAgent solo conserva datos antiguos cuando coinciden ID y clave pública.
// Una IP reutilizada o un nodo reinscrito nunca hereda la versión de otro nodo.
func MergeAgent(inventory network.Inventory, observations map[string]NodeMetadata, previous AgentState, now time.Time) AgentState {
	value := AgentState{Enabled: true, IntervalSeconds: 60, SyncedAt: &now, AttemptedAt: &now, Nodes: []AgentNode{}, Missing: []string{}}
	value.TotalNodes = len(inventory.Nodes)
	if len(inventory.Nodes) > 512 {
		value.OmittedNodes = len(inventory.Nodes) - 512
		inventory.Nodes = inventory.Nodes[:512]
		value.Partial = true
	}
	old := map[string]AgentNode{}
	for _, node := range previous.Nodes {
		old[node.ID] = node
	}
	for _, node := range inventory.Nodes {
		name := node.GivenName
		if name == "" {
			name = node.Name
		}
		n := AgentNode{ID: node.ID, Name: name, Identity: nodeIdentity(node), Online: node.Online}
		if metadata, ok := observations[node.ID]; ok {
			n.Metadata = metadata
			n.ObservedAt = &now
			n.Available = true
		} else {
			value.Partial = true
			value.Missing = append(value.Missing, node.ID)
			if cached, ok := old[node.ID]; ok && n.Identity != "" && n.Identity == cached.Identity {
				n.Metadata = cached.Metadata
				n.ObservedAt = cached.ObservedAt
			}
		}
		value.Nodes = append(value.Nodes, n)
	}
	return value
}
