'use strict';
// El navegador prepara datos tipados. Solo el controlador local autorizado
// valida y aplica el archivo Headscale; nunca se descarga su configuración completa.
(() => {
  const tr = value => typeof window !== 'undefined' && typeof window.tr === 'function' ? window.tr(value) : value;
  const lines = value => String(value || '').split(/\r?\n/).map(v => v.trim()).filter(Boolean);
  function splitRules(text) {
    const result = Object.create(null);
    for (const line of lines(text)) {
      const index = line.indexOf('=');
      if (index < 1) throw Error(tr('Split DNS: usa una regla por línea con el formato zona = resolutor, resolutor.'));
      const domain = line.slice(0, index).trim().toLowerCase();
      const values = line.slice(index + 1).split(',').map(v => v.trim()).filter(Boolean);
      if (!values.length || Object.prototype.hasOwnProperty.call(result, domain)) throw Error(tr('Split DNS: la zona está repetida o no tiene resolutores.'));
      result[domain] = values;
    }
    return result;
  }
  const validDomain = value => value.length <= 253 && value.includes('.') && value.split('.').every(label => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(label));
  function validRecord(record) {
    if (!validDomain(record.name)) return false;
    if (record.type === 'A') return record.value.split('.').length === 4 && record.value.split('.').every(v => /^(0|[1-9][0-9]{0,2})$/.test(v) && Number(v) <= 255);
    if (record.type !== 'AAAA' || !/^[0-9a-fA-F:.]+$/.test(record.value)) return false;
    try { return new URL('http://[' + record.value + ']/').hostname.startsWith('['); } catch { return false; }
  }
  if (typeof module === 'object' && module.exports) { module.exports = {lines, splitRules, validDomain, validRecord}; return; }
  const $ = id => document.getElementById(id);
  const dirty = new Set(), conflicts = new Set(), bases = {};
  let documentState = null, info = null, agentState = null, records = [], pending = null, busy = false, loading = false, generation = 0, agentTimer = null;
  const storageKey = 'hgw.headscale.operation';
  const status = (text, bad = false) => { $('hsc-status').textContent = text; $('hsc-status').className = bad ? 'error' : 'field-help'; };
  const showError = error => { if (error.stale) return; status(error.message, true); $('hsc-status').focus(); };
  const clone = value => JSON.parse(JSON.stringify(value));
  const sectionValue = (doc, section) => section === 'records' ? doc.records : section === 'oidc' ? doc.oidc : doc.dns;
  const canWrite = () => currentRole === 'admin' && info?.can_write === true && !busy && !loading;
  function resetPreview() { pending = null; $('hsc-preview-box').hidden = true; $('hsc-apply').disabled = true; }
  function edited(section) { dirty.add(section); resetPreview(); }
  function locks() {
    $('hsc-reload').disabled = busy || loading;
    $('hsc-dns-fields').disabled = !canWrite();
    $('hsc-oidc-fields').disabled = !canWrite() || !documentState?.oidc;
    $('hsc-record-fields').disabled = !canWrite() || !documentState?.records_writable;
    document.querySelectorAll('[data-hsc-write]').forEach(button => { button.disabled = !canWrite(); });
    $('hsc-oidc-review').disabled = !canWrite() || !documentState?.oidc;
    $('hsc-record-review').disabled = !canWrite() || !documentState?.records_writable;
    $('hsc-agent-sync').disabled = busy || loading || info?.can_sync_agent !== true || !agentState?.enabled || agentState?.running === true;
    $('hsc-apply').disabled = !canWrite() || !pending;
  }
  function renderRecords() {
    const body = $('hsc-records-rows'); body.replaceChildren();
    records.forEach((record, index) => {
      const row = document.createElement('tr');
      for (const key of ['name', 'type', 'value']) { const cell = document.createElement('td'); cell.textContent = record[key] || ''; row.append(cell); }
      const cell = document.createElement('td'), button = document.createElement('button');
      button.type = 'button'; button.className = 'secondary'; button.textContent = tr('Retirar del borrador');
      button.disabled = !canWrite() || !documentState?.records_writable;
      button.addEventListener('click', () => { if (!canWrite()) return; records.splice(index, 1); edited('records'); renderRecords(); });
      cell.append(button); row.append(cell); body.append(row);
    });
  }
  function fill(doc, force) {
    for (const section of ['dns', 'oidc', 'records']) {
      const value = sectionValue(doc, section), encoded = JSON.stringify(value);
      if (dirty.has(section) && !force) { if (encoded !== bases[section]) conflicts.add(section); continue; }
      bases[section] = encoded; conflicts.delete(section);
      if (section === 'dns') {
        $('hsc-magic').checked = !!doc.dns.magic_dns; $('hsc-domain').value = doc.dns.base_domain || ''; $('hsc-domain').required = !!doc.dns.magic_dns;
        $('hsc-override').checked = !!doc.dns.override_local_dns;
        $('hsc-global').value = (doc.dns.nameservers.global || []).join('\n');
        $('hsc-split').value = Object.entries(doc.dns.nameservers.split || {}).map(([domain, servers]) => domain + ' = ' + servers.join(', ')).join('\n');
        $('hsc-search').value = (doc.dns.search_domains || []).join('\n');
      } else if (section === 'oidc') {
        for (const field of ['domains', 'groups', 'users']) $('hsc-allowed-' + field).value = (doc.oidc?.['allowed_' + field] || []).join('\n');
      } else records = clone(doc.records || []);
    }
    documentState = doc;
    $('hsc-oidc-note').textContent = doc.oidc ? tr('Si configuras varios filtros, deben cumplirse todos. Una lista vacía desactiva ese filtro. No concede administración del Gateway ni revoca nodos o claves existentes.') : tr('Headscale no tiene un proveedor OIDC configurado. Se conserva su configuración actual; estas listas están desactivadas.');
    $('hsc-records-note').textContent = doc.records_writable ? tr('Archivo dinámico autorizado: los cambios de registros se aplican sin reiniciar Headscale.') : tr('Registros de solo lectura. El instalador del controlador debe autorizar un archivo extra_records_path para poder modificarlos.');
    renderRecords(); locks();
  }
  async function readDocument(force = false) {
    if (currentRole !== 'admin' || loading) return;
    const current = generation; loading = true; locks(); renderRecords();
    try {
      const nextInfo = await api('network/control/info');
      if (current !== generation || currentRole !== 'admin') return;
      info = nextInfo;
      if (info.mode === 'disabled') { $('hsc-editor').hidden = true; status(tr('Administración del coordinador desactivada. Configura el modo local o un Gateway controlador remoto.')); await readAgent(); return; }
      const doc = await api('network/control/document');
      if (current !== generation || currentRole !== 'admin') return;
      if (force) dirty.clear();
      fill(doc, force); $('hsc-editor').hidden = false;
      const access = info.can_write ? tr('Administración autorizada') : tr('Delegación de solo lectura');
      status(access + ' · ' + doc.instance + (conflicts.size ? ' · ' + tr('Hay borradores que entran en conflicto con cambios externos; vuelve a leer el estado antes de aplicarlos.') : ''));
      resetPreview(); await readAgent();
    } catch (error) {
      if (current !== generation || currentRole !== 'admin') return;
      info = null; throw error;
    } finally {
      if (current === generation) { loading = false; locks(); renderRecords(); }
    }
  }
  async function review(section, value) {
    if (!canWrite() || !documentState) throw Error(tr('No hay permiso de escritura en el controlador.'));
    if (conflicts.has(section)) throw Error(tr('Estos ajustes cambiaron mientras editabas. Conserva tu borrador y vuelve a leer el estado antes de aplicarlo.'));
    const change = {revision: documentState.revision, [section]: clone(value)};
    const current = generation;
    const preview = await api('network/control/preview', 'POST', change);
    if (current !== generation || currentRole !== 'admin') return;
    pending = {section, change};
    $('hsc-preview').textContent = tr('Configuración actual:') + '\n' + JSON.stringify(sectionValue(documentState, section), null, 2) + '\n\n' + tr('Propuesta:') + '\n' + JSON.stringify(value, null, 2);
    $('hsc-preview-impact').textContent = preview.restart_required ? tr('Requiere reiniciar Headscale. El controlador comprueba el candidato aislado y restaura la configuración anterior si falla. El Gateway y sus servicios continúan ejecutándose.') : tr('Solo cambia el archivo dinámico de registros; no requiere reiniciar Headscale.');
    $('hsc-preview-box').hidden = false; locks(); $('hsc-apply').focus();
  }
  const operationLabels = {queued:'Cambio en cola',validating:'Validando una copia aislada',applying:'Aplicando los archivos autorizados',restarting:'Reiniciando Headscale',checking:'Comprobando la recuperación de Headscale',rolling_back:'Restaurando la configuración anterior',completed:'Cambio aplicado y comprobado',failed:'Cambio rechazado',rolled_back:'Configuración anterior restaurada',recovery_required:'Se requiere recuperación local; se conserva el diario'};
  async function follow(id) {
    const current = generation;
    let last = '', connectionWarning = false; const deadline = Date.now() + 300000;
    $('hsc-operation-box').hidden = false; $('hsc-operation-id').textContent = tr('Identificador de operación:') + ' ' + id;
    while (Date.now() < deadline) {
      if (currentRole !== 'admin' || current !== generation) throw Object.assign(Error(tr('La sesión administrativa terminó.')), {terminal:true,stale:current !== generation});
      try {
        const value = await api('network/control/operations/' + encodeURIComponent(id));
        if (current !== generation || currentRole !== 'admin') throw Object.assign(Error(tr('La sesión administrativa terminó.')), {terminal:true,stale:true});
        connectionWarning = false;
        if (value.state !== last) { const item = document.createElement('li'); item.textContent = tr(operationLabels[value.state] || 'Estado del controlador no reconocido'); item.className = ['failed','recovery_required'].includes(value.state) ? 'error' : ''; $('hsc-operation-log').append(item); last = value.state; }
        if (value.finished_at) {
          try { sessionStorage.removeItem(storageKey); } catch {}
          if (value.state !== 'completed') throw Object.assign(Error(value.error || tr('El cambio no se completó.')), {terminal:true});
          return;
        }
      } catch (error) {
        if (error.status === 404) { try { sessionStorage.removeItem(storageKey); } catch {} throw Error(tr('El controlador ya no conserva esa operación. Lee su estado actual antes de intentar otro cambio.')); }
        if (error.terminal || [401,403].includes(error.status)) throw error;
        if (!connectionWarning) { const item = document.createElement('li'); item.textContent = tr('Esperando conexión con el controlador. Solo se consulta el estado; el cambio no se vuelve a enviar.'); $('hsc-operation-log').append(item); connectionWarning = true; }
      }
      await new Promise(resolve => setTimeout(resolve, 1200));
    }
    throw Error(tr('No se pudo confirmar el resultado. Conserva el identificador y lee el estado del controlador antes de intentar otro cambio.'));
  }
  async function applyReviewed() {
    if (!pending || !canWrite()) return;
    const selected = pending, current = generation; busy = true; locks(); renderRecords(); status(tr('Aplicando los cambios revisados; esperando la confirmación del controlador.')); $('hsc-operation-log').replaceChildren();
    try {
      const operation = await api('network/control/apply', 'POST', selected.change);
      try { sessionStorage.setItem(storageKey, operation.id); } catch {}
      await follow(operation.id); if (current !== generation) return; dirty.delete(selected.section); resetPreview();
      await readDocument(); if (current !== generation) return; status(tr('Cambios aplicados y estado de Headscale comprobado.'));
    } finally { if (current === generation) { busy = false; locks(); renderRecords(); } }
  }
  const date = value => value && !Number.isNaN(new Date(value).valueOf()) ? new Date(value).toLocaleString(window.gatewayLanguage?.() || 'es') : tr('No disponible');
  const observerVisible = () => currentRole === 'admin' && !document.hidden && !document.querySelector('[data-page="headscale-control"]').hidden;
  function scheduleAgent(delay) {
    clearTimeout(agentTimer); agentTimer = null;
    if (!observerVisible()) return;
    agentTimer = setTimeout(async () => {
      agentTimer = null;
      if (!observerVisible()) return;
      if (busy) { scheduleAgent(1500); return; }
      try { await readAgent(); } catch {
        $('hsc-agent-status').textContent = tr('No se pudo actualizar el observador. Se conservan los últimos datos con su fecha.');
        scheduleAgent(30000);
      }
    }, delay);
  }
  document.addEventListener('visibilitychange', () => scheduleAgent(document.hidden ? 30000 : 500));
  async function readAgent() {
    const current = generation;
    const value = await api('network/control/agent'), body = $('hsc-agent-rows');
    if (current !== generation || currentRole !== 'admin') return;
    body.replaceChildren();
    agentState = value;
    let observerStatus = (!value.enabled ? tr('Observador desactivado') : value.running ? tr('Sincronización en curso') : value.error || (value.partial ? tr('Sincronización parcial; algunos nodos no son visibles para tsnet') : tr('Observador disponible'))) + ' · ' + tr('Última sincronización:') + ' ' + date(value.synced_at) + (value.stale ? ' · ' + tr('Datos antiguos') : '');
    $('hsc-agent-sync').disabled = busy || loading || info?.can_sync_agent !== true || !value.enabled || value.running;
    for (const node of value.nodes || []) {
      const row = document.createElement('tr'), m = node.metadata || {};
      const system = [m.os,m.os_version,m.distro,m.distro_version].filter(Boolean).join(' ') || tr('No disponible');
      for (const text of [node.name,node.online ? tr('Conectado') : tr('Desconectado'),system,m.client_version || tr('No disponible'),date(node.observed_at) + (!node.available ? ' · ' + tr('Dato anterior o no visible') : '')]) { const cell = document.createElement('td'); cell.textContent = text; row.append(cell); }
      body.append(row);
    }
    if (value.omitted_nodes) observerStatus += ' · ' + tr('Nodos fuera del límite de observación:') + ' ' + value.omitted_nodes;
    if ($('hsc-agent-status').textContent !== observerStatus) $('hsc-agent-status').textContent = observerStatus;
    scheduleAgent(value.running ? 1200 : 30000);
  }
  for (const [id, section] of [['hsc-dns-form','dns'],['hsc-oidc-form','oidc']]) $(id).addEventListener('input', () => edited(section));
  document.querySelectorAll('#hsc-editor input, #hsc-editor textarea').forEach(input => {
    input.addEventListener('invalid', () => input.setAttribute('aria-invalid','true'));
    input.addEventListener('input', () => { input.setCustomValidity(''); input.setAttribute('aria-invalid','false'); });
  });
  $('hsc-magic').addEventListener('change', () => { $('hsc-domain').required = $('hsc-magic').checked; });
  $('hsc-dns-form').addEventListener('submit', event => { event.preventDefault(); run(async () => {
    const domain = $('hsc-domain').value.trim().toLowerCase();
    if (domain && !validDomain(domain)) { $('hsc-domain').setCustomValidity(tr('Introduce un dominio completo válido, sin punto final.')); $('hsc-domain').reportValidity(); return; }
    try { await review('dns',{magic_dns:$('hsc-magic').checked,base_domain:domain,override_local_dns:$('hsc-override').checked,nameservers:{global:lines($('hsc-global').value),split:splitRules($('hsc-split').value)},search_domains:lines($('hsc-search').value).map(v => v.toLowerCase())}); } catch (e) { showError(e); }
  }); });
  $('hsc-oidc-form').addEventListener('submit', event => { event.preventDefault(); run(async () => { try { await review('oidc',{allowed_domains:lines($('hsc-allowed-domains').value).map(v => v.toLowerCase()),allowed_groups:lines($('hsc-allowed-groups').value),allowed_users:lines($('hsc-allowed-users').value)}); } catch (e) { showError(e); } }); });
  $('hsc-record-form').addEventListener('submit', event => { event.preventDefault(); if (!canWrite() || !documentState?.records_writable) return;
    const record = {name:$('hsc-record-name').value.trim().toLowerCase(),type:new FormData(event.currentTarget).get('record_type'),value:$('hsc-record-value').value.trim()};
    if (!validRecord(record)) { $('hsc-record-value').setCustomValidity(tr('Comprueba el nombre completo y la dirección del tipo IPv4 o IPv6 seleccionado.')); $('hsc-record-value').reportValidity(); return; }
    if (records.some(v => v.name === record.name && v.type === record.type && v.value === record.value)) { showError(Error(tr('Ese registro ya está en el borrador.'))); return; }
    records.push(record); edited('records'); event.currentTarget.reset(); renderRecords();
  });
  $('hsc-record-review').addEventListener('click', () => run(async () => { try { await review('records',records); } catch (e) { showError(e); } }));
  $('hsc-apply').addEventListener('click', () => run(async () => { try { await applyReviewed(); } catch (e) { showError(e); } }));
  $('hsc-preview-cancel').addEventListener('click', resetPreview);
  $('hsc-reload').addEventListener('click', () => run(async () => { if (dirty.size && !confirm(tr('¿Descartar los borradores y leer la configuración actual?'))) return; try { await readDocument(true); } catch (e) { showError(e); } }));
  $('hsc-settings').addEventListener('click', () => document.querySelector('[data-tab="settings"]').click());
  $('hsc-agent-refresh').addEventListener('click', () => run(readAgent));
  $('hsc-agent-sync').addEventListener('click', () => run(async () => { if (busy || info?.can_sync_agent !== true) return; await api('network/control/agent/sync','POST',{}); await readAgent(); }));
  window.refreshHeadscaleControl = async () => {
    if (dirty.size || busy || loading) return;
    const current = generation;
    try {
      let id = null; try { id = sessionStorage.getItem(storageKey); } catch {}
      if (id) { busy = true; locks(); await follow(id); if (current !== generation) return; busy = false; }
      await readDocument();
    } catch (error) {
      if (current === generation) { busy = false; locks(); showError(error); }
    }
  };
  window.clearHeadscaleControl = () => { generation++; busy = false; loading = false; clearTimeout(agentTimer); agentTimer = null;  for(const id of ['hsc-dns-form','hsc-oidc-form','hsc-record-form'])$(id).reset(); $('hsc-preview').textContent=''; $('hsc-operation-log').replaceChildren(); $('hsc-operation-id').textContent=''; documentState = null; info = null; records = []; pending = null; dirty.clear(); conflicts.clear(); $('hsc-editor').hidden = true; $('hsc-records-rows').replaceChildren(); $('hsc-agent-rows').replaceChildren(); resetPreview(); locks(); };
})();
