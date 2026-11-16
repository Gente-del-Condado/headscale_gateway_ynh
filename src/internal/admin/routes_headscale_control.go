package admin

import (
	"context"
	"errors"
	"net/http"

	"github.com/gentedelcondado/headscale-gateway/internal/headscalecontrol"
	"github.com/gentedelcondado/headscale-gateway/internal/network"
)

type HeadscaleControlController interface {
	HeadscaleControlIsLocal() bool
	HeadscaleControlInfo(context.Context) (headscalecontrol.Info, error)
	HeadscaleControlDocument(context.Context) (headscalecontrol.Document, error)
	HeadscaleControlPreview(context.Context, headscalecontrol.Change) (headscalecontrol.Preview, error)
	HeadscaleControlApply(context.Context, headscalecontrol.Change) (headscalecontrol.Operation, error)
	HeadscaleControlOperation(context.Context, string) (headscalecontrol.Operation, error)
}

type HeadscaleAgentController interface {
	HeadscaleAgentState(context.Context) (headscalecontrol.AgentState, error)
	HeadscaleAgentSync(context.Context) (headscalecontrol.AgentState, error)
}

func (s *Server) registerHeadscaleControlRoutes(mux routeRegistrar) {
	gate := func(fn func(http.ResponseWriter, *http.Request, HeadscaleControlController)) http.HandlerFunc {
		return s.secure(func(w http.ResponseWriter, r *http.Request) {
			token, _ := r.Context().Value(tokenRequestKey{}).(bool)
			// Una sesión operator no obtiene estos poderes por su rol habitual.
			// Los tokens requieren además el alcance específico ya comprobado por
			// secure y la exposición Bearer activada explícitamente para el módulo.
			if !s.isAdminRequest(r) && !token {
				problem(w, 403, "administración Headscale reservada al administrador o a una delegación explícita")
				return
			}
			ctl, ok := s.controller.(HeadscaleControlController)
			if !ok {
				problem(w, 501, "controlador Headscale no disponible")
				return
			}
			if token && !ctl.HeadscaleControlIsLocal() {
				problem(w, 403, "una delegación solo puede dirigirse al controlador local de Headscale; no se reenvía entre Gateway")
				return
			}
			if token {
				if _, e := ctl.HeadscaleControlInfo(r.Context()); e != nil {
					problem(w, 409, "el vínculo local del coordinador no está disponible o no coincide con la URL Headscale")
					return
				}
			}
			w.Header().Set("Cache-Control", "no-store")
			fn(w, r, ctl)
		})
	}
	finish := func(w http.ResponseWriter, status int, value any, e error) {
		if e != nil {
			problem(w, 409, e.Error())
			return
		}
		reply(w, status, value, nil)
	}
	mux.HandleFunc("GET /api/v1/network/control/agent", gate(func(w http.ResponseWriter, r *http.Request, _ HeadscaleControlController) {
		c, ok := s.controller.(HeadscaleAgentController)
		if !ok {
			problem(w, 501, "observador Headscale no disponible")
			return
		}
		v, e := c.HeadscaleAgentState(r.Context())
		finish(w, 200, v, e)
	}))
	mux.HandleFunc("POST /api/v1/network/control/agent/sync", gate(func(w http.ResponseWriter, r *http.Request, _ HeadscaleControlController) {
		c, ok := s.controller.(HeadscaleAgentController)
		if !ok {
			problem(w, 501, "observador Headscale no disponible")
			return
		}
		v, e := c.HeadscaleAgentSync(r.Context())
		finish(w, 202, v, e)
	}))
	mux.HandleFunc("GET /api/v1/network/control/info", gate(func(w http.ResponseWriter, r *http.Request, c HeadscaleControlController) {
		v, e := c.HeadscaleControlInfo(r.Context())
		if token, _ := r.Context().Value(tokenRequestKey{}).(bool); token {
			write := s.recoveryTokenMatches(r.Header.Get("Authorization"))
			for _, scope := range r.Context().Value(tokenScopesKey{}).([]string) {
				if scope == "headscale-write" {
					write = true
				}
			}
			v.CanWrite = v.CanWrite && write && rolePermits(r.Context().Value(adminRoleKey{}).(string), "headscale-write", http.MethodPost) && s.policy != nil && s.policy.TokenAllowed("headscale-write")
			v.CanSyncAgent = v.CanSyncAgent && write && rolePermits(r.Context().Value(adminRoleKey{}).(string), "headscale-write", http.MethodPost) && s.policy != nil && s.policy.TokenAllowed("headscale-write")
		}
		finish(w, 200, v, e)
	}))
	mux.HandleFunc("GET /api/v1/network/control/document", gate(func(w http.ResponseWriter, r *http.Request, c HeadscaleControlController) {
		v, e := c.HeadscaleControlDocument(r.Context())
		finish(w, 200, v, e)
	}))
	mux.HandleFunc("POST /api/v1/network/control/preview", gate(func(w http.ResponseWriter, r *http.Request, c HeadscaleControlController) {
		var change headscalecontrol.Change
		if !decodeLimit(w, r, &change, headscalecontrol.MaxDocument) {
			return
		}
		v, e := c.HeadscaleControlPreview(r.Context(), change)
		finish(w, 200, v, e)
	}))
	mux.HandleFunc("POST /api/v1/network/control/apply", gate(func(w http.ResponseWriter, r *http.Request, c HeadscaleControlController) {
		var change headscalecontrol.Change
		if !decodeLimit(w, r, &change, headscalecontrol.MaxDocument) {
			return
		}
		v, e := c.HeadscaleControlApply(r.Context(), change)
		finish(w, 202, v, e)
	}))
	mux.HandleFunc("GET /api/v1/network/control/operations/{id}", gate(func(w http.ResponseWriter, r *http.Request, c HeadscaleControlController) {
		v, e := c.HeadscaleControlOperation(r.Context(), r.PathValue("id"))
		var upstream *headscalecontrol.HTTPError
		if errors.As(e, &upstream) {
			if upstream.StatusCode == 404 {
				problem(w, 404, "la operación ya no está en este proceso; lee el estado actual del controlador antes de continuar")
				return
			}
			if upstream.StatusCode == 401 || upstream.StatusCode == 403 {
				problem(w, 403, "la delegación del controlador ha caducado o fue revocada")
				return
			}
		}
		finish(w, 200, v, e)
	}))
	// La administración delegada reutiliza los mismos controladores tipados
	// que el panel local, sin publicar un proxy HTTP o CLI de propósito general.
	management := func(w http.ResponseWriter) (HeadscaleManagementController, bool) {
		c, ok := s.controller.(HeadscaleManagementController)
		if !ok {
			problem(w, 501, "administración Headscale no disponible")
		}
		return c, ok
	}
	mux.HandleFunc("GET /api/v1/network/control/headscale/users", gate(func(w http.ResponseWriter, r *http.Request, _ HeadscaleControlController) {
		if c, ok := management(w); ok {
			v, e := c.HeadscaleUsers(r.Context())
			finish(w, 200, v, e)
		}
	}))
	mux.HandleFunc("GET /api/v1/network/control/headscale/keys", gate(func(w http.ResponseWriter, r *http.Request, _ HeadscaleControlController) {
		if c, ok := management(w); ok {
			v, e := c.HeadscalePreAuthKeys(r.Context())
			finish(w, 200, v, e)
		}
	}))
	mux.HandleFunc("POST /api/v1/network/control/headscale/action", gate(func(w http.ResponseWriter, r *http.Request, _ HeadscaleControlController) {
		if c, ok := management(w); ok {
			var action network.HeadscaleAction
			if !decode(w, r, &action) {
				return
			}
			v, e := c.HeadscaleManage(r.Context(), action)
			finish(w, 200, v, e)
		}
	}))
	mux.HandleFunc("GET /api/v1/network/control/headscale/nodes", gate(func(w http.ResponseWriter, r *http.Request, _ HeadscaleControlController) {
		c, ok := s.controller.(NetworkController)
		if !ok {
			problem(w, 501, "inventario Headscale no disponible")
			return
		}
		v, e := c.NetworkNodes(r.Context())
		finish(w, 200, v, e)
	}))
	mux.HandleFunc("GET /api/v1/network/control/headscale/policy", gate(func(w http.ResponseWriter, r *http.Request, _ HeadscaleControlController) {
		c, ok := s.controller.(HeadscalePolicyDNSController)
		if !ok {
			problem(w, 501, "política Headscale no disponible")
			return
		}
		v, e := c.HeadscaleGetPolicy(r.Context())
		finish(w, 200, v, e)
	}))
	mux.HandleFunc("PUT /api/v1/network/control/headscale/policy", gate(func(w http.ResponseWriter, r *http.Request, _ HeadscaleControlController) {
		c, ok := s.controller.(HeadscalePolicyDNSController)
		if !ok {
			problem(w, 501, "política Headscale no disponible")
			return
		}
		var change struct {
			Policy   string `json:"policy"`
			Revision string `json:"revision"`
		}
		if !decodeLimit(w, r, &change, 101<<10) {
			return
		}
		v, e := c.HeadscaleSetPolicy(r.Context(), change.Policy, change.Revision)
		finish(w, 200, v, e)
	}))
}
