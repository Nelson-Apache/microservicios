package com.empresa.e2e.step_definitions;

import com.empresa.e2e.support.ConfiguracionBase;
import com.empresa.e2e.support.TestContext;
import io.cucumber.java.en.Given;

/**
 * Step definitions para el SMOKE TEST (verificación básica del sistema).
 * 
 * PROPÓSITO:
 * Verificar que el sistema está operativo antes de ejecutar pruebas complejas.
 * Este es el test más básico y rápido que se puede ejecutar.
 * 
 * SMOKE TEST:
 * Un smoke test es una prueba rápida que verifica que las funcionalidades
 * básicas del sistema funcionan. Si el smoke test falla, no tiene sentido
 * ejecutar pruebas más complejas.
 * 
 * ESCENARIO CUBIERTO:
 * - El sistema responde correctamente (health.feature)
 * 
 * ENDPOINT VERIFICADO:
 * GET /health → Debe retornar 200 OK
 * 
 * USO:
 * Este test se ejecuta primero para detectar rápidamente si:
 * - El API Gateway está accesible
 * - La red está configurada correctamente
 * - Los servicios backend están respondiendo
 * - Las variables de entorno están configuradas
 */
public class HealthSteps extends ConfiguracionBase {

    public HealthSteps(TestContext ctx) {
        super(ctx);
    }

    /**
     * Paso: "Dado que el sistema está desplegado y operativo"
     * 
     * PROPÓSITO:
     * Verificar que el API Gateway está accesible y responde correctamente.
     * 
     * ENDPOINT:
     * GET /health
     * 
     * RESPUESTA ESPERADA:
     * {
     *   "status": "healthy"
     * }
     * 
     * VERIFICACIÓN:
     * La respuesta se guarda en ctx.ultimaRespuesta para que el paso
     * "Entonces la respuesta debe tener código 200" pueda verificarla.
     * 
     * IMPORTANCIA:
     * Este es el primer paso que se ejecuta en el smoke test.
     * Si falla, indica que:
     * - El sistema no está levantado (docker-compose no está corriendo)
     * - La URL base está mal configurada (BASE_URL en .env)
     * - Hay problemas de red o firewall
     * - El API Gateway no está respondiendo
     * 
     * USO:
     * Se usa en health.feature como smoke test básico.
     * También se puede usar en Antecedentes de otros features para verificar
     * que el sistema está operativo antes de ejecutar el escenario.
     */
    @Given("que el sistema está desplegado y operativo")
    public void sistemaOperativo() {
        ctx.setUltimaRespuesta(request().get("/health"));
    }
}
