# Script para verificar consistencia de las pruebas E2E (PowerShell)
# Ejecuta la suite completa 3 veces consecutivas

$ErrorActionPreference = "Stop"

$ITERATIONS = 3
$FAILED = $false

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Verificacion de consistencia de pruebas E2E" -ForegroundColor Cyan
Write-Host "Ejecutando $ITERATIONS veces consecutivas" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

for ($i = 1; $i -le $ITERATIONS; $i++) {
    Write-Host "===========================================" -ForegroundColor Yellow
    Write-Host "  Ejecucion $i de $ITERATIONS" -ForegroundColor Yellow
    Write-Host "===========================================" -ForegroundColor Yellow
    Write-Host ""
    
    mvn test
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[OK] Ejecucion ${i}: EXITOSA" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "[ERROR] Ejecucion ${i}: FALLIDA" -ForegroundColor Red
        Write-Host ""
        $FAILED = $true
        break
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
if (-not $FAILED) {
    Write-Host "[OK] RESULTADO: Todas las ejecuciones pasaron" -ForegroundColor Green
    Write-Host "Las pruebas son consistentes y no son flaky" -ForegroundColor Green
} else {
    Write-Host "[ERROR] RESULTADO: Al menos una ejecucion fallo" -ForegroundColor Red
    Write-Host "Revisa los logs para identificar pruebas intermitentes" -ForegroundColor Red
    exit 1
}
Write-Host "==========================================" -ForegroundColor Cyan
