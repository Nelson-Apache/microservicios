package com.empresa.e2e.step_definitions;

import com.empresa.e2e.support.ConfiguracionBase;
import com.empresa.e2e.support.TestContext;
import com.empresa.e2e.support.WaitUtils;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import io.restassured.response.Response;

import java.util.HashMap;
import java.util.Map;

import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.*;

/**
 * Step definitions para escenarios de ONBOARDING de empleados.
 * 
 * FLUJO DE ONBOARDING:
 * 1. ADMIN crea un empleado en empleados-service
 * 2. empleados-service publica evento "empleado.creado" en RabbitMQ
 * 3. auth-service consume el evento y crea credenciales (asincrónico)
 * 4. notificaciones-service consume el evento y envía notificación (asincrónico)
 * 
 * DESAFÍOS:
 * - Eventos asincrónicos: No podemos verificar inmediatamente
 * - Consistencia eventual: Usamos polling con WaitUtils
 * - Aislamiento de datos: IDs únicos con timestamp
 * 
 * ESCENARIOS CUBIERTOS:
 * 1. Registro exitoso → verificar credenciales creadas
 * 2. Registro exitoso → verificar notificación de bienvenida
 * 3. Flujo completo: Registro → Establecer contraseña → Login
 * 4. Registro con datos inválidos → error 400
 */
public class OnboardingSteps extends ConfiguracionBase {

    public OnboardingSteps(TestContext ctx) {
        super(ctx);
    }

    /**
     * Paso: "Cuando registro un empleado con datos válidos"
     * 
     * PROPÓSITO:
     * Crear un empleado en el sistema y guardar sus datos en el contexto
     * para verificaciones posteriores.
     * 
     * TÉCNICA: IDs ÚNICOS CON TIMESTAMP
     * - empleadoId: timestamp % 1000000 (ID único de 6 dígitos)
     * - email: empleado_<timestamp>@empresa.com
     * 
     * VENTAJAS:
     * ✅ Cada escenario crea sus propios datos únicos
     * ✅ No hay colisiones entre ejecuciones paralelas o consecutivas
     * ✅ No requiere limpieza de base de datos entre escenarios
     * ✅ Los datos quedan en el sistema para auditoría/debugging
     * 
     * DATOS GUARDADOS EN CONTEXTO:
     * - ctx.empleadoEmail: Para verificar creación de credenciales
     * - ctx.empleadoId: Para consultar notificaciones
     */
    @When("registro un empleado con datos válidos")
    public void registrarEmpleado() {
        // Generar ID único basado en timestamp
        String timestamp = String.valueOf(System.currentTimeMillis());
        String email = "empleado_" + timestamp + "@empresa.com";
        int empleadoId = (int) (System.currentTimeMillis() % 1000000); // ID único de 6 dígitos
        
        // Construir el cuerpo de la petición
        Map<String, Object> body = new HashMap<>();
        body.put("id", empleadoId);
        body.put("nombre", "Empleado Test " + timestamp);
        body.put("email", email);
        body.put("cargo", "Desarrollador");
        // departamento_id es opcional, no lo incluimos

        // Hacer la petición POST /empleados
        ctx.setUltimaRespuesta(requestAutenticado().body(body).post("/empleados"));
        
        // Si la creación fue exitosa, guardar datos en el contexto
        if (ctx.getUltimaRespuesta().statusCode() == 201) {
            ctx.setEmpleadoEmail(email);
            ctx.setEmpleadoId(empleadoId);
        }
    }

