# Script para ejecutar tests E2E con variables de entorno configuradas

# Cargar variables desde .env
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        Set-Item -Path "env:$name" -Value $value
        Write-Host "OK $name configurado" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Ejecutando tests E2E..." -ForegroundColor Cyan
mvn test
