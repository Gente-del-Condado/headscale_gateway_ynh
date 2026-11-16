package headscalecontrol

import "testing"

func TestControllerBindingRejectsCredentialedOrUnencryptedRemoteOrigins(t *testing.T) {
	base := Spec{Instance: "lab", AllowedUID: 993, HeadscaleUID: 992, HeadscaleGID: 992, Binary: "/usr/bin/headscale", ConfigPath: "/etc/headscale/config.yaml", StateDir: "/var/lib/headscale-gateway-control/lab", SocketPath: "/run/headscale-gateway-control/lab/control.sock", Unit: "headscale.service", HealthURL: "http://127.0.0.1:8080/health"}
	for _, origin := range []string{"https://user:secret@control.example.test", "http://192.0.2.28:8080", "https://control.example.test?token=secret", "https://control.example.test/api"} {
		value := base
		value.APIOrigin = origin
		if value.Validate() == nil {
			t.Fatal("se aceptó un origen API inseguro")
		}
	}
	for _, origin := range []string{"", "https://control.example.test", "http://127.0.0.1:8080"} {
		value := base
		value.APIOrigin = origin
		if err := value.Validate(); err != nil {
			t.Fatal(err)
		}
	}
}

func TestControllerUsesLinuxPathsOnEveryClientPlatform(t *testing.T) {
	value := Spec{Instance: "portable", AllowedUID: 993, HeadscaleUID: 992, HeadscaleGID: 992, Binary: "/usr/bin/headscale", ConfigPath: "/etc/headscale/config.yaml", StateDir: "/var/lib/headscale-gateway-control/portable", SocketPath: "/run/headscale-gateway-control/portable/control.sock", Unit: "headscale.service", HealthURL: "http://127.0.0.1:8080/health"}
	if err := value.Validate(); err != nil {
		t.Fatalf("el contrato Linux debe ser válido también en Windows: %v", err)
	}
	for _, invalid := range []string{`C:\headscale\config.yaml`, `\\server\share\config.yaml`, `\etc\headscale`, "relative/config.yaml", "/etc/headscale/../config.yaml", "/", "/etc/headscale\nconfig.yaml", "/etc/headscale\x00config.yaml"} {
		for _, field := range []string{"binary", "config", "records", "health_ca"} {
			t.Run(field+"/"+invalid, func(t *testing.T) {
				candidate := value
				switch field {
				case "binary":
					candidate.Binary = invalid
				case "config":
					candidate.ConfigPath = invalid
				case "records":
					candidate.RecordsPath = invalid
				case "health_ca":
					candidate.HealthCA = invalid
				}
				if candidate.Validate() == nil {
					t.Fatal("se aceptó una ruta ajena al contrato Linux")
				}
			})
		}
	}
}
