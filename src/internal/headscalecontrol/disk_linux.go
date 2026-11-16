//go:build linux && !android

package headscalecontrol

import (
	"bytes"
	"context"
	"crypto/tls"
	"crypto/x509"
	"encoding/json"
	"errors"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"go.yaml.in/yaml/v3"
)

type DiskBackend struct {
	spec     Spec
	validate func(context.Context, Snapshot) error
	restart  func(context.Context) error
	healthy  func(context.Context) error
}
type journal struct {
	BeforeConfig  fileImage  `json:"before_config"`
	BeforeRecords *fileImage `json:"before_records,omitempty"`
	After         Snapshot   `json:"after"`
	Restart       bool       `json:"restart"`
}

func NewDiskBackend(spec Spec) (*DiskBackend, error) {
	if e := spec.Validate(); e != nil {
		return nil, e
	}
	// Una IP del registro debe pertenecer al anfitrión; el chequeo no es un
	// cliente HTTP genérico y nunca sigue redirecciones ni usa proxies heredados.
	u, _ := url.Parse(spec.HealthURL)
	ip := net.ParseIP(u.Hostname())
	local := ip.IsLoopback()
	addresses, e := net.InterfaceAddrs()
	if e != nil {
		return nil, e
	}
	for _, a := range addresses {
		host, _, e := net.ParseCIDR(a.String())
		if e == nil && host.Equal(ip) {
			local = true
		}
	}
	if !local {
		return nil, errors.New("la IP de salud no pertenece al anfitrión")
	}
	if e = ensureRootDir(spec.StateDir, 0700); e != nil {
		return nil, e
	}
	state, e := os.Lstat(spec.StateDir)
	if e != nil || !state.IsDir() || state.Mode().Perm() != 0700 {
		return nil, errors.New("el estado del controlador requiere una carpeta privada 0700")
	}
	if st, ok := state.Sys().(*syscall.Stat_t); !ok || st.Uid != 0 {
		return nil, errors.New("el estado del controlador debe pertenecer a root")
	}
	b := &DiskBackend{spec: spec}
	b.validate = b.validateIsolated
	b.restart = b.restartService
	b.healthy = b.checkHealth
	return b, nil
}

func (b *DiskBackend) images() (fileImage, *fileImage, error) {
	config, e := readImage(b.spec.ConfigPath)
	if e != nil {
		return fileImage{}, nil, e
	}
	if config.UID != 0 && config.UID != b.spec.HeadscaleUID {
		return fileImage{}, nil, errors.New("propietario de configuración Headscale inesperado")
	}
	var records *fileImage
	if b.spec.RecordsPath != "" {
		image, e := readImage(b.spec.RecordsPath)
		if e != nil {
			return fileImage{}, nil, e
		}
		if image.UID != 0 && image.UID != b.spec.HeadscaleUID {
			return fileImage{}, nil, errors.New("propietario de registros Headscale inesperado")
		}
		records = &image
	}
	return config, records, nil
}

func (b *DiskBackend) Read(ctx context.Context) (Snapshot, error) {
	if e := ctx.Err(); e != nil {
		return Snapshot{}, e
	}
	config, records, e := b.images()
	if e != nil {
		return Snapshot{}, e
	}
	value := Snapshot{Config: config.Data}
	if records != nil {
		value.Records = records.Data
	}
	return value, nil
}

func (b *DiskBackend) journalPath() string { return filepath.Join(b.spec.StateDir, "pending.json") }

// Recover no sobrescribe una edición ajena: los archivos deben coincidir con
// el candidato o su copia previa. Un diario dudoso bloquea nuevas operaciones.
func (b *DiskBackend) Recover(ctx context.Context) error {
	image, e := readImageLimit(b.journalPath(), 8<<20)
	if os.IsNotExist(e) {
		return nil
	}
	if e != nil {
		return e
	}
	if image.UID != 0 || image.Mode != 0600 {
		return errors.New("diario de recuperación inseguro")
	}
	var entry journal
	if json.Unmarshal(image.Data, &entry) != nil {
		return errors.New("diario de recuperación inválido")
	}
	config, records, e := b.images()
	if e != nil {
		return e
	}
	if !bytes.Equal(config.Data, entry.BeforeConfig.Data) && !bytes.Equal(config.Data, entry.After.Config) {
		return errors.New("configuración ajena modificada durante la recuperación")
	}
	if (records == nil) != (entry.BeforeRecords == nil) {
		return errors.New("registro de recuperación incompatible")
	}
	if records != nil && !bytes.Equal(records.Data, entry.BeforeRecords.Data) && !bytes.Equal(records.Data, entry.After.Records) {
		return errors.New("registros ajenos modificados durante la recuperación")
	}
	if e = writeImage(b.spec.ConfigPath, entry.BeforeConfig); e != nil {
		return e
	}
	if entry.BeforeRecords != nil {
		if e = writeImage(b.spec.RecordsPath, *entry.BeforeRecords); e != nil {
			return e
		}
	}
	if entry.Restart {
		if e = b.restart(ctx); e != nil {
			return e
		}
	}
	if e = b.healthy(ctx); e != nil {
		return e
	}
	return removeFile(b.journalPath())
}

