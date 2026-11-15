'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function setup(lastSync,results=[],candidates=[],download){
 const calls=[];
 const controls=new Map();
 const create=()=>({textContent:'',style:{},children:[],listeners:{},attributes:{},focus(){this.focused=true},setAttribute(k,v){this.attributes[k]=v},
  append(...items){this.children.push(...items)},replaceChildren(){this.children=[]},
  addEventListener(name,fn){this.listeners[name]=fn},closest(){return this}});
 const element=id=>{if(!controls.has(id))controls.set(id,create());return controls.get(id)};
 const document={getElementById:element,querySelector:element,createElement:create};
 const api=async (path,method,body)=>{calls.push({path,body});if(path==='pki/discover/download')return download?download():results;if(path==='pki/discover')return {candidates};return {platform:'android',peers:[{name:'prueba',endpoint:'https://prueba.test',fingerprint:'abc',last_sync:lastSync}]}};
 vm.runInNewContext(fs.readFileSync(__dirname+'/panel-pki.js','utf8'),{document,api,Date,Number,window:{tr:(text,params)=>text.replace(/\{(\w+)\}/g,(_,key)=>params[key])}});
 return {element,calls};
}
async function renderedPeerDate(lastSync){
 const {element}=setup(lastSync);
 element('[data-tab="pki"]').listeners.click();
 await new Promise(resolve=>setImmediate(resolve));
 return element('pki-peer-rows').children[0].children[2].textContent;
}
test('una verificación inexistente o inválida no se convierte en una fecha local',async()=>{
 for(const value of [null,undefined,'','0001-01-01T00:00:00Z','0001-01-01T00:00:00.000Z','fecha inválida']){
  assert.equal(await renderedPeerDate(value),'—');
 }
});
test('la fecha de una verificación real conserva el formato local',async()=>{
 const value='2026-11-15T10:00:00Z';
 assert.equal(await renderedPeerDate(value),new Date(value).toLocaleString());
});

test('la descarga no anuncia éxito si todas las CA fallan',async()=>{
 const {element}=setup(null,[{endpoint:'https://prueba.test',error:'HTTP 404'}]);
 await element('pki-download-discovered').listeners.click();
 assert.match(element('pki-message').textContent,/0 obtenidas, 1 con error/);
 assert.equal(element('pki-message').style.color,'#fda4af');
 assert.equal(element('pki-download-discovered').disabled,false);
 assert.equal(element('pki-discovery-message').focused,true);
});
test('la descarga distingue resultados parciales y conserva la aprobación existente',async()=>{
 const {element}=setup(null,[{endpoint:'https://prueba.test',anchor:{approved:true,fingerprint:'abc'}},{endpoint:'https://apagado.test',error:'timeout'}]);
 await element('pki-download-discovered').listeners.click();
 assert.match(element('pki-message').textContent,/1 obtenidas, 1 con error/);
 assert.match(allText(element('pki-discovery').children[0]),/CA ya aprobada/);
});

function allText(node){return [node.textContent,...node.children.map(allText)].join(' ')}
test('los errores largos quedan en detalles y el estado tiene texto y color',async()=>{
 const errors=['connection was refused','context deadline exceeded','HTTP 404','x509: certificate expired'];
 const {element}=setup(null,errors.map((error,i)=>({endpoint:'https://nodo'+i+'.test',error})));
 await element('pki-download-discovered').listeners.click();
 const rows=element('pki-discovery').children;
 assert.match(allText(rows[0]),/Puerto cerrado/);assert.match(allText(rows[1]),/Sin respuesta a tiempo/);
 assert.match(allText(rows[2]),/CA no publicada/);assert.match(allText(rows[3]),/Error de certificado HTTPS/);
 for(const row of rows){assert.equal(row.className,'pki-discovery-entry is-warning');assert.equal(row.children[2].children[0].textContent,'Detalles técnicos');assert.equal(row.children[2].children[1].tabIndex,0)}
});
test('un error remoto se muestra como texto sin interpretar HTML',async()=>{
 const error='<img src=x onerror=alert(1)>';
 const {element}=setup(null,[{endpoint:'https://nodo.test',error}]);
 await element('pki-download-discovered').listeners.click();
 assert.equal(element('pki-discovery').children[0].children[2].children[1].textContent,error);
});
test('solo identifica un Gateway registrado o con CA, no deduce ausencia por un timeout',async()=>{
 const {element}=setup(null,[{endpoint:'https://prueba.test',error:'timeout'},{endpoint:'https://simple.test',error:'timeout'},{endpoint:'https://nuevo.test',anchor:{fingerprint:'def',approved:false}}]);
 element('[data-tab="pki"]').listeners.click();await new Promise(resolve=>setImmediate(resolve));
 await element('pki-download-discovered').listeners.click();
 const rows=element('pki-discovery').children;
 assert.match(allText(rows[0]),/Gateway registrado/);assert.match(allText(rows[1]),/Gateway sin confirmar/);assert.match(allText(rows[2]),/Gateway con CA disponible/);
});
test('la descarga individual usa el origen del candidato, no inicia un lote',async()=>{
 const {element,calls}=setup(null,[],[{endpoint:'https://prueba.test',name:'prueba',targets:[]}]);
 await element('pki-lan-discover').listeners.click();
 const row=element('pki-discovery').children[0];row.children.at(-1).listeners.click();
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(calls.filter(call=>call.path==='pki/discover/download')[0].body.endpoint,'https://prueba.test');
});
test('no solapa búsquedas y descargas al pulsar repetidamente',async()=>{
 let finish;const wait=new Promise(resolve=>finish=resolve);
 const {element,calls}=setup(null,[],[],()=>wait);
 const first=element('pki-download-discovered').listeners.click();
 await element('pki-download-discovered').listeners.click();await element('pki-lan-discover').listeners.click();
 assert.equal(calls.length,1);assert.equal(element('pki-lan-discover').disabled,true);
 finish([]);await first;assert.equal(element('pki-lan-discover').disabled,false);
});
