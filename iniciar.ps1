$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.env')) {
    Write-Host 'Coloque seu arquivo .env existente nesta pasta para conectar ao MySQL.'
}
Write-Host 'Acesse o endereço exibido abaixo. Ctrl+C encerra o sistema.'
$env:OPEN_BROWSER = '1'
python app.py
