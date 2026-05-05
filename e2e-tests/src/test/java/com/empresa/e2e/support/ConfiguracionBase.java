package com.empresa.e2e.support;

import io.restassured.RestAssured;
import io.restassured.specification.RequestSpecification;

/**
 * Clase base para todos los step definitions.
 * 
 * PROPÓSITO:
 * - Proporcionar acceso al contexto compartido (TestContext)
 * - Ofrecer helpers de Rest Assured preconfigurados
 * - Evitar duplicación de código en los step definitions
 * 
 * USO:
 * Todos los step definitions extienden esta clase:
 *   public class AuthSteps extends ConfiguracionBase {
 *       public AuthSteps(TestContext ctx) { super(ctx); }
 *   }
 * 
 * HELPERS DISPONIBLES:
 * - request(): Petición HTTP sin autenticación
 * - requestAutenticado(): Petición HTTP con token JWT
 */
public class ConfiguracionBase {

    /** Contexto compartido inyectado por PicoContainer */
    protected final TestContext ctx;

    /**
     * Constructor que recibe el contexto compartido.
     * PicoContainer inyecta automáticamente la instancia de TestContext.
     */
    public ConfiguracionBase(TestContext ctx) {
        this.ctx = ctx;
    }

    /**
     * Crea una petición HTTP sin autenticación.
     * 
     * CONFIGURACIÓN:
     * - baseUri: URL del API Gateway (desde ctx.baseUrl)
     * - contentType: application/json (por defecto)
     * - log().ifValidationFails(): Muestra logs solo si la validación falla
     * 
     * USO:
     *   request().get("/health")
     *   request().body(loginData).post("/auth/login")
     * 
     * @return RequestSpecification de Rest Assured listo para usar
     */
    protected RequestSpecification request() {
        return RestAssured.given()
                .baseUri(ctx.baseUrl)
                .contentType("application/json")
                .log().ifValidationFails();
    }

    /**
     * Crea una petición HTTP con header de autenticación JWT.
     * 
     * CONFIGURACIÓN:
     * - Incluye todo lo de request()
     * - Agrega header: Authorization: Bearer <token>
     * 
     * PREREQUISITO:
     * El token JWT debe estar almacenado en ctx.tokenJwt
     * (normalmente se obtiene en un paso "Dado que estoy autenticado")
     * 
     * USO:
     *   requestAutenticado().get("/empleados")
     *   requestAutenticado().body(empleado).post("/empleados")
     * 
     * @return RequestSpecification con autenticación JWT
     */
    protected RequestSpecification requestAutenticado() {
        return request().header("Authorization", "Bearer " + ctx.getTokenJwt());
    }
}
