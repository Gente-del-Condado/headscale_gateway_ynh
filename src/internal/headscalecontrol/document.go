package headscalecontrol

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"net/url"
	"strings"

	"github.com/gentedelcondado/headscale-gateway/internal/network"
	"go.yaml.in/yaml/v3"
)

const MaxDocument = 1 << 20

type parsed struct {
	tree     yaml.Node
	document Document
}

// La revisión incluye los dos archivos: editar registros también invalida un
// formulario DNS abierto. No se devuelve el contenido completo del coordinador.
func revision(config, records []byte) string {
	h := sha256.New()
	h.Write(config)
	h.Write([]byte{0})
	h.Write(records)
	return hex.EncodeToString(h.Sum(nil))
}

func child(node *yaml.Node, key string) *yaml.Node {
	if node == nil || node.Kind != yaml.MappingNode {
		return nil
	}
	for i := 0; i < len(node.Content); i += 2 {
		if node.Content[i].Value == key {
			return node.Content[i+1]
		}
	}
	return nil
}

func scalar(node *yaml.Node, key string) string {
	if n := child(node, key); n != nil && n.Kind == yaml.ScalarNode {
		return n.Value
	}
	return ""
}

// No se expanden alias, claves duplicadas ni documentos múltiples. Rechazar
// configuraciones ambiguas es preferible a modificar secretos referenciados
// indirectamente desde otro apartado. Los errores excluyen valores del YAML.
func safeTree(n *yaml.Node, depth int) bool {
	if depth > 32 || n.Kind == yaml.AliasNode || n.Anchor != "" {
		return false
	}
	if n.Kind == yaml.MappingNode {
		seen := map[string]bool{}
		for i := 0; i < len(n.Content); i += 2 {
			k := n.Content[i]
			if k.Kind != yaml.ScalarNode || k.Tag != "!!str" || seen[k.Value] {
				return false
			}
			seen[k.Value] = true
		}
	}
	for _, c := range n.Content {
		if !safeTree(c, depth+1) {
			return false
		}
	}
	return true
}

func parse(config, records []byte, recordsWritable bool) (*parsed, error) {
	if len(config) == 0 || len(config) > MaxDocument || len(records) > MaxDocument {
		return nil, errors.New("configuración Headscale vacía o demasiado grande")
	}
	p := &parsed{}
	decoder := yaml.NewDecoder(bytes.NewReader(config))
	if e := decoder.Decode(&p.tree); e != nil || len(p.tree.Content) != 1 || p.tree.Content[0].Kind != yaml.MappingNode || !safeTree(&p.tree, 0) {
		return nil, errors.New("YAML Headscale inválido o ambiguo")
	}
	var second yaml.Node
	if decoder.Decode(&second) != io.EOF {
		return nil, errors.New("se requiere un único documento YAML Headscale")
	}
	root := p.tree.Content[0]
	p.document.CoordinatorOrigin = scalar(root, "server_url")
	if e := network.ValidateURL(p.document.CoordinatorOrigin); e != nil {
		return nil, errors.New("origen del coordinador no válido o con credenciales")
	}
	dns := child(root, "dns")
	p.document.DNS.MagicDNS = true
	p.document.DNS.OverrideLocalDNS = true
	if dns == nil || dns.Kind != yaml.MappingNode || dns.Decode(&p.document.DNS) != nil {
		return nil, errors.New("apartado DNS de Headscale no reconocido")
	}
	if oidc := child(root, "oidc"); oidc != nil && scalar(oidc, "issuer") != "" {
		p.document.OIDC = &Restrictions{}
		if oidc.Decode(p.document.OIDC) != nil {
			return nil, errors.New("restricciones OIDC de Headscale no reconocidas")
		}
	}
	p.document.Records = []Record{}
	if len(records) > 0 {
		decoder := json.NewDecoder(bytes.NewReader(records))
		decoder.DisallowUnknownFields()
		if decoder.Decode(&p.document.Records) != nil {
			return nil, errors.New("archivo de registros MagicDNS inválido")
		}
		var extra any
		if decoder.Decode(&extra) != io.EOF {
			return nil, errors.New("archivo de registros MagicDNS ambiguo")
		}
	} else if inline := child(dns, "extra_records"); inline != nil {
		if inline.Decode(&p.document.Records) != nil {
			return nil, errors.New("registros MagicDNS estáticos no reconocidos")
		}
	}
	p.document.RecordsWritable = recordsWritable
	p.document.Revision = revision(config, records)
	return p, nil
}

