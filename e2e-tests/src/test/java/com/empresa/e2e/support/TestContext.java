package com.empresa.e2e.support;

import io.restassured.response.Response;

/**
 * Contexto compartido entre step definitions dentro de un mismo escenario.
 * 
 * PROPÓSITO:
 * - Almacenar el estado compartido entre pasos de un mismo escenario (token JWT, respuestas HTTP, IDs)
 * - Resolver variables de entorno de forma centralizada
 * - Garantizar aislamiento entre escenarios (cada escenario tiene su propia instancia)
 *
 * CICLO DE VIDA:
 * Cucumber con PicoContainer crea una NUEVA instancia de TestContext para cada escenario.
 * Esto garantiza que no hay "contaminación" de datos entre escenarios diferentes.
 * 
 * INYECCIÓN DE DEPENDENCIAS:
 * Cada step definition declara TestContext en su constructor:
 *   public AuthSteps(TestContext ctx) { super(ctx); }
 * 
 * PicoContainer automáticamente inyecta la misma instancia de TestContext en todos
 * los step definitions que se ejecutan dentro del mismo escenario.
 *
 * RESOLUCIÓN DE VARIABLES DE ENTORNO:
 * Prioridad (de mayor a menor):
 *   1. System property (-Dbase.url=...)
 *   2. Variable de entorno (BASE_URL=...)
 *   3. Valor por defecto (solo para BASE_URL)
 */
public class TestContext {

    // ══════════════════════════════════════════════════════════════════════════
    // VARIABLES DE ENTORNO
    // ══════════════════════════════════════════════════════════════════════════
    // Se resuelven al crear la instancia y son inmutables (final)

    /** 
     * URL base del API Gateway. 
     * Ejemplo: http://localhost:8000 o http://api-gateway:8000 (en Docker)
     */
    public final String baseUrl = env("BASE_URL", "http://localhost:8000");

    /** 
     * Credenciales del usuario ADMIN (rol con permisos completos).
     * Se usan en escenarios que requieren crear/eliminar empleados.
     */
    public final String adminUser     = env("ADMIN_USER",     null);
    public final String adminPassword = env("ADMIN_PASSWORD", null);

    /** 
     * Credenciales del usuario USER (rol básico con permisos limitados).
     * Se usan en escenarios de seguridad para verificar restricciones RBAC.
     */
    public final String userUser     = env("USER_USER",     null);
    public final String userPassword = env("USER_PASSWORD", null);

    // ══════════════════════════════════════════════════════════════════════════
    // ESTADO POR ESCENARIO
    // ══════════════════════════════════════════════════════════════════════════
    // Variables mutables que almacenan el estado durante la ejecución del escenario

    /** 
     * Última respuesta HTTP recibida.
     * Se usa en pasos "Entonces" para verificar códigos de estado y contenido.
     */
    private Response ultimaRespuesta;
    
    /** 
     * Token JWT de autenticación actual.
     * Se obtiene en pasos "Dado que estoy autenticado" y se usa en peticiones posteriores.
     */
    private String   tokenJwt;
    
    /** 
     * ID del empleado creado en el escenario actual.
     * Se usa para consultas, eliminaciones y verificaciones posteriores.
     */
    private Integer  empleadoId;
    
    /** 
     * Email del empleado creado en el escenario actual.
     * Se usa para verificar creación de credenciales y hacer login.
     */
    private String   empleadoEmail;
    
    /** 
     * Contraseña del empleado establecida en el escenario actual.
     * Se usa para verificar que el empleado puede hacer login después del onboarding.
     */
    private String   empleadoPassword;

    // ══════════════════════════════════════════════════════════════════════════
    // GETTERS / SETTERS
    // ══════════════════════════════════════════════════════════════════════════

    public Response getUltimaRespuesta() { return ultimaRespuesta; }
    public void setUltimaRespuesta(Response r) { this.ultimaRespuesta = r; }

    public String getTokenJwt() { return tokenJwt; }
    public void setTokenJwt(String token) { this.tokenJwt = token; }

    /**
     * Verifica si hay un token JWT válido almacenado.
     * Útil para validar que el usuario está autenticado antes de hacer peticiones.
     */
    public boolean tieneToken() {
        return tokenJwt != null && !tokenJwt.isBlank();
    }

    public Integer getEmpleadoId() { return empleadoId; }
    public void setEmpleadoId(Integer id) { this.empleadoId = id; }

    public String getEmpleadoEmail() { return empleadoEmail; }
    public void setEmpleadoEmail(String email) { this.empleadoEmail = email; }

    public String getEmpleadoPassword() { return empleadoPassword; }
    public void setEmpleadoPassword(String password) { this.empleadoPassword = password; }

    // ══════════════════════════════════════════════════════════════════════════
    // HELPER PRIVADO PARA RESOLUCIÓN DE VARIABLES DE ENTORNO
    // ══════════════════════════════════════════════════════════════════════════

    /**
     * Resuelve una variable de entorno con prioridad definida.
     * 
     * ORDEN DE BÚSQUEDA:
     * 1. System property: -Dbase.url=http://localhost:8000
     * 2. Variable de entorno: BASE_URL=http://localhost:8000
     * 3. Valor por defecto (si se proporciona)
     * 
     * CONVERSIÓN DE NOMBRES:
     * BASE_URL → base.url (para system properties)
     * ADMIN_USER → admin.user
     * 
     * MANEJO DE ERRORES:
     * Si no se encuentra la variable y no hay valor por defecto,
     * lanza IllegalStateException con mensaje descriptivo.
     * 
     * @param key Nombre de la variable de entorno (ej: "BASE_URL")
     * @param defaultValue Valor por defecto (puede ser null)
     * @return Valor resuelto de la variable
     * @throws IllegalStateException si la variable es requerida y no está configurada
     */
    private static String env(String key, String defaultValue) {
        // Convertir BASE_URL → base.url para system properties
        String propKey = key.toLowerCase().replace('_', '.');
        
        // Buscar primero en system properties, luego en variables de entorno
        String value = System.getProperty(propKey, System.getenv(key));
        
        if (value == null || value.isBlank()) {
            if (defaultValue != null) return defaultValue;
            
            // Variable requerida no configurada → error descriptivo
            throw new IllegalStateException(
                "Variable de entorno requerida no configurada: " + key +
                "\nDefínela como variable de entorno o con -D" + propKey + "=<valor>"
            );
        }
        return value;
    }
}
