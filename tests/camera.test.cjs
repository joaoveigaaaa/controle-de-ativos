const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/live-scanner.js'), 'utf8');
function setup(devices = [{id:'webcam', label:'Webcam integrada'}], failure) {
  const elements = {};
  for (const id of ['iniciar-camera','parar-camera','camera-status','selecionar-camera','serie-consulta']) {
    elements[id] = {value:'', disabled:false, listeners:{}, textContent:'', addEventListener(k, fn){this.listeners[k]=fn;}, replaceChildren(){}, append(){}};
  }
  const state = {started:0, stopped:0, consulted:[]};
  class Scanner {
    static async getCameras(){if(failure) throw failure; return devices;}
    async start(id, config, success){state.started++;state.id=id;state.success=success;}
    async stop(){state.stopped++;}
  }
  vm.runInNewContext(source, {document:{querySelector:s=>elements[s.slice(1)],createElement:()=>({}),addEventListener(){}}, navigator:{mediaDevices:{getUserMedia(){}}}, Html5Qrcode:Scanner, consultarSerie:async s=>state.consulted.push(s)});
  return {elements,state,start:()=>elements['iniciar-camera'].listeners.click(),stop:()=>elements['parar-camera'].listeners.click()};
}
test('clique abre a webcam disponível e a leitura consulta uma única vez', async()=>{
  const app=setup(); await app.start();
  assert.equal(app.state.started,1); assert.equal(app.state.id,'webcam');
  assert.equal(app.elements['parar-camera'].disabled,false);
  app.state.success('000123'); app.state.success('000123');
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(app.state.consulted,['000123']); assert.equal(app.state.stopped,1);
  assert.equal(app.elements['serie-consulta'].value,'000123');
  assert.equal(app.elements['iniciar-camera'].disabled,false);
  await app.start(); assert.equal(app.state.started,2);
});
test('nenhuma câmera ou permissão negada permite tentar novamente',async()=>{
  for(const [devices,error,message] of [[[],null,/Nenhuma câmera/],[[],new Error('NotAllowedError'),/Permissão de câmera negada/]]){
    const app=setup(devices,error); await app.start();
    assert.match(app.elements['camera-status'].textContent,message);
    assert.equal(app.elements['iniciar-camera'].disabled,false);
    assert.equal(app.state.started,0);
  }
});
test('parar libera a câmera e impede consultas duplicadas',async()=>{
  const app=setup();await app.start();app.stop();await new Promise(resolve=>setImmediate(resolve));
  assert.equal(app.state.stopped,1); assert.equal(app.elements['selecionar-camera'].disabled,false);
});