func set(root *yaml.Node, path []string, value any) error {
	for _, key := range path[:len(path)-1] {
		next := child(root, key)
		if next == nil {
			next = &yaml.Node{Kind: yaml.MappingNode, Tag: "!!map"}
			root.Content = append(root.Content, &yaml.Node{Kind: yaml.ScalarNode, Tag: "!!str", Value: key}, next)
		}
		if next.Kind != yaml.MappingNode {
			return errors.New("apartado Headscale no editable")
		}
		root = next
	}
	key := path[len(path)-1]
	var replacement yaml.Node
	if e := replacement.Encode(value); e != nil {
		return errors.New("valor Headscale no serializable")
	}
	if previous := child(root, key); previous != nil {
		replacement.HeadComment = previous.HeadComment
		replacement.LineComment = previous.LineComment
		replacement.FootComment = previous.FootComment
		*previous = replacement
	} else {
		root.Content = append(root.Content, &yaml.Node{Kind: yaml.ScalarNode, Tag: "!!str", Value: key}, &replacement)
	}
	return nil
}

// prepare modifica exclusivamente las hojas admitidas. Los demás apartados,
// claves de cifrado y comentarios siguen perteneciendo al archivo Headscale.
func prepare(config, records []byte, writable bool, change Change) ([]byte, []byte, bool, error) {
	p, e := parse(config, records, writable)
	if e != nil {
		return nil, nil, false, e
	}
	if change.Revision == "" || change.Revision != p.document.Revision {
		return nil, nil, false, errors.New("la configuración cambió; vuelve a cargarla antes de guardar")
	}
	// Comparar valores tipados evita reescribir el YAML o reiniciar por una
	// diferencia de formato, como una lista vacía representada por null.
	same := func(a, b any) bool {
		left, e1 := yaml.Marshal(a)
		right, e2 := yaml.Marshal(b)
		return e1 == nil && e2 == nil && bytes.Equal(left, right)
	}
	if change.DNS != nil && same(*change.DNS, p.document.DNS) {
		change.DNS = nil
	}
	if change.OIDC != nil && p.document.OIDC != nil && same(*change.OIDC, *p.document.OIDC) {
		change.OIDC = nil
	}
	if change.Records != nil && same(*change.Records, p.document.Records) {
		change.Records = nil
	}
	if change.DNS == nil && change.OIDC == nil && change.Records == nil {
		return nil, nil, false, errors.New("no hay cambios Headscale")
	}
	root := p.tree.Content[0]
	patch := func(path []string, value any) error { return set(root, path, value) }
	if d := change.DNS; d != nil {
		if e = d.Validate(); e != nil {
			return nil, nil, false, e
		}
		server, e := url.Parse(scalar(root, "server_url"))
		if e != nil {
			return nil, nil, false, errors.New("URL del coordinador no reconocida")
		}
		if d.BaseDomain != "" && strings.EqualFold(d.BaseDomain, server.Hostname()) {
			return nil, nil, false, errors.New("el dominio MagicDNS debe ser distinto del dominio del coordinador")
		}
		for _, item := range []struct {
			key   string
			value any
		}{{"magic_dns", d.MagicDNS}, {"base_domain", d.BaseDomain}, {"override_local_dns", d.OverrideLocalDNS}, {"search_domains", d.SearchDomains}} {
			if e = patch([]string{"dns", item.key}, item.value); e != nil {
				return nil, nil, false, e
			}
		}
		if e = patch([]string{"dns", "nameservers", "global"}, d.Nameservers.Global); e != nil {
			return nil, nil, false, e
		}
		if e = patch([]string{"dns", "nameservers", "split"}, d.Nameservers.Split); e != nil {
			return nil, nil, false, e
		}
	}
	if r := change.OIDC; r != nil {
		if p.document.OIDC == nil {
			return nil, nil, false, errors.New("Headscale no tiene OIDC configurado")
		}
		if e = r.Validate(); e != nil {
			return nil, nil, false, e
		}
		for _, item := range []struct {
			key   string
			value any
		}{{"allowed_domains", r.AllowedDomains}, {"allowed_groups", r.AllowedGroups}, {"allowed_users", r.AllowedUsers}} {
			if e = patch([]string{"oidc", item.key}, item.value); e != nil {
				return nil, nil, false, e
			}
		}
	}
	output := config
	if change.DNS != nil || change.OIDC != nil {
		var b bytes.Buffer
		encoder := yaml.NewEncoder(&b)
		encoder.SetIndent(2)
		if encoder.Encode(&p.tree) != nil {
			return nil, nil, false, errors.New("no se pudo preparar el YAML Headscale")
		}
		output = b.Bytes()
	}
	if change.Records != nil {
		if !writable {
			return nil, nil, false, errors.New("los registros estáticos son de solo lectura; configura extra_records_path en el controlador local")
		}
		if e = ValidateRecords(*change.Records); e != nil {
			return nil, nil, false, e
		}
		records, e = json.MarshalIndent(*change.Records, "", "  ")
		if e != nil {
			return nil, nil, false, errors.New("no se pudieron preparar los registros MagicDNS")
		}
		records = append(records, '\n')
	}
	return output, records, !bytes.Equal(config, output), nil
}
