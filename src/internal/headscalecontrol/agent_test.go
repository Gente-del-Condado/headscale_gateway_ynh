package headscalecontrol

import (
	"github.com/gentedelcondado/headscale-gateway/internal/network"
	"testing"
	"time"
)

func TestAgentDoesNotReuseMetadataAfterNodeReregistration(t *testing.T) {
	now := time.Now().UTC()
	inventory := network.Inventory{Nodes: []network.Node{{ID: "7", Name: "tablet", PublicKey: "key-first", Online: true}}}
	first := MergeAgent(inventory, map[string]NodeMetadata{"7": {OS: "android", OSVersion: "6"}}, AgentState{}, now)
	if !first.Nodes[0].Available || first.Partial {
		t.Fatal("faltó el dato recién observado")
	}
	stale := MergeAgent(inventory, nil, first, now.Add(time.Minute))
	if stale.Nodes[0].Available || stale.Nodes[0].Metadata.OSVersion != "6" || !stale.Partial || !stale.Nodes[0].ObservedAt.Equal(now) {
		t.Fatal("dato antiguo presentado como recién observado")
	}
	inventory.Nodes[0].PublicKey = "key-new"
	changed := MergeAgent(inventory, nil, first, now.Add(time.Minute))
	if changed.Nodes[0].Metadata.OS != "" || changed.Nodes[0].ObservedAt != nil {
		t.Fatal("un nodo nuevo heredó metadatos del anterior")
	}
	removed := MergeAgent(network.Inventory{}, nil, first, now.Add(time.Minute))
	if len(removed.Nodes) != 0 {
		t.Fatal("se conservaron datos de un nodo eliminado")
	}
}
