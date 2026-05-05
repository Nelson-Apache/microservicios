#!/bin/bash
# =====================================================
# Script de configuración automática de SonarQube
# =====================================================
# Este script:
#   1. Espera a que SonarQube esté listo
#   2. Crea un Quality Gate con cobertura >= 70%
#   3. Configura el webhook a Jenkins
#   4. Crea los proyectos
#   5. Asigna el Quality Gate a los proyectos
# =====================================================

SONAR_URL="${SONAR_URL:-http://localhost:9000}"
SONAR_USER="${SONAR_USER:-admin}"
SONAR_PASS="${SONAR_PASS:-admin123}"
SONAR_DEFAULT_PASS="admin"
JENKINS_URL="${JENKINS_URL:-http://jenkins:8080}"

echo "╔══════════════════════════════════════════════════╗"
echo "║  Configuración automática de SonarQube           ║"
echo "╚══════════════════════════════════════════════════╝"

# ─── 1. Esperar a que SonarQube esté listo ───
echo ""
echo "⏳ Esperando a que SonarQube esté disponible..."
until curl -s -f "${SONAR_URL}/api/system/status" | grep -q '"status":"UP"'; do
    echo "   SonarQube no está listo aún... reintentando en 10s"
    sleep 10
done
echo "✅ SonarQube está disponible"

# ─── 2. Cambiar contraseña por defecto ───
echo ""
echo "🔐 Cambiando contraseña por defecto de admin..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -u "${SONAR_USER}:${SONAR_DEFAULT_PASS}" \
    -X POST "${SONAR_URL}/api/users/change_password" \
    -d "login=${SONAR_USER}&previousPassword=${SONAR_DEFAULT_PASS}&password=${SONAR_PASS}")

if [ "$HTTP_CODE" = "204" ]; then
    echo "   ✅ Contraseña cambiada exitosamente"
elif [ "$HTTP_CODE" = "401" ]; then
    echo "   ℹ️  La contraseña ya fue cambiada previamente"
else
    echo "   ⚠️  Respuesta inesperada: HTTP ${HTTP_CODE}"
fi

# ─── 3. Crear Quality Gate con cobertura >= 70% ───
echo ""
echo "🚦 Creando Quality Gate 'CI-Pipeline-Gate' (cobertura >= 70%)..."

# Crear el Quality Gate
QG_RESPONSE=$(curl -s -u "${SONAR_USER}:${SONAR_PASS}" \
    -X POST "${SONAR_URL}/api/qualitygates/create" \
    -d "name=CI-Pipeline-Gate")

QG_ID=$(echo "$QG_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)

if [ -n "$QG_ID" ] && [ "$QG_ID" != "" ]; then
    echo "   ✅ Quality Gate creado con ID: ${QG_ID}"

    # Agregar condición de cobertura >= 70%
    curl -s -u "${SONAR_USER}:${SONAR_PASS}" \
        -X POST "${SONAR_URL}/api/qualitygates/create_condition" \
        -d "gateName=CI-Pipeline-Gate&metric=new_coverage&op=LT&error=70" > /dev/null

    echo "   ✅ Condición agregada: new_coverage >= 70%"

    # Establecer como Quality Gate por defecto
    curl -s -u "${SONAR_USER}:${SONAR_PASS}" \
        -X POST "${SONAR_URL}/api/qualitygates/set_as_default" \
        -d "name=CI-Pipeline-Gate" > /dev/null

    echo "   ✅ Establecido como Quality Gate por defecto"
else
    echo "   ℹ️  El Quality Gate ya existe o hubo un error"
fi

# ─── 4. Configurar Webhook a Jenkins ───
echo ""
echo "🔔 Configurando webhook de SonarQube → Jenkins..."

WEBHOOK_RESPONSE=$(curl -s -u "${SONAR_USER}:${SONAR_PASS}" \
    -X POST "${SONAR_URL}/api/webhooks/create" \
    -d "name=Jenkins&url=${JENKINS_URL}/sonarqube-webhook/")

echo "   ✅ Webhook configurado: ${JENKINS_URL}/sonarqube-webhook/"

# ─── 5. Crear proyectos ───
echo ""
echo "📦 Creando proyectos en SonarQube..."

for PROJECT in "notificaciones-service:Notificaciones Service" "departamentos-service:Departamentos Service"; do
    KEY=$(echo "$PROJECT" | cut -d: -f1)
    NAME=$(echo "$PROJECT" | cut -d: -f2)

    curl -s -u "${SONAR_USER}:${SONAR_PASS}" \
        -X POST "${SONAR_URL}/api/projects/create" \
        -d "project=${KEY}&name=${NAME}" > /dev/null

    echo "   ✅ Proyecto creado: ${KEY}"
done

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  ✅ Configuración de SonarQube completada        ║"
echo "║                                                  ║"
echo "║  📊 Dashboard:  ${SONAR_URL}                     ║"
echo "║  👤 Usuario:    ${SONAR_USER}                    ║"
echo "║  🔑 Contraseña: ${SONAR_PASS}                   ║"
echo "╚══════════════════════════════════════════════════╝"
