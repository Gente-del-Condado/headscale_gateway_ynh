'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function controls(){
 const items=new Map();
 const element=id=>{if(!items.has(id))items.set(id,{value:'',listeners:{},textContent:'',hidden:false,focus(){this.focused=true},addEventListener(k,v){this.listeners[k]=v}});return items.get(id)};
 return {element,document:{getElementById:element,querySelector:element,createElement(){return {addEventListener(){}}}}};
}
test('una retirada confirmada conserva el aviso DNS y lo anuncia como advertencia',async()=>{
 const {element,document}=controls();const notices=[];
 const context=vm.createContext({document,window:{tr:x=>x},api:async()=>({dns_cleanup:{status:'warning',deleted:1,message:'DNS pendiente: faltan permisos'}}),currentRole:'admin',setInterval:()=>0,notice:(...args)=>notices.push(args),run:fn=>fn()});
 const code=fs.readFileSync(__dirname+'/panel-headscale.js','utf8');vm.runInContext(code.slice(0,code.indexOf('const hsRow')),context);
 const result=await vm.runInContext("headscaleAction({action:'node.delete',id:'7'},'Nodo eliminado')",context);
 assert.equal(result.dns_cleanup.deleted,1);assert.match(element('headscale-node-action-status').textContent,/Nodo eliminado.*DNS pendiente.*1/);
 assert.equal(element('headscale-node-action-status').className,'error');assert.equal(element('headscale-node-action-status').focused,true);assert.equal(notices[0][1],true);
});
test('propone el nombre una vez y respeta lo que el usuario está escribiendo',()=>{
 const {element,document}=controls();const context=vm.createContext({document,el:element,run:fn=>fn()});
 const source=fs.readFileSync(__dirname+'/panel.js','utf8');vm.runInContext(source.slice(source.indexOf('// La confirmación es local')),context);
 vm.runInContext("renderInitialNodeName({'headscale.node_name_confirmed':'false','headscale.node_name':'mi-pc'})",context);
 assert.equal(element('initial-node-value').value,'mi-pc');assert.equal(element('initial-node-value').focused,true);
 element('initial-node-value').value='mi-nombre';
 vm.runInContext("renderInitialNodeName({'headscale.node_name_confirmed':'false','headscale.node_name':'mi-pc'})",context);
 assert.equal(element('initial-node-value').value,'mi-nombre');
 vm.runInContext("renderInitialNodeName({'headscale.node_name_confirmed':'true'})",context);
 assert.equal(element('initial-node-name').hidden,true);
});
