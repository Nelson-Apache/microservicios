package com.empresa.e2e.step_definitions;

import com.empresa.e2e.support.ConfiguracionBase;
import com.empresa.e2e.support.TestContext;
import com.empresa.e2e.support.WaitUtils;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import io.restassured.response.Response;

import java.util.HashMap;
import java.util.Map;

import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.*;

/**
 * Step definitions para escenarios de OFFBOARDING de empleados.
 * 
 * PROPÓSITO:
 * Verificar el flujo completo de desvinculación de empleados, incluyendo:
 * - Eliminación del empleado del sistema
 * - Inhabilitación de credenciales (evento asincrónico)
 * - Envío de notificación de desvinculación (evento asincrónico)
 * - Bloqueo de recuperación de contraseña
 * 
 * FLUJO DE OFFBOARDING:
 * 1. ADMIN elimina un empleado en empleados-service
 * 2. empleados-service publica evento "empleado.eliminado" en RabbitMQ
 * 3. auth-service consume el evento y deshabilita credenciales (asincrónico)
 * 4. notificaciones-service consume el evento y envía notificación (asincrónico)
 * 
 * DESAFÍOS:
 * - Eventos asincrónicos: No podemos verificar inmediatamente
 * - Consistencia eventual: Usamos polling con WaitUtils
 * - Setup complejo: Necesitamos un empleado con credenciales activas
 * 
 * ESCENARIOS CUBIERTOS:
 * 1. Desvinculación completa → verificar notificación
 * 2. Empleado desvinculado no puede hacer login
 * 3. Recuperación de contraseña falla para empleado desvinculado
 */
public class OffboardingSteps extends ConfiguracionBase {

    public OffboardingSteps(TestContext ctx) {
        super(ctx);
    }

