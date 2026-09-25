const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/equipamentos.js'), 'utf8');
function element() {
  return {listeners:{}, files:[], value:'', textContent:'', className:'', children:[], disabled:false,
    addEventListener(k, fn){this.listeners[k]=fn;}, append(...children){this.children.push(...children);},
    replaceChildren(...children){this.children=children;}, focus(){}, setAttribute(){}, removeAttribute(){}, click(){this.clicked=true;}, remove(){}};
}
function setup(responder) {
  const elements = {};
  const get = id => elements[id] ||= element();
  get('planilha').files = [{name:'controle.xlsx',size:100}];
  const context = vm.createContext({document:{body:element(), createTextNode:text=>({textContent:text}),querySelector:s=>get(s.slice(1)),getElementById:get,createElement:element,createDocumentFragment:element}, location:{protocol:'http:'}, URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}}, window:{confirm:()=>false},
    FormData:class{append(){}}, Error, fetch: async (url, options) => url === '/api/equipamentos' ? {ok:true,status:200,json:async()=>({registros:[]})} : responder(url, options)});
  vm.runInContext(source,context);
  return {elements,get,context,preview:()=>vm.runInContext('visualizarExcel()', context)};
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

test('exportação gera download e mantém link manual disponível',async()=>{
  const app=setup(async()=>({ok:true,headers:{get:key=>key==='Content-Type'?'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':'1'},blob:async()=>({})}));
  const button=app.get('exportar-excel');
  await button.listeners.click({preventDefault(){},currentTarget:button});
  const link=app.get('mensagem-inventario').children.at(-1);
  assert.equal(link.href,'blob:test');
  assert.equal(link.download,'inventario-equipamentos.xlsx');
  assert.equal(button.textContent,'Exportar Excel');
});

test('exportação rejeita HTML no lugar de arquivo',async()=>{
  const app=setup(async()=>({ok:true,headers:{get:()=> 'text/html'}}));
  const button=app.get('exportar-excel');
  await button.listeners.click({preventDefault(){},currentTarget:button});
  assert.match(app.get('mensagem-inventario').textContent,/página em vez do Excel/);
});

test('cancelar confirmação não envia exclusão',async()=>{
  const app=setup(async()=>{throw new Error('Não deveria enviar');});
  await new Promise(resolve=>setImmediate(resolve));
  vm.runInContext('renderizarInventario({registros:[{ativo:"PC",numero_serie:"AB001"}]})',app.context);
  const row=app.get('linhas-inventario').children[0].children[0];
  const button=row.children.at(-1).children[0];
  assert.match(button.textContent,/Excluir/);
  await button.listeners.click();
  assert.equal(button.disabled,false);
});
test('leitura concluída usa primeira aba e habilita importação sem seletor',async()=>{
  const app=setup(async(url,options)=>{
    assert.equal(url,'/api/excel');assert.equal(options.method,'POST');
    return {status:200,ok:true,json:async()=>({abas:['Inventário','Filial'],aba:'Inventário',quantidade:4})};
  });
  await app.preview();
  assert.equal(app.elements['aba-excel'],undefined);
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
