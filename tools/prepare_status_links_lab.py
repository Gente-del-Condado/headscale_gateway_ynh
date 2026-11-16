#!/usr/bin/env python3
"""Prepara una página sin red ni credenciales usando el renderizador real del panel."""
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]

def prepare(output):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('El laboratorio necesita una carpeta vacía')
    output.mkdir(parents=True, exist_ok=True)
    source = (ROOT / 'src/internal/admin/panel.js').read_text()
    renderer = source[source.index('// El estado viene'):source.index('function button(')]
    shutil.copy2(ROOT / 'src/internal/admin/panel.css', output / 'panel.css')
    page = '''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Laboratorio de enlaces del Gateway</title><link rel="stylesheet" href="panel.css"><main><h1>Laboratorio: datos ficticios</h1><p>No conecta con Headscale, DNS ni certificados reales.</p><div class="card"><h2>Estado</h2><dl id="status"></dl></div><div hidden><span id="about-version"></span><div id="setup-banner"></div><p id="setup-message"></p><button id="reload">Recargar</button></div><pre id="lab-result">PENDIENTE</pre></main><script>
const el=id=>document.getElementById(id),tr=value=>value;
'''+renderer+r'''
try {
 const data={node:'laboratorio',domain:'gateway-lab.example.test',headscale_url:'http://127.0.0.1:9/headscale',admin_domain_url:'https://admin.gateway-lab.example.test/admin/',admin_oidc_callback:'https://admin.gateway-lab.example.test/admin/auth/oidc/callback'};
 renderStatus(data);
 const check=(ok,message)=>{if(!ok)throw Error(message)};
 check(el('status').firstElementChild.textContent==='Dominio principal','Orden del dominio');
 const links=[...el('status').querySelectorAll('a')];
 check(links.length===4,'Faltan enlaces web');
 check(links[0].href==='https://gateway-lab.example.test/','Dominio principal incorrecto');
 check(links.every(a=>a.target==='_blank'&&a.rel==='noopener noreferrer'),'Navegación fuera del panel');
 links[0].focus();const before=scrollY;renderStatus(data);
 check(document.activeElement.dataset.statusKey==='domain'&&scrollY===before,'Foco perdido al refrescar');
 check(!statusLinkURL('domain','evil.test/path')&&!statusLinkURL('url','javascript:alert(1)')&&!statusLinkURL('url','https://user:secret@example.test/'),'URL insegura aceptada');
 check(document.documentElement.scrollWidth<=innerWidth+2,'Desbordamiento horizontal');
 el('lab-result').textContent='STATUS_LINKS_BROWSER_OK: dominio principal, cuatro URL, HTTPS/HTTP, foco, navegación y rechazo de URL inseguras';
} catch(error) { el('lab-result').textContent='STATUS_LINKS_BROWSER_FAILED: '+error.message; }
// En Windows Edge puede cerrar el lanzador sin entregar stdout. El laboratorio
// opcional recibe un resultado mínimo en un puerto loopback aleatorio; no envía
// HTML, credenciales ni datos de una instalación.
const callback=new URLSearchParams(location.hash.slice(1)).get('report');
if(callback&&/^http:\/\/127\.0\.0\.1:[0-9]+\/[a-f0-9-]+\/result$/.test(callback)){
 const reportImage=new Image();reportImage.src=callback+'?result='+encodeURIComponent(el('lab-result').textContent);window.__labReportImage=reportImage;
}
</script></html>'''
    (output / 'index.html').write_text(page)
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    print(prepare(parser.parse_args().output))