    /**
     * Paso: "Entonces eventualmente el usuario debe existir en auth-service"
     * 
     * PROPÓSITO:
     * Verificar que el evento "empleado.creado" fue procesado por auth-service
     * y se crearon las credenciales del empleado.
     * 
     * TÉCNICA: POLLING CON REINTENTOS
     * No podemos verificar inmediatamente porque el evento es asincrónico.
     * Usamos WaitUtils.waitUntil() para consultar repetidamente.
     * 
     * ESTRATEGIA DE VERIFICACIÓN:
     * Intentamos hacer login con el email del empleado.
     * 
     * INTERPRETACIÓN DE RESPUESTAS:
     * - 401 + "Usuario inhabilitado" → ✅ Usuario existe (sin contraseña aún)
     * - 401 + "Credenciales inválidas" → ✅ Usuario existe (con contraseña)
     * - 401 + otro mensaje → ❌ Usuario no existe
     * - Otro código → ❌ Error inesperado
     * 
     * TIMEOUT: 10 intentos × 2 segundos = 20 segundos
     */
    @Then("eventualmente el usuario debe existir en auth-service")
    public void verificarUsuarioCreado() {
        String email = ctx.getEmpleadoEmail();
        assertThat("No se guardó el email del empleado", email, notNullValue());

        WaitUtils.waitUntil(() -> {
            // Intentar login con el email creado
            Map<String, String> loginBody = new HashMap<>();
            loginBody.put("nombre_usuario", email);
            loginBody.put("contrasena", "password_temporal_para_verificacion");

            Response response = request().body(loginBody).post("/auth/login");
            
            // El usuario existe si:
            // - Da 401 con mensaje "Usuario inhabilitado" (usuario creado pero sin contraseña)
            // - Da 401 con mensaje "Credenciales inválidas" (usuario existe con contraseña)
            // El usuario NO existe si da 401 con otro mensaje o error de conexión
            
            if (response.statusCode() == 401) {
                String detalle = response.jsonPath().getString("detail");
                // Si el mensaje menciona "inhabilitado" o "Credenciales", el usuario existe
                return detalle != null && 
                       (detalle.contains("inhabilitado") || detalle.contains("Credenciales"));
            }
            
            return false;
        }, 10, 2000);
    }

    /**
     * Paso: "Cuando registro un empleado" (alias simplificado)
     * 
     * Reutiliza la lógica de registrarEmpleado().
     * Se usa en escenarios donde el paso es más corto.
     */
    @When("registro un empleado")
    public void registrarEmpleadoSimple() {
        registrarEmpleado(); // Reutiliza la lógica existente
    }

    /**
     * Paso: "Y establece su contraseña"
     * 
     * PROPÓSITO:
     * Simular el flujo completo de establecimiento de contraseña después del onboarding.
     * 
     * FLUJO REAL (PRODUCCIÓN):
     * 1. Usuario recibe email con link de recuperación
     * 2. Link contiene token JWT firmado
     * 3. Usuario usa el token para establecer su contraseña
     * 
     * FLUJO EN E2E TEST:
     * 1. Esperamos a que el usuario exista en auth-service (polling)
     * 2. Generamos el token JWT usando JwtTestUtils (mismo secreto que auth-service)
     * 3. Usamos el token para establecer la contraseña vía POST /auth/reset-password
     * 
     * JUSTIFICACIÓN:
     * ✅ Es aceptable generar el JWT en tests (controlamos el entorno)
     * ✅ Evita dependencias externas (parsear logs, crear endpoints de test)
     * ✅ Prueba la validación real del JWT
     * 
     * DATOS GUARDADOS:
     * - ctx.empleadoPassword: Para hacer login posteriormente
     */
    @When("establece su contraseña")
    public void establecerContrasena() {
        String email = ctx.getEmpleadoEmail();
        assertThat("No se guardó el email del empleado", email, notNullValue());

        // Esperar a que el usuario exista en auth-service y establecer la contraseña
        // Como el usuario se crea asincrónicamente vía RabbitMQ, necesitamos polling
        final Response[] resetResponseFinal = new Response[1];
        
        WaitUtils.waitUntil(() -> {
            // Generar token válido usando JwtTestUtils (simula el link enviado por email)
            String token = com.empresa.e2e.support.JwtTestUtils.crearTokenRecuperacion(email);
            
            // Intentar establecer la contraseña
            Map<String, String> resetBody = new HashMap<>();
            resetBody.put("token", token);
            resetBody.put("nueva_contrasena", "Password123!");
            
            Response resetResponse = request().body(resetBody).post("/auth/reset-password");
            resetResponseFinal[0] = resetResponse;
            
            // Si devuelve 200, el usuario existe y se actualizó la contraseña
            return resetResponse.statusCode() == 200;
        }, 10, 2000);

        Response finalResp = resetResponseFinal[0];
        if (finalResp != null && finalResp.statusCode() != 200) {
            String errorDetail = finalResp.jsonPath().getString("detail");
            System.out.println("Error al establecer contraseña: " + errorDetail);
            System.out.println("Status code: " + finalResp.statusCode());
            System.out.println("Response body: " + finalResp.getBody().asString());
        }
        
        assertThat("No se pudo establecer la contraseña", finalResp != null && finalResp.statusCode() == 200, equalTo(true));
        
        // Guardar la contraseña en el contexto para el login posterior
        ctx.setEmpleadoPassword("Password123!");
    }

