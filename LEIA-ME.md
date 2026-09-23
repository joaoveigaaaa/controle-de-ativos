# Luxafit — equipamentos

O `templates/index.html` usa o HTML fornecido, preservando seu CSS, layout, cadastro, importação Excel e inventário. O envio de foto foi substituído pelo scanner com câmera ao vivo. Os scripts estão em arquivos separados para funcionar com as regras de segurança do servidor.

## Iniciar

Coloque seu `.env` existente ao lado de `app.py` e execute `iniciar.bat`. O navegador abrirá no endereço correto. Se a porta 5000 estiver ocupada por outra versão, o sistema escolhe a próxima porta livre e informa o endereço no terminal. O programa não cria nem sobrescreve seu `.env`. Mantenha o terminal aberto. A primeira instalação das dependências precisa de internet.

## MySQL existente

Conforme a última correção, os padrões são **tabela `numero_de_serie`, coluna de série `ativos`**. Podem ser ajustados no `.env` por `MYSQL_TABLE` e `MYSQL_SERIAL_COLUMN`.

Variáveis aceitas: `MYSQL_HOST` ou `DB_HOST`; `MYSQL_PORT` ou `DB_PORT` (padrão 3306); `MYSQL_DATABASE`, `DB_NAME` ou `MYSQL_DB`; `MYSQL_USER` ou `DB_USER`; `MYSQL_PASSWORD` ou `DB_PASSWORD`. `PORT` define a porta do Python (padrão 5000).

A aplicação não cria banco nem altera a estrutura de tabelas. Agora consulta **e cadastra** registros. O usuário MySQL precisa de SELECT e INSERT; a tabela deve usar um mecanismo transacional como InnoDB e ter índice UNIQUE na coluna da série para impedir duplicidades entre aplicações concorrentes.

O sistema identifica as colunas existentes com `SHOW COLUMNS`. Para o nome do ativo, reconhece `ativo`, `nome`, `equipamento`, `descricao` ou `produto`; para Sede, `sede` ou `empresa`. Outros campos correspondem aos nomes do formulário. Se os nomes forem diferentes, adicione no `.env` um mapeamento JSON, por exemplo:

```dotenv
MYSQL_FIELD_MAP='{"ativo":"nome_equipamento","sede":"empresa"}'
```

Os nomes à direita devem existir na sua tabela. Um campo preenchido sem coluna correspondente impede a gravação e mostra uma mensagem; dados não são descartados silenciosamente. Campos obrigatórios adicionais no banco precisam ter valor padrão ou correspondência com o formulário. Não foi possível conferir o esquema nem conectar ao banco da empresa neste computador.

## Scanner

Clique em Iniciar câmera, autorize o acesso e enquadre o código de barras ou QR da série. A primeira abertura identifica as webcams disponíveis. Para trocar, pare a câmera, selecione outra no campo Câmera disponível e abra novamente. A consulta é automática. A câmera para após capturar; Nova leitura a reabre. Não há upload de fotos ou OCR: a série deve estar codificada no código, ou pode ser digitada. No navegador usado para testar a interface, nenhuma câmera foi detectada; a captura física ainda precisa ser confirmada no navegador com acesso à webcam. Localhost funciona no próprio computador; uso em celular pela rede exige configuração adicional de HTTPS e acesso.

O leitor [html5-qrcode](https://scanapp.org/html5-qrcode-docs/docs/intro) está incluído em `static/vendor`, junto da licença. As imagens são processadas no navegador, enviando ao Python apenas a série.

## Excel

Se aparecer HTTP 405 ou HTTP 404 ao selecionar uma planilha, o endereço aberto não está disponibilizando as rotas da API. Feche a página e execute `iniciar.bat` desta pasta; use a página aberta por ele. Não abra `templates/index.html` diretamente nem pelo Live Server do editor, pois isso não executa o servidor Python. O botão Importar só é habilitado depois que a leitura da planilha termina com sucesso; erros de leitura permanecem visíveis.

Baixe o modelo pela área de importação. Cabeçalhos na primeira linha: Ativo, Número de série, Categoria, Status, Matrícula, Data de garantia, Departamento, Responsável, Sede. Ativo e Número de série são obrigatórios. Série e matrícula devem ser texto para preservar zeros; formatos numéricos compostos por zeros também são reconhecidos. Datas podem ser células de data ou textos AAAA-MM-DD / DD/MM/AAAA. Converta fórmulas em valores. Colunas desconhecidas não são importadas.

A importação valida todas as linhas antes de gravar, ignora séries existentes e usa uma transação. Limites: 20 MB, 10.000 registros e 100 colunas.

Ao clicar em Exportar Excel, o sistema consulta o banco e baixa a planilha preenchida com todos os campos do formulário e as colunas adicionais da tabela. A aba Equipamentos contém uma linha por série, comparando sem diferenças de maiúsculas/minúsculas e espaços nas pontas. Valores iguais em campos de equipamentos diferentes, como Sede ou Categoria, permanecem porque são dados válidos.

Quando há registros duplicados, prioriza a data de atualização/cadastro mais recente e depois o maior ID; sem esses campos, prioriza o registro mais completo. Campos vazios são completados com valores disponíveis nas outras ocorrências. Valores conflitantes são preservados na aba Divergências para revisão. Itens diferentes sem série não são mesclados. Nada é excluído ou alterado no banco. Se o banco estiver inacessível, aparece uma mensagem e nenhum arquivo vazio é baixado.

## Verificação

Execute `.\.venv\Scripts\python -m unittest discover -s tests -v`. Os testes usam MySQL simulado e não acessam o banco da empresa.

Se tiver Node instalado, `node --test tests/camera.test.cjs` testa o controle da câmera com um dispositivo simulado.