    /**
     * Paso: "Dado que existe un empleado activo con credenciales configuradas"
     * 
     * PROPÓSITO:
     * Crear un empleado completo con credenciales activas para probar el offboarding.
     * Este es un SETUP COMPLEJO que prepara el estado necesario para los escenarios.
     * 
     * FLUJO COMPLETO:
     * 1. Autenticarse como ADMIN
     * 2. Crear un empleado con ID único (timestamp)
     * 3. Esperar asincrónicamente a que se creen las credenciales (polling)
     * 4. Generar token de recuperación con JwtTestUtils
     * 5. Establecer contraseña usando el token
     * 6. Guardar email y contraseña en TestContext
     * 
     * TÉCNICAS UTILIZADAS:
     * - IDs únicos con timestamp para evitar colisiones
     * - Polling con WaitUtils para esperar creación de credenciales
     * - JwtTestUtils para generar token de recuperación
     * - Reutilización de lógica de onboarding
     * 
     * DATOS GUARDADOS EN CONTEXTO:
     * - ctx.empleadoId: Para eliminar el empleado después
     * - ctx.empleadoEmail: Para intentar login después de desvinculación
     * - ctx.empleadoPassword: Para verificar que el login falla
     * 
     * VENTAJAS:
     * ✅ Cada escenario tiene su propio empleado independiente
     * ✅ No depende de datos precargados en la base de datos
     * ✅ No depende de otros escenarios
     * ✅ Reutiliza la lógica de onboarding (DRY)
     * 
     * TIMEOUT:
     * Usa 10 intentos × 2s = 20s para esperar la creación de credenciales.
     */
    @Given("que existe un empleado activo con credenciales configuradas")
    public void crearEmpleadoActivoConCredenciales() {
        // Primero autenticarse como ADMIN para poder crear el empleado
        Map<String, String> loginBody = new HashMap<>();
        loginBody.put("nombre_usuario", ctx.adminUser);
        loginBody.put("contrasena", ctx.adminPassword);

        Response loginResponse = request().body(loginBody).post("/auth/login");
        assertThat("Login de admin falló", loginResponse.statusCode(), equalTo(200));
        ctx.setTokenJwt(loginResponse.jsonPath().getString("access_token"));

        // Crear un empleado para el test de offboarding con ID único
        String timestamp = String.valueOf(System.currentTimeMillis());
        String email = "empleado_offboarding_" + timestamp + "@empresa.com";
        int empleadoId = (int) (System.currentTimeMillis() % 1000000);
        
        Map<String, Object> body = new HashMap<>();
        body.put("id", empleadoId);
        body.put("nombre", "Empleado Offboarding " + timestamp);
        body.put("email", email);
        body.put("cargo", "Temporal");
        // departamento_id es opcional

        Response response = requestAutenticado().body(body).post("/empleados");
        assertThat("No se pudo crear el empleado de prueba", response.statusCode(), equalTo(201));
        
        ctx.setEmpleadoId(empleadoId);
        ctx.setEmpleadoEmail(email);

        // Esperar a que se creen las credenciales (evento asincrónico)
        // Intentamos hacer login para verificar que el usuario existe
        WaitUtils.waitUntil(() -> {
            Map<String, String> testLoginBody = new HashMap<>();
            testLoginBody.put("nombre_usuario", email);
            testLoginBody.put("contrasena", "cualquier_contrasena");

            Response testResponse = request().body(testLoginBody).post("/auth/login");
            
            // El usuario existe si da 401 (credenciales incorrectas o inhabilitado)
            // En lugar de error de "usuario no encontrado"
            if (testResponse.statusCode() == 401) {
                String detalle = testResponse.jsonPath().getString("detail");
                return detalle != null && 
                       (detalle.contains("inhabilitado") || detalle.contains("Credenciales"));
            }
            
            return false;
        }, 10, 2000);

        // Establecer contraseña para el empleado usando JwtTestUtils
        // Necesita WaitUtils porque el evento RabbitMQ de creación es asíncrono
        final Response[] resetResponseFinal = new Response[1];
        String password = "Password123!";
        
        WaitUtils.waitUntil(() -> {
            String tokenRecuperacion = com.empresa.e2e.support.JwtTestUtils.crearTokenRecuperacion(email);
            
            Map<String, String> resetBody = new HashMap<>();
            resetBody.put("token", tokenRecuperacion);
            resetBody.put("nueva_contrasena", password);
            
            Response resetResponse = request().body(resetBody).post("/auth/reset-password");
            resetResponseFinal[0] = resetResponse;
            return resetResponse.statusCode() == 200;
        }, 10, 2000);
        
        assertThat("No se pudo establecer la contraseña", resetResponseFinal[0].statusCode(), equalTo(200));
        
        ctx.setEmpleadoPassword(password);
    }

    /**
     * Paso: "Dado que el empleado tiene credenciales activas"
     * 
     * PROPÓSITO:
     * Verificar que el empleado puede hacer login ANTES de eliminarlo.
     * Esto asegura que el setup fue exitoso y que las credenciales están activas.
     * 
     * VERIFICACIÓN:
     * Intenta hacer login con el email y contraseña del empleado.
     * Si el login es exitoso (200), las credenciales están activas.
     * 
     * PREREQUISITOS:
     * - ctx.empleadoEmail debe estar configurado
     * - ctx.empleadoPassword debe estar configurado
     * 
     * IMPORTANCIA:
     * Este paso es crucial para verificar que el estado inicial es correcto.
     * Si este paso falla, significa que el setup no funcionó correctamente.
     */
    @Given("que el empleado tiene credenciales activas")
    public void verificarCredencialesActivas() {
        // Verificar que el empleado puede hacer login antes de eliminarlo
        String email = ctx.getEmpleadoEmail();
        String password = ctx.getEmpleadoPassword();
        
        assertThat("No se guardó el email del empleado", email, notNullValue());
        assertThat("No se guardó la contraseña del empleado", password, notNullValue());

        Map<String, String> loginBody = new HashMap<>();
        loginBody.put("nombre_usuario", email);
        loginBody.put("contrasena", password);

        WaitUtils.waitUntil(() -> {
            Response response = request().body(loginBody).post("/auth/login");
            if (response.statusCode() != 200) {
                System.out.println("Login falló: " + response.getBody().asString());
            }
            return response.statusCode() == 200;
        }, 5, 1000);

        Response finalResp = request().body(loginBody).post("/auth/login");
        assertThat("El empleado no puede hacer login antes de eliminarlo", 
                   finalResp.statusCode(), equalTo(200));
    }

