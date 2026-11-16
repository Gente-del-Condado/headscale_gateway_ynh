package main

import (
	"context"
	"errors"
	"strings"
	"sync"
	"time"

	"github.com/gentedelcondado/headscale-gateway/internal/diagnostics"
	"github.com/gentedelcondado/headscale-gateway/internal/headscalecontrol"
	"github.com/gentedelcondado/headscale-gateway/internal/network"
	"tailscale.com/types/key"
)

func (a *adminController) headscaleAgentState() (headscalecontrol.AgentState, error) {
	value := headscalecontrol.AgentState{IntervalSeconds: 60, Nodes: []headscalecontrol.AgentNode{}, Missing: []string{}}
	db, e := openCatalog(a.configPath)
	if e != nil {
		return value, e
	}
	defer db.Close()
	_, e = db.GetJSON("headscale.agent.v1", &value)
	value.Enabled = a.runtime.currentConfig().HeadscaleAgentEnabled
	value.Running = a.agentRunning.Load()
	value.Stale = value.Error != "" || !value.Enabled || value.SyncedAt == nil || time.Since(*value.SyncedAt) > 2*time.Minute
	return value, e
}

func (a *adminController) HeadscaleAgentState(ctx context.Context) (headscalecontrol.AgentState, error) {
	if a.runtime.currentConfig().HeadscaleControlMode == "remote" {
		c, e := a.headscaleControlClient(ctx)
		if e != nil {
			return headscalecontrol.AgentState{}, e
		}
		defer c.Close()
		return c.Agent(ctx)
	}
	return a.headscaleAgentState()
}

func (a *adminController) HeadscaleAgentSync(ctx context.Context) (headscalecontrol.AgentState, error) {
	if a.runtime.currentConfig().HeadscaleControlMode == "remote" {
		c, e := a.headscaleControlClient(ctx)
		if e != nil {
			return headscalecontrol.AgentState{}, e
		}
		defer c.Close()
		return c.SyncAgent(ctx)
	}
	if !a.runtime.currentConfig().HeadscaleAgentEnabled {
		return headscalecontrol.AgentState{}, errors.New("activa la sincronización de información de nodos en Configuración")
	}
	a.queueHeadscaleAgent()
	return a.headscaleAgentState()
}

func (a *adminController) headscaleAgentLoop(ctx context.Context) {
	ticker := time.NewTicker(time.Minute)
	defer ticker.Stop()
	for {
		cfg := a.runtime.currentConfig()
		if cfg.HeadscaleAgentEnabled && cfg.HeadscaleControlMode != "remote" {
			a.queueHeadscaleAgent()
		}
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
	}
}

func (a *adminController) queueHeadscaleAgent() {
	if !a.agentMu.TryLock() {
		return
	}
	a.agentRunning.Store(true)
	// Se vincula al proceso, no al navegador que inició la sincronización.
	work, cancel := context.WithTimeout(processContext, 35*time.Second)
	go func() {
		defer a.agentMu.Unlock()
		defer a.agentRunning.Store(false)
		defer cancel()
		a.collectHeadscaleAgent(work)
	}()
}

func metadataText(value string) string {
	value = strings.Map(func(r rune) rune {
		if r < ' ' || r == 127 {
			return -1
		}
		return r
	}, value)
	runes := []rune(value)
	if len(runes) > 96 {
		runes = runes[:96]
	}
	return string(runes)
}

func (a *adminController) collectHeadscaleAgent(ctx context.Context) {
	previous, e := a.headscaleAgentState()
	if e != nil {
		return
	}
	cfg := a.runtime.currentConfig()
	now := time.Now().UTC()
	inventory, e := network.List(ctx, cfg.HeadscaleURL, cfg.HeadscaleAPIKey)
	value := previous
	value.AttemptedAt = &now
	if e != nil {
		value.ConsecutiveErrors++
		value.Error = "No se pudo sincronizar el inventario de Headscale; se conservan los últimos datos con su fecha."
		value.Stale = true
	} else {
		observations := map[string]headscalecontrol.NodeMetadata{}
		vpn := a.networkServer()
		if vpn != nil {
			if client, e := vpn.LocalClient(); e == nil {
				var workers sync.WaitGroup
				var mutex sync.Mutex
				limit := make(chan struct{}, 4)
				nodes := inventory.Nodes
				if len(nodes) > 512 {
					nodes = nodes[:512]
				}
				for _, node := range nodes {
					if ctx.Err() != nil {
						break
					}
					var public key.NodePublic
					if public.UnmarshalText([]byte(node.PublicKey)) != nil {
						continue
					}
					limit <- struct{}{}
					workers.Add(1)
					go func(node network.Node, public key.NodePublic) {
						defer workers.Done()
						defer func() { <-limit }()
						lookup, cancel := context.WithTimeout(ctx, 2*time.Second)
						defer cancel()
						who, e := client.WhoIsNodeKey(lookup, public)
						if e != nil || who == nil || who.Node == nil || who.Node.Key != public || !who.Node.Hostinfo.Valid() {
							return
						}
						h := who.Node.Hostinfo
						metadata := headscalecontrol.NodeMetadata{OS: metadataText(h.OS()), OSVersion: metadataText(h.OSVersion()), ClientVersion: metadataText(h.IPNVersion()), Distro: metadataText(h.Distro()), DistroVersion: metadataText(h.DistroVersion()), DeviceModel: metadataText(h.DeviceModel())}
						mutex.Lock()
						observations[node.ID] = metadata
						mutex.Unlock()
					}(node, public)
				}
				workers.Wait()
			}
		}
		value = headscalecontrol.MergeAgent(inventory, observations, previous, now)
	}
	value.Enabled = cfg.HeadscaleAgentEnabled
	value.Running = false
	db, e := openCatalog(a.configPath)
	if e != nil {
		return
	}
	defer db.Close()
	if e = db.PutJSON("headscale.agent.v1", value); e != nil {
		diagnostics.Emit("admin", diagnostics.Warn, "HGW-HS-AGENT-STORE", "No se pudo conservar el estado del observador Headscale")
	}
}
