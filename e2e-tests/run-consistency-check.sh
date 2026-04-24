#!/bin/bash
# Script para verificar consistencia de las pruebas E2E
# Ejecuta la suite completa 3 veces consecutivas

set -e  # Salir si alguna ejecución falla

ITERATIONS=3
FAILED=0

echo "=========================================="
echo "Verificación de consistencia de pruebas E2E"
echo "Ejecutando $ITERATIONS veces consecutivas"
echo "=========================================="
echo ""

for i in $(seq 1 $ITERATIONS); do
    echo "┌─────────────────────────────────────────┐"
    echo "│  Ejecución $i de $ITERATIONS                      │"
    echo "└─────────────────────────────────────────┘"
    echo ""
    
    if mvn test; then
        echo ""
        echo "✅ Ejecución $i: EXITOSA"
        echo ""
    else
        echo ""
        echo "❌ Ejecución $i: FALLIDA"
        echo ""
        FAILED=1
        break
    fi
done

echo ""
echo "=========================================="
if [ $FAILED -eq 0 ]; then
    echo "✅ RESULTADO: Todas las ejecuciones pasaron"
    echo "Las pruebas son consistentes y no son flaky"
else
    echo "❌ RESULTADO: Al menos una ejecución falló"
    echo "Revisa los logs para identificar pruebas intermitentes"
    exit 1
fi
echo "=========================================="