    /**
     * Paso: "Cuando elimino el empleado"
     * 
     * PROPÓSITO:
     * Eliminar el empleado del sistema, lo que dispara el flujo de offboarding.
     * 
     * ENDPOINT:
     * DELETE /empleados/{id}
     * 
     * PREREQUISITO:
     * - ctx.empleadoId debe estar configurado
     * - El usuario debe estar autenticado como ADMIN
     * 
     * EFECTO SECUNDARIO:
     * Al eliminar el empleado, se publica el evento "empleado.eliminado" en RabbitMQ,
     * que dispara acciones asincrónicas:
     * - auth-service deshabilita las credenciales del empleado
     * - notificaciones-service envía notificación de desvinculación
     * 
     * RESULTADO ESPERADO:
     * - Código: 204 No Content (eliminación exitosa)
     */
    @When("elimino el empleado")
    public void eliminarEmpleado() {
        Integer empleadoId = ctx.getEmpleadoId();
        assertThat("No se guardó el ID del empleado", empleadoId, notNullValue());

        ctx.setUltimaRespuesta(requestAutenticado().delete("/empleados/" + empleadoId));
    }

    /**
     * Paso: "Cuando el empleado intenta hacer login"
     * 
     * PROPÓSITO:
     * Intentar hacer login con las credenciales del empleado desvinculado
     * y esperar asincrónicamente a que el login falle.
     * 
     * TÉCNICA: POLLING CON REINTENTOS
     * No podemos verificar inmediatamente porque el evento es asincrónico.
     * Usamos WaitUtils.waitUntil() para consultar repetidamente hasta que
     * el login falle con 401.
     * 
     * PREREQUISITOS:
     * - ctx.empleadoEmail debe estar configurado
     * - ctx.empleadoPassword debe estar configurado
     * - El empleado debe haber sido eliminado previamente
     * 
     * RESULTADO ESPERADO:
     * Eventualmente (después de que auth-service procese el evento):
     * - Código: 401 Unauthorized
     * - Mensaje: "Usuario inhabilitado" o similar
     * 
     * TIMEOUT: 10 intentos × 2s = 20s
     */
    @When("el empleado intenta hacer login")
    public void empleadoIntentaLogin() {
        String email = ctx.getEmpleadoEmail();
        String password = ctx.getEmpleadoPassword();
        
        assertThat("No se guardó el email del empleado", email, notNullValue());
        assertThat("No se guardó la contraseña del empleado", password, notNullValue());

        // Esperar a que el evento de deshabilitación se procese
        WaitUtils.waitUntil(() -> {
            Map<String, String> loginBody = new HashMap<>();
            loginBody.put("nombre_usuario", email);
            loginBody.put("contrasena", password);

            Response response = request().body(loginBody).post("/auth/login");
            ctx.setUltimaRespuesta(response);
            
            // Esperar hasta que el login falle con 401
            return response.statusCode() == 401;
        }, 10, 2000);
    }

    /**
     * Paso: "Cuando solicito recuperación de contraseña para el empleado desvinculado"
     * 
     * PROPÓSITO:
     * Intentar recuperar la contraseña de un empleado desvinculado.
     * 
     * ENDPOINT:
     * POST /auth/recover-password
     * Body: { "email": "empleado@empresa.com" }
     * 
     * PREREQUISITO:
     * - ctx.empleadoEmail debe estar configurado
     * - El empleado debe haber sido eliminado previamente
     * 
     * COMPORTAMIENTO ESPERADO:
     * El sistema debe retornar el mensaje genérico (por seguridad),
     * pero NO debe generar un token de recuperación válido.
     * 
     * RESULTADO ESPERADO:
     * - Código: 200 OK (mensaje genérico por seguridad)
     * - Mensaje: "Si el email está registrado, recibirás un correo..."
     * 
     * NOTA:
     * El sistema retorna 200 para evitar enumeración de usuarios,
     * pero internamente no genera el token si el usuario está inhabilitado.
     */
    @When("solicito recuperación de contraseña para el empleado desvinculado")
    public void solicitarRecuperacionEmpleadoDesvinculado() {
        String email = ctx.getEmpleadoEmail();
        assertThat("No se guardó el email del empleado", email, notNullValue());

        Map<String, String> body = new HashMap<>();
        body.put("email", email);

        ctx.setUltimaRespuesta(request().body(body).post("/auth/recover-password"));
    }