func (b *DiskBackend) Transact(ctx context.Context, before, after Snapshot, restart bool, notify func(string)) error {
	if _, e := os.Lstat(b.journalPath()); !os.IsNotExist(e) {
		return errors.New("hay una recuperación Headscale pendiente")
	}
	notify("validating")
	if e := b.validate(ctx, after); e != nil {
		return errors.New("Headscale no aceptó el candidato aislado")
	}
	config, records, e := b.images()
	if e != nil {
		return e
	}
	currentRecords := []byte(nil)
	if records != nil {
		currentRecords = records.Data
	}
	if revision(config.Data, currentRecords) != revision(before.Config, before.Records) {
		return errors.New("la configuración cambió durante la validación")
	}
	entry := journal{BeforeConfig: config, BeforeRecords: records, After: after, Restart: restart}
	data, e := json.Marshal(entry)
	if e != nil {
		return e
	}
	if e = writeImage(b.journalPath(), fileImage{Data: data, Mode: 0600, UID: 0, GID: 0}); e != nil {
		return e
	}
	notify("applying")
	apply := func() error {
		if records != nil && !bytes.Equal(records.Data, after.Records) {
			value := *records
			value.Data = after.Records
			if e := writeImage(b.spec.RecordsPath, value); e != nil {
				return e
			}
		}
		if !bytes.Equal(config.Data, after.Config) {
			value := config
			value.Data = after.Config
			if e := writeImage(b.spec.ConfigPath, value); e != nil {
				return e
			}
		}
		if restart {
			notify("restarting")
			if e := b.restart(ctx); e != nil {
				return e
			}
		}
		notify("checking")
		if e := b.healthy(ctx); e != nil {
			return e
		}
		return removeFile(b.journalPath())
	}
	if e = apply(); e != nil {
		notify("rolling_back")
		// La restauración conserva su propio plazo aunque haya expirado el de
		// validación/aplicación. El diario permanece si no consigue recuperarse.
		recovery, cancel := context.WithTimeout(context.Background(), 75*time.Second)
		defer cancel()
		if rollback := b.Recover(recovery); rollback != nil {
			return &TransactionError{Recovered: false}
		}
		return &TransactionError{Recovered: true}
	}
	return nil
}

func (b *DiskBackend) restartService(ctx context.Context) error {
	command := exec.CommandContext(ctx, "/usr/bin/systemctl", "restart", "--", b.spec.Unit)
	command.Stdout = io.Discard
	command.Stderr = io.Discard
	if command.Run() != nil {
		return errors.New("no se pudo reiniciar el servicio Headscale")
	}
	return nil
}

func (b *DiskBackend) checkHealth(ctx context.Context) error {
	tlsConfig := &tls.Config{MinVersion: tls.VersionTLS12}
	if b.spec.HealthCA != "" {
		image, e := readImage(b.spec.HealthCA)
		if e != nil {
			return errors.New("CA local de salud no disponible")
		}
		roots := x509.NewCertPool()
		if !roots.AppendCertsFromPEM(image.Data) {
			return errors.New("CA local de salud inválida")
		}
		tlsConfig.RootCAs = roots
	}
	transport := &http.Transport{TLSClientConfig: tlsConfig, Proxy: nil}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, Timeout: 3 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
	deadline := time.Now().Add(45 * time.Second)
	for time.Now().Before(deadline) {
		req, e := http.NewRequestWithContext(ctx, http.MethodGet, b.spec.HealthURL, nil)
		if e != nil {
			return e
		}
		response, e := client.Do(req)
		if e == nil {
			io.Copy(io.Discard, io.LimitReader(response.Body, 4096))
			response.Body.Close()
			if response.StatusCode == 200 {
				return nil
			}
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(time.Second):
		}
	}
	return errors.New("Headscale no recuperó su estado saludable")
}

