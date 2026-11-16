package network

// HeadscaleAction mantiene un catálogo cerrado de órdenes administrativas.
// Se comparte entre el panel, la API y el cliente de control remoto.
type HeadscaleAction struct {
	Action    string   `json:"action"`
	ID        string   `json:"id,omitempty"`
	Name      string   `json:"name,omitempty"`
	User      string   `json:"user,omitempty"`
	Routes    []string `json:"routes,omitempty"`
	Tags      []string `json:"tags,omitempty"`
	Reusable  bool     `json:"reusable,omitempty"`
	Ephemeral bool     `json:"ephemeral,omitempty"`
	Hours     int      `json:"hours,omitempty"`
}