    /**
     * Paso: "Y hace login"
     * 
     * PROPÓSITO:
     * Verificar que el empleado puede autenticarse con las credenciales establecidas.
     * 
     * PREREQUISITOS:
     * - ctx.empleadoEmail debe estar configurado
     * - ctx.empleadoPassword debe estar configurado
     * 
     * VERIFICACIÓN:
     * La respuesta se guarda en ctx.ultimaRespuesta para que el paso
     * "Entonces la respuesta debe tener código 200" pueda verificarla.
     */
    @When("hace login")
    public void hacerLogin() {
        String email = ctx.getEmpleadoEmail();
        String password = ctx.getEmpleadoPassword();
        
        assertThat("No se guardó el email del empleado", email, notNullValue());
        assertThat("No se guardó la contraseña del empleado", password, notNullValue());

        Map<String, String> body = new HashMap<>();
        body.put("nombre_usuario", email);
        body.put("contrasena", password);

        ctx.setUltimaRespuesta(request().body(body).post("/auth/login"));
    }

    /**
     * Paso: "Entonces eventualmente debe existir una notificación de bienvenida"
     * 
     * PROPÓSITO:
     * Verificar que el evento "empleado.creado" fue procesado por notificaciones-service
     * y se generó una notificación de tipo BIENVENIDA.
     * 
     * TÉCNICA: POLLING CON REINTENTOS
     * Consultamos repetidamente GET /notificaciones/{empleadoId} hasta que:
     * - Existe al menos una notificación con tipo "BIENVENIDA" → ✅ éxito
     * - Se agota el timeout (20 segundos) → ❌ fallo
     * 
     * ENDPOINT:
     * GET /notificaciones/{empleadoId}
     * Retorna: [ { "tipo": "BIENVENIDA", ... }, ... ]
     * 
     * TIMEOUT: 10 intentos × 2 segundos = 20 segundos
     */
    @Then("eventualmente debe existir una notificación de bienvenida")
    public void verificarNotificacionBienvenida() {
        String email = ctx.getEmpleadoEmail();
        assertThat("No se guardó el email del empleado", email, notNullValue());

        WaitUtils.waitUntil(() -> {
            // Consultar el endpoint de notificaciones
            // Nota: necesitamos el empleadoId, que está en la respuesta del POST /empleados
            Integer empleadoId = ctx.getEmpleadoId();
            if (empleadoId == null) {
                // Intentar extraerlo de la última respuesta si aún está disponible
                try {
                    empleadoId = ctx.getUltimaRespuesta().jsonPath().getInt("id");
                    ctx.setEmpleadoId(empleadoId);
                } catch (Exception e) {
                    return false;
                }
            }

            Response response = requestAutenticado().get("/notificaciones/" + empleadoId);
            
            if (response.statusCode() == 200) {
                // Verificar que existe al menos una notificación de tipo BIENVENIDA
                try {
                    java.util.List<Map<String, Object>> notificaciones = response.jsonPath().getList("$");
                    return notificaciones != null && notificaciones.stream()
                            .anyMatch(n -> "BIENVENIDA".equals(n.get("tipo")));
                } catch (Exception e) {
                    return false;
                }
            }
            
            return false;
        }, 10, 2000);
    }

    /**
     * Paso: "Cuando registro un empleado con departamento inexistente"
     * 
     * PROPÓSITO:
     * Verificar que el sistema valida correctamente los datos de entrada
     * y retorna error 400 cuando el departamento no existe.
     * 
     * VALIDACIÓN ESPERADA:
     * empleados-service debe consultar departamentos-service para verificar
     * que el departamento existe antes de crear el empleado.
     * 
     * RESULTADO ESPERADO:
     * - Código de respuesta: 400 Bad Request
     * - Mensaje de error descriptivo
     */
    @When("registro un empleado con departamento inexistente")
    public void registrarEmpleadoConDepartamentoInexistente() {
        String timestamp = String.valueOf(System.currentTimeMillis());
        String email = "empleado_invalido_" + timestamp + "@empresa.com";
        int empleadoId = (int) (System.currentTimeMillis() % 1000000);
        
        Map<String, Object> body = new HashMap<>();
        body.put("id", empleadoId);
        body.put("nombre", "Empleado Inválido " + timestamp);
        body.put("email", email);
        body.put("cargo", "Desarrollador");
        body.put("departamento_id", 999999); // ID de departamento que no existe

        ctx.setUltimaRespuesta(requestAutenticado().body(body).post("/empleados"));
    }
}
