'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function fixture(){
 let document;
 class Element {
  constructor(tag){this.tagName=tag;this.children=[];this.dataset={};this._text='';}
  set textContent(value){this._text=String(value);this.children=[];}
  get textContent(){return this._text+this.children.map(n=>n.textContent).join('');}
  append(...nodes){this.children.push(...nodes);}
  contains(node){return this===node || this.children.some(n=>n.contains(node));}
  replaceChildren(){if(this.contains(document.activeElement))document.activeElement=document.body;this.children=[];}
  querySelectorAll(){return this.children.flatMap(n=>[...(n.tagName==='a'?[n]:[]),...n.querySelectorAll()]);}
  focus(options){document.activeElement=this;this.focusOptions=options;}
 }
 const elements=new Map();const el=id=>{if(!elements.has(id))elements.set(id,new Element('div'));return elements.get(id);};
 document={createElement:tag=>new Element(tag),body:new Element('body')};document.activeElement=document.body;
 const context=vm.createContext({URL,document,el,tr:x=>x});
 const source=fs.readFileSync(__dirname+'/panel.js','utf8');
 vm.runInContext(source.slice(source.indexOf('// El estado viene'),source.indexOf('function button(')),context);
 return {context,document,el,render:data=>context.renderStatus(data)};
}
test('dominio principal primero, con portal HTTPS y enlaces web nativos',()=>{
 const {render,el}=fixture();render({node:'mi-pc',headscale_url:'http://headscale.example.test:8080/',domain:'mi-pc.intra.example.test',admin_domain_url:'https://admin.mi-pc.intra.example.test/admin/'});
 const rows=el('status').children;
 assert.equal(rows[0].textContent,'Dominio principal');assert.equal(rows[1].children[0].href,'https://mi-pc.intra.example.test/');
 assert.match(rows[1].textContent,/administración tiene su propio enlace/);
 const links=el('status').querySelectorAll();assert.equal(links.length,3);
 for(const link of links){assert.equal(link.tagName,'a');assert.equal(link.target,'_blank');assert.equal(link.rel,'noopener noreferrer');assert.equal(link.textContent,link.href);}
});
test('rechaza esquemas ejecutables, credenciales, controles y dominios con rutas',()=>{
 const {context}=fixture();
 for(const value of ['javascript:alert(1)','data:text/html,hello','//example.test','https://user:password@example.test','https://example.test\n.evil.test','https://example.test/a b','<img src=x onerror=alert(1)>'])assert.equal(context.statusLinkURL('headscale_url',value),'',value);
 for(const value of ['example.test/admin','evil.test?x=1','user@evil.test','evil.test:444','evil.test\\path','javascript:alert(1)'])assert.equal(context.statusLinkURL('domain',value),'',value);
 assert.equal(context.statusLinkURL('admin_domain_url','https://[fd7a:115c:a1e0::1]:8443/admin/'),'https://[fd7a:115c:a1e0::1]:8443/admin/');
});
test('sin dominio confirmado muestra espera y conserva los valores inseguros como texto',()=>{
 const {render,el}=fixture();render({domain:'',headscale_url:'javascript:alert(1)'});
 assert.match(el('status').children[1].textContent,/Pendiente de conexión/);
 assert.equal(el('status').querySelectorAll().length,0);
 assert.match(el('status').textContent,/javascript:alert/);
});
test('el refresco conserva el foco del enlace sin tomarlo desde otro control',()=>{
 const {render,el,document}=fixture();const data={domain:'mi-pc.example.test'};render(data);
 const first=el('status').querySelectorAll()[0];first.focus();render(data);
 const next=el('status').querySelectorAll()[0];assert.equal(document.activeElement,next);assert.equal(next.focusOptions.preventScroll,true);
 document.activeElement=document.body;render(data);assert.equal(document.activeElement,document.body);
});
