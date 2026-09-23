$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.env')) {
    Write-Host 'Coloque seu arquivo .env existente nesta pasta para conectar ao MySQL.'
}
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Instale o Python e tente novamente.' }
}
& '.venv/Scripts/python.exe' -m pip install -r requirements.txt --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências. Confira a conexão com a internet.' }
Write-Host 'Acesse o endereço exibido abaixo. Ctrl+C encerra o sistema.'
$env:OPEN_BROWSER = '1'
& '.venv/Scripts/python.exe' app.py