    /**
     * Paso: "Entonces eventualmente el usuario debe estar deshabilitado"
     * 
     * PROPÓSITO:
     * Verificar que el evento "empleado.eliminado" fue procesado por auth-service
     * y las credenciales del empleado fueron deshabilitadas.
     * 
     * TÉCNICA: POLLING CON REINTENTOS
     * No podemos verificar inmediatamente porque el evento es asincrónico.
     * Usamos WaitUtils.waitUntil() para consultar repetidamente.
     * 
     * ESTRATEGIA DE VERIFICACIÓN:
     * Intentamos hacer login con las credenciales reales del empleado.
     * 
     * INTERPRETACIÓN DE RESPUESTAS:
     * - 401 + "Usuario inhabilitado" → ✅ Usuario deshabilitado correctamente
     * - 200 → ❌ Usuario aún activo (evento no procesado)
     * - 401 + otro mensaje → ❌ Error inesperado
     * 
     * TIMEOUT: 30 intentos × 2s = 60 segundos
     * 
     * NOTA:
     * El timeout es mayor que en onboarding (60s vs 20s) porque el offboarding
     * puede tardar más en procesarse, especialmente si hay múltiples eventos
     * en la cola de RabbitMQ.
     */
    @Then("eventualmente el usuario debe estar deshabilitado")
    public void verificarUsuarioDeshabilitado() {
        String email = ctx.getEmpleadoEmail();
        String password = ctx.getEmpleadoPassword();
        assertThat("No se guardó el email del empleado", email, notNullValue());
        assertThat("No se guardó la contraseña del empleado", password, notNullValue());

        WaitUtils.waitUntil(() -> {
            // Intentar login con el usuario eliminado usando su contraseña real
            Map<String, String> loginBody = new HashMap<>();
            loginBody.put("nombre_usuario", email);
            loginBody.put("contrasena", password);

            Response response = request().body(loginBody).post("/auth/login");
            
            // El usuario está deshabilitado si da 401 con mensaje "Usuario inhabilitado"
            if (response.statusCode() == 401) {
                String detalle = response.jsonPath().getString("detail");
                return detalle != null && detalle.contains("inhabilitado");
            }
            
            return false;
        }, 30, 2000); // 30 intentos × 2s = 60 segundos timeout para eventos asíncronos
    }

    /**
     * Paso: "Entonces eventualmente debe existir una notificación de desvinculación"
     * 
     * PROPÓSITO:
     * Verificar que el evento "empleado.eliminado" fue procesado por notificaciones-service
     * y se generó una notificación de tipo DESVINCULACION u OFFBOARDING.
     * 
     * TÉCNICA: POLLING CON REINTENTOS
     * Consultamos repetidamente GET /notificaciones/{empleadoId} hasta que:
     * - Existe al menos una notificación con tipo "DESVINCULACION" o "OFFBOARDING" → ✅ éxito
     * - Se agota el timeout (20 segundos) → ❌ fallo
     * 
     * ENDPOINT:
     * GET /notificaciones/{empleadoId}
     * Retorna: [ { "tipo": "DESVINCULACION", ... }, ... ]
     * 
     * PREREQUISITO:
     * - ctx.empleadoId debe estar configurado
     * - El usuario debe estar autenticado como ADMIN
     * 
     * TIMEOUT: 10 intentos × 2 segundos = 20 segundos
     */
    @Then("eventualmente debe existir una notificación de desvinculación")
    public void verificarNotificacionDesvinculacion() {
        Integer empleadoId = ctx.getEmpleadoId();
        assertThat("No se guardó el ID del empleado", empleadoId, notNullValue());

        WaitUtils.waitUntil(() -> {
            // Consultar notificaciones del empleado
            Response response = requestAutenticado().get("/notificaciones/" + empleadoId);
            
            if (response.statusCode() == 200) {
                try {
                    java.util.List<Map<String, Object>> notificaciones = response.jsonPath().getList("$");
                    return notificaciones != null && notificaciones.stream()
                            .anyMatch(n -> "DESVINCULACION".equals(n.get("tipo")) || 
                                          "OFFBOARDING".equals(n.get("tipo")));
                } catch (Exception e) {
                    return false;
                }
            }
            
            return false;
        }, 10, 2000);
    }

