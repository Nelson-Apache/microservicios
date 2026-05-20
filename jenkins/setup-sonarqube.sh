#!/bin/bash
# =====================================================
# Script de configuración automática de SonarQube
# =====================================================

SONAR_URL="${SONAR_URL:-http://localhost:9000}"
SONAR_USER="${SONAR_USER:-admin}"
SONAR_PASS="${SONAR_PASS:-admin123}"
SONAR_DEFAULT_PASS="admin"
JENKINS_URL="${JENKINS_URL:-http://jenkins:8080}"

echo "=================================================="
echo "  Configuracion automatica de SonarQube"
echo "=================================================="

# ─── 1. Esperar a que SonarQube esté listo ───
echo ""
echo "Esperando a que SonarQube este disponible..."
until curl -s -f "${SONAR_URL}/api/system/status" | grep -q '"status":"UP"'; do
    echo "  SonarQube no esta listo aun... reintentando en 10s"
    sleep 10
done
echo "SonarQube disponible"

# ─── 2. Cambiar contraseña por defecto ───
echo ""
echo "Cambiando contrasena por defecto de admin..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -u "${SONAR_USER}:${SONAR_DEFAULT_PASS}" \
    -X POST "${SONAR_URL}/api/users/change_password" \
    -d "login=${SONAR_USER}&previousPassword=${SONAR_DEFAULT_PASS}&password=${SONAR_PASS}")

if [ "$HTTP_CODE" = "204" ]; then
    echo "  Contrasena cambiada exitosamente"
elif [ "$HTTP_CODE" = "401" ]; then
    echo "  La contrasena ya fue cambiada previamente"
else
    echo "  Respuesta HTTP ${HTTP_CODE}"
fi

# ─── 3. Deshabilitar autenticación forzada ───
# Necesario para que Jenkins pueda enviar análisis sin token configurado
echo ""
echo "Deshabilitando autenticacion forzada para analisis..."
curl -s -o /dev/null -u "${SONAR_USER}:${SONAR_PASS}" \
    -X POST "${SONAR_URL}/api/settings/set" \
    -d "key=sonar.forceAuthentication&value=false"
echo "  Autenticacion forzada deshabilitada"

# ─── 4. Crear Quality Gate con cobertura >= 70% ───
echo ""
echo "Creando Quality Gate 'CI-Pipeline-Gate' (cobertura >= 70%)..."

QG_RESPONSE=$(curl -s -u "${SONAR_USER}:${SONAR_PASS}" \
    -X POST "${SONAR_URL}/api/qualitygates/create" \
    -d "name=CI-Pipeline-Gate")

QG_ID=$(echo "$QG_RESPONSE" | tr ',' '\n' | grep '"id"' | head -1 | tr -d '" ' | cut -d: -f2)

if [ -n "$QG_ID" ]; then
    echo "  Quality Gate creado con ID: ${QG_ID}"

    curl -s -o /dev/null -u "${SONAR_USER}:${SONAR_PASS}" \
        -X POST "${SONAR_URL}/api/qualitygates/create_condition" \
        -d "gateName=CI-Pipeline-Gate&metric=coverage&op=LT&error=70"
    echo "  Condicion agregada: coverage >= 70%"

    curl -s -o /dev/null -u "${SONAR_USER}:${SONAR_PASS}" \
        -X POST "${SONAR_URL}/api/qualitygates/set_as_default" \
        -d "name=CI-Pipeline-Gate"
    echo "  Establecido como Quality Gate por defecto"
else
    echo "  El Quality Gate ya existe o no se pudo crear"
fi

# ─── 5. Configurar Webhook a Jenkins ───
echo ""
echo "Configurando webhook SonarQube -> Jenkins..."
curl -s -o /dev/null -u "${SONAR_USER}:${SONAR_PASS}" \
    -X POST "${SONAR_URL}/api/webhooks/create" \
    -d "name=Jenkins&url=${JENKINS_URL}/sonarqube-webhook/"
echo "  Webhook configurado: ${JENKINS_URL}/sonarqube-webhook/"

# ─── 6. Generar token para análisis CI ───
echo ""
echo "Generando token para análisis CI de SonarQube..."
curl -s -o /dev/null -u "${SONAR_USER}:${SONAR_PASS}" \
    -X POST "${SONAR_URL}/api/user_tokens/revoke" \
    -d "login=${SONAR_USER}&name=jenkins-ci"
TOKEN_JSON=$(curl -s -u "${SONAR_USER}:${SONAR_PASS}" \
    -X POST "${SONAR_URL}/api/user_tokens/generate" \
    -d "login=${SONAR_USER}&name=jenkins-ci&type=USER_TOKEN")
SONAR_CI_TOKEN=$(echo "$TOKEN_JSON" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
if [ -n "$SONAR_CI_TOKEN" ]; then
    echo "$SONAR_CI_TOKEN" > /var/jenkins_home/sonarqube-token
    chmod 644 /var/jenkins_home/sonarqube-token
    echo "  Token guardado en /var/jenkins_home/sonarqube-token"
else
    echo "  No se pudo generar el token de análisis"
fi

# ─── 7. Crear los 8 proyectos y asignar el Quality Gate ───
echo ""
echo "Creando proyectos en SonarQube..."

for PROJECT in \
    "api-gateway:API Gateway" \
    "auth-service:Auth Service" \
    "empleados-service:Empleados Service" \
    "departamentos-service:Departamentos Service" \
    "perfiles-service:Perfiles Service" \
    "notificaciones-service:Notificaciones Service" \
    "vacaciones-service:Vacaciones Service" \
    "reportes-service:Reportes Service"; do

    KEY=$(echo "$PROJECT" | cut -d: -f1)
    NAME=$(echo "$PROJECT" | cut -d: -f2-)

    curl -s -o /dev/null -u "${SONAR_USER}:${SONAR_PASS}" \
        -X POST "${SONAR_URL}/api/projects/create" \
        -d "project=${KEY}&name=${NAME}"

    curl -s -o /dev/null -u "${SONAR_USER}:${SONAR_PASS}" \
        -X POST "${SONAR_URL}/api/qualitygates/select" \
        -d "projectKey=${KEY}&gateName=CI-Pipeline-Gate"

    echo "  ${KEY} [Quality Gate asignado]"
done

echo ""
echo "=================================================="
echo "  Configuracion de SonarQube completada"
echo "  Dashboard: ${SONAR_URL}"
echo "  Usuario:   ${SONAR_USER}"
echo "  Contrasena: ${SONAR_PASS}"
echo "=================================================="