// configtest de Headscale 0.29 construye estado y abre SQLite y claves. La
// validación usa archivos nuevos y una cuenta sin privilegios; nunca abre la
// base activa, el socket ni las claves Noise/DERP del servicio existente.
func (b *DiskBackend) validateIsolated(ctx context.Context, snapshot Snapshot) error {
	p, e := parse(snapshot.Config, snapshot.Records, b.spec.RecordsPath != "")
	if e != nil {
		return e
	}
	root := p.tree.Content[0]
	databaseType := scalar(child(root, "database"), "type")
	if databaseType != "sqlite" && databaseType != "sqlite3" {
		return errors.New("la validación aislada requiere SQLite")
	}
	dnsPath := scalar(child(root, "dns"), "extra_records_path")
	if b.spec.RecordsPath != "" && dnsPath != b.spec.RecordsPath {
		return errors.New("extra_records_path no coincide con el registro local autorizado")
	}
	temporary, e := os.MkdirTemp("", "hgw-headscale-validation-")
	if e != nil {
		return e
	}
	defer os.RemoveAll(temporary)
	if e = os.Chown(temporary, 0, b.spec.HeadscaleGID); e != nil {
		return e
	}
	if e = os.Chmod(temporary, 0750); e != nil {
		return e
	}
	work := filepath.Join(temporary, "state")
	if e = os.Mkdir(work, 0700); e != nil {
		return e
	}
	if e = os.Chown(work, b.spec.HeadscaleUID, b.spec.HeadscaleGID); e != nil {
		return e
	}
	for _, item := range []struct {
		path  []string
		value any
	}{
		{[]string{"database", "sqlite", "path"}, filepath.Join(work, "db.sqlite")},
		{[]string{"noise", "private_key_path"}, filepath.Join(work, "noise.key")},
		{[]string{"unix_socket"}, filepath.Join(work, "headscale.sock")},
		{[]string{"derp", "server", "private_key_path"}, filepath.Join(work, "derp.key")},
		{[]string{"tls_letsencrypt_cache_dir"}, filepath.Join(work, "acme")},
	} {
		if e = set(root, item.path, item.value); e != nil {
			return e
		}
	}
	if dnsPath != "" {
		recordsPath := filepath.Join(temporary, "records.json")
		if e = writeImage(recordsPath, fileImage{Data: snapshot.Records, Mode: 0440, UID: 0, GID: b.spec.HeadscaleGID}); e != nil {
			return e
		}
		if e = set(root, []string{"dns", "extra_records_path"}, recordsPath); e != nil {
			return e
		}
	}
	var output bytes.Buffer
	encoder := yaml.NewEncoder(&output)
	if encoder.Encode(&p.tree) != nil {
		return errors.New("candidato aislado no serializable")
	}
	path := filepath.Join(temporary, "config.yaml")
	if e = writeImage(path, fileImage{Data: output.Bytes(), Mode: 0440, UID: 0, GID: b.spec.HeadscaleGID}); e != nil {
		return e
	}
	validation, cancel := context.WithTimeout(ctx, 35*time.Second)
	defer cancel()
	command := exec.CommandContext(validation, b.spec.Binary, "--config", path, "configtest")
	command.Env = []string{"PATH=/usr/sbin:/usr/bin:/sbin:/bin", "HOME=" + work, "LANG=C"}
	command.Dir = work
	command.SysProcAttr = &syscall.SysProcAttr{Credential: &syscall.Credential{Uid: uint32(b.spec.HeadscaleUID), Gid: uint32(b.spec.HeadscaleGID), Groups: []uint32{}}}
	command.Stdout = io.Discard
	command.Stderr = io.Discard
	if command.Run() != nil {
		return errors.New("configtest rechazó el candidato aislado")
	}
	return nil
}

// loadSpec solo acepta un registro root 0600. No admite una segunda estructura
// JSON ni argumentos de ejecución enviados por el usuario del panel.
func loadSpec(path string) (Spec, error) {
	image, e := readImageLimit(path, 16384)
	if e != nil {
		return Spec{}, e
	}
	if image.UID != 0 || image.Mode != 0600 {
		return Spec{}, errors.New("el registro requiere propietario root y modo 0600")
	}
	decoder := json.NewDecoder(bytes.NewReader(image.Data))
	decoder.DisallowUnknownFields()
	var spec Spec
	if decoder.Decode(&spec) != nil {
		return Spec{}, errors.New("registro del controlador inválido")
	}
	var extra any
	if decoder.Decode(&extra) != io.EOF {
		return Spec{}, errors.New("registro del controlador ambiguo")
	}
	if strings.ContainsAny(spec.Instance, "\r\n\x00") {
		return Spec{}, errors.New("nombre de instancia inválido")
	}
	return spec, spec.Validate()
}
