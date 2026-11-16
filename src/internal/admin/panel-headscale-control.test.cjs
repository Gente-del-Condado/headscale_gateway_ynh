'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {splitRules, validDomain, validRecord} = require('./panel-headscale-control.js');
test('prepara Split DNS sin perder parámetros de las URL ni repetir zonas', () => {
  const value = splitRules('intra.example.test = 100.64.0.2, 2001:db8::53\nexternal.example.test = https://dns.example.test/query?profile=lab');
  assert.deepEqual(value['intra.example.test'], ['100.64.0.2','2001:db8::53']);
  assert.equal(value['external.example.test'][0], 'https://dns.example.test/query?profile=lab');
  assert.equal(Object.getPrototypeOf(value), null);
  assert.throws(() => splitRules('intra.example.test = '));
  assert.throws(() => splitRules('intra.example.test = 1.1.1.1\nintra.example.test = 9.9.9.9'));
});
test('los registros usan nombres completos y el tipo de dirección seleccionado', () => {
  assert.equal(validRecord({name:'fotos.pc1.example.test',type:'A',value:'100.64.0.7'}), true);
  assert.equal(validRecord({name:'fotos.pc1.example.test',type:'AAAA',value:'fd7a:115c:a1e0::7'}), true);
  for (const value of ['100.64.0.999','127.1','01.2.3.4','<script>']) assert.equal(validRecord({name:'fotos.example.test',type:'A',value}), false);
  assert.equal(validRecord({name:'*.example.test',type:'A',value:'100.64.0.7'}), false);
  assert.equal(validDomain('example.test\nclient_secret: value'), false);
});