    /**
     * Paso: "Entonces el mensaje debe indicar que el usuario está inhabilitado"
     * 
     * PROPÓSITO:
     * Verificar que el mensaje de error del login contiene la palabra "inhabilitado".
     * 
     * VERIFICACIÓN:
     * Extrae el campo "detail" de la respuesta JSON y verifica que contiene
     * la palabra "inhabilitado".
     * 
     * ESTRUCTURA ESPERADA:
     * {
     *   "detail": "Usuario inhabilitado"
     * }
     * 
     * USO:
     * Se usa después de intentar hacer login con un empleado desvinculado
     * para verificar que el mensaje de error es descriptivo.
     */
    @Then("el mensaje debe indicar que el usuario está inhabilitado")
    public void verificarMensajeInhabilitado() {
        String detalle = ctx.getUltimaRespuesta().jsonPath().getString("detail");
        assertThat("El mensaje no indica que el usuario está inhabilitado", 
                   detalle, containsString("inhabilitado"));
    }

    /**
     * Paso: "Entonces eventualmente no debe generarse token de recuperación"
     * 
     * PROPÓSITO:
     * Verificar que un empleado desvinculado NO puede recuperar su contraseña.
     * 
     * TÉCNICA: POLLING CON REINTENTOS
     * Intentamos usar un token de recuperación generado con JwtTestUtils.
     * Si el usuario está deshabilitado, el reset debe fallar.
     * 
     * ESTRATEGIA DE VERIFICACIÓN:
     * 1. Generar un token de recuperación válido con JwtTestUtils
     * 2. Intentar establecer una nueva contraseña usando el token
     * 3. Verificar que el reset falla con 401 o 403
     * 
     * RESULTADO ESPERADO:
     * Eventualmente (después de que auth-service procese el evento):
     * - Código: 401 Unauthorized o 403 Forbidden
     * - El sistema rechaza el reset porque el usuario está inhabilitado
     * 
     * JUSTIFICACIÓN:
     * Un usuario desvinculado no debe poder recuperar su contraseña,
     * incluso si tiene un token de recuperación válido.
     * 
     * TIMEOUT: 10 intentos × 2s = 20s
     */
    @Then("eventualmente no debe generarse token de recuperación")
    public void verificarNoTokenRecuperacion() {
        String email = ctx.getEmpleadoEmail();
        assertThat("No se guardó el email del empleado", email, notNullValue());

        // Esperar un tiempo razonable para que el sistema procese
        // Si el usuario está deshabilitado, no debería poder recuperar contraseña
        WaitUtils.waitUntil(() -> {
            // Intentar usar un token de recuperación generado
            String tokenRecuperacion = com.empresa.e2e.support.JwtTestUtils.crearTokenRecuperacion(email);
            
            Map<String, String> resetBody = new HashMap<>();
            resetBody.put("token", tokenRecuperacion);
            resetBody.put("nueva_contrasena", "NuevaPassword123!");
            
            Response response = request().body(resetBody).post("/auth/reset-password");
            
            // Si el usuario está deshabilitado, el reset debe fallar (401 o 403)
            return response.statusCode() == 401 || response.statusCode() == 403;
        }, 10, 2000);
    }
}
