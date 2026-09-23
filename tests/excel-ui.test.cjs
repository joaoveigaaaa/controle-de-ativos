const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/equipamentos.js'), 'utf8');
function element() {
  return {listeners:{}, files:[], value:'', textContent:'', className:'', children:[], disabled:false,
    addEventListener(k, fn){this.listeners[k]=fn;}, append(...children){this.children.push(...children);},
    replaceChildren(...children){this.children=children;}, focus(){}};
}
function setup(responder) {
  const elements = {};
  const get = id => elements[id] ||= element();
  get('planilha').files = [{name:'controle.xlsx',size:100}];
  const context = vm.createContext({document:{querySelector:s=>get(s.slice(1)),getElementById:get,createElement:element,createDocumentFragment:element}, location:{protocol:'http:'},
    FormData:class{append(){}}, Error, fetch: async (url, options) => url === '/api/equipamentos' ? {ok:true,status:200,json:async()=>({registros:[]})} : responder(url, options)});
  vm.runInContext(source,context);
  return {elements,get,preview:()=>vm.runInContext('visualizarExcel()', context)};
}
test('HTTP 405 permanece visível e importação fica bloqueada', async()=>{
  const app=setup(async()=>({status:405,ok:false,json:async()=>{throw new Error('HTML response');}}));
  await app.preview();
  const message=app.get('mensagem-excel').textContent;
  assert.match(message,/HTTP 405/);assert.match(message,/iniciar.bat/);
  assert.equal(app.get('botao-importar').disabled,true);
  await app.get('botao-importar').listeners.click();
  assert.equal(app.get('mensagem-excel').textContent,message);
});
test('leitura concluída preenche abas e habilita importação',async()=>{
  const app=setup(async(url,options)=>{
    assert.equal(url,'/api/excel');assert.equal(options.method,'POST');
    return {status:200,ok:true,json:async()=>({abas:['Inventário','Filial'],aba:'Inventário',quantidade:4})};
  });
  await app.preview();
  assert.equal(app.get('aba-excel').children.length,2);
  assert.equal(app.get('aba-excel').value,'Inventário');
  assert.equal(app.get('botao-importar').disabled,false);
  assert.match(app.get('resumo-excel').textContent,/4 linha/);
});
test('erro de validação é preservado e permite selecionar outro arquivo',async()=>{
  let valid=false;
  const app=setup(async()=>({status:valid?200:400,ok:valid,json:async()=>valid?{abas:['Dados'],aba:'Dados',quantidade:1}:{erro:'A primeira linha deve conter Ativo e Número de série.'}}));
  await app.preview();assert.match(app.get('mensagem-excel').textContent,/primeira linha/);
  assert.equal(app.get('botao-importar').disabled,true);
  valid=true;await app.preview();assert.equal(app.get('botao-importar').disabled,false);
});
