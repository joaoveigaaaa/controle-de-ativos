# Controle de ativos

Sistema em Python e Flask para consultar e cadastrar equipamentos no MySQL, escanear números de série com a câmera e importar/exportar Excel.

## Executar no Windows

1. Instale Python 3.13.
2. Coloque seu arquivo `.env` na pasta do projeto com a configuração do MySQL existente.
3. Execute `iniciar.bat`. O navegador abre automaticamente no endereço local disponível.

Os arquivos `.env`, ambientes virtuais e bancos locais não são versionados.

Consulte [LEIA-ME.md](LEIA-ME.md) para configurar tabela e colunas, operar o scanner, importar planilhas e entender a consolidação de séries repetidas na exportação.

## Testes

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
node --test tests/camera.test.cjs tests/excel-ui.test.cjs
```

Os testes simulam o MySQL e a câmera. A conexão real e a captura física dependem da configuração e dos dispositivos disponíveis no ambiente de execução.
