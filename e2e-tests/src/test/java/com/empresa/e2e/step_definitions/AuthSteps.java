package com.empresa.e2e.step_definitions;

import com.empresa.e2e.support.ConfiguracionBase;
import com.empresa.e2e.support.TestContext;
import io.cucumber.java.en.*;
import io.restassured.response.Response;

import java.util.HashMap;
import java.util.Map;

import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.*;

/**
 * Step definitions para escenarios de AUTENTICACIÓN.
 * 
 * PROPÓSITO:
 * - Verificar el flujo de login (exitoso y fallido)
 * - Verificar el flujo de recuperación de contraseña
 * - Proporcionar pasos reutilizables para verificar respuestas HTTP
 * 
 * PASOS REUTILIZABLES:
 * Muchos pasos de esta clase se reutilizan en otros escenarios:
 * - "la respuesta debe tener código {int}" → usado en TODOS los escenarios
 * - "estoy autenticado como usuario" → usado en empleados.feature
 * 
 * ESCENARIOS CUBIERTOS:
 * 1. Login exitoso con credenciales válidas
 * 2. Login fallido con contraseña incorrecta
 * 3. Login fallido con usuario inexistente
 * 4. Solicitud de recuperación de contraseña
 * 5. Recuperación con email inexistente (respuesta genérica por seguridad)
 */
public class AuthSteps extends ConfiguracionBase {

    public AuthSteps(TestContext ctx) {
        super(ctx);
    }

    /**
     * Paso: "Dado el servicio de autenticación está disponible"
     * 
     * PROPÓSITO:
     * Verificar que el API Gateway está accesible antes de ejecutar el escenario.
     * 
     * TÉCNICA:
     * - GET /health debe retornar código < 500
     * - Si falla, el escenario se detiene inmediatamente
     * 
     * USO:
     * Se usa en los Antecedentes de auth.feature para verificar
     * que el sistema está operativo antes de probar autenticación.
     */
    @Given("el servicio de autenticación está disponible")
    public void servicioDisponible() {
        ctx.setUltimaRespuesta(request().get("/health"));
        assertThat("El gateway no responde", ctx.getUltimaRespuesta().statusCode(), lessThan(500));
    }

    /**
     * Paso: "Dado estoy autenticado como usuario"
     * 
     * PROPÓSITO:
     * Autenticar al usuario con rol USER y guardar el token JWT.
     * 
     * DIFERENCIA CON "que estoy autenticado como {string}":
     * - Este paso es específico para el rol USER (sin parámetro)
     * - Se usa en empleados.feature donde siempre se necesita USER
     * - El paso parametrizado se usa cuando el rol varía (ADMIN/USER)
     * 
     * FLUJO:
     * 1. Obtener credenciales de USER desde TestContext
     * 2. Hacer login vía POST /auth/login
     * 3. Verificar que el login fue exitoso (200)
     * 4. Guardar el token JWT en ctx.tokenJwt
     */
    @Given("estoy autenticado como usuario")
    public void autenticarUsuario() {
        Map<String, String> body = new HashMap<>();
        body.put("nombre_usuario", ctx.userUser);
        body.put("contrasena", ctx.userPassword);

        Response response = request().body(body).post("/auth/login");
        assertThat("Login de usuario falló", response.statusCode(), equalTo(200));
        ctx.setTokenJwt(response.jsonPath().getString("access_token"));
    }

    /**
     * Paso: "Cuando inicio sesión con usuario {string} y contraseña {string}"
     * 
     * PROPÓSITO:
     * Intentar hacer login con credenciales específicas (pueden ser válidas o inválidas).
     * 
     * PARÁMETROS:
     * - usuario: Nombre de usuario o email
     * - contrasena: Contraseña (puede ser incorrecta para probar fallos)
     * 
     * USO EN ESCENARIOS:
     * Cuando inicio sesión con usuario "admin" y contraseña "admin123"
     * Cuando inicio sesión con usuario "admin" y contraseña "wrongpassword"
     * Cuando inicio sesión con usuario "noexiste" y contraseña "cualquiera"
     * 
     * NOTA:
     * No verifica el resultado aquí, solo hace la petición.
     * La verificación se hace en pasos "Entonces".
     */
    @When("inicio sesión con usuario {string} y contraseña {string}")
    public void iniciarSesion(String usuario, String contrasena) {
        Map<String, String> body = new HashMap<>();
        body.put("nombre_usuario", usuario);
        body.put("contrasena", contrasena);

        ctx.setUltimaRespuesta(request().body(body).post("/auth/login"));
    }

    /**
     * Paso: "Cuando solicito recuperación de contraseña con email {string}"
     * 
     * PROPÓSITO:
     * Solicitar recuperación de contraseña para un email específico.
     * 
     * COMPORTAMIENTO ESPERADO (SEGURIDAD):
     * El sistema debe retornar SIEMPRE el mismo mensaje genérico,
     * independientemente de si el email existe o no.
     * Esto evita la enumeración de usuarios.
     * 
     * MENSAJE GENÉRICO:
     * "Si el email está registrado, recibirás un correo con instrucciones"
     * 
     * USO EN ESCENARIOS:
     * Cuando solicito recuperación de contraseña con email "admin@empresa.com"
     * Cuando solicito recuperación de contraseña con email "noexiste@empresa.com"
     * 
     * AMBOS CASOS DEBEN RETORNAR:
     * - Código: 200 OK
     * - Mensaje: Genérico (no revela si el email existe)
     */
    @When("solicito recuperación de contraseña con email {string}")
    public void solicitarRecuperacion(String email) {
        Map<String, String> body = new HashMap<>();
        body.put("email", email);

        ctx.setUltimaRespuesta(request().body(body).post("/auth/recover-password"));
    }

    /**
     * Paso: "Entonces la respuesta debe tener código {int}"
     * 
     * PROPÓSITO:
     * Verificar el código de estado HTTP de la última respuesta.
     * 
     * PARÁMETRO:
     * - codigoEsperado: Código HTTP esperado (200, 201, 400, 401, 403, 404, etc.)
     * 
     * REUTILIZACIÓN:
     * Este es el paso MÁS REUTILIZADO en toda la suite de pruebas.
     * Se usa en TODOS los escenarios para verificar el resultado de las peticiones.
     * 
     * EJEMPLOS DE USO:
     * Entonces la respuesta debe tener código 200  (éxito)
     * Entonces la respuesta debe tener código 201  (creado)
     * Entonces la respuesta debe tener código 400  (datos inválidos)
     * Entonces la respuesta debe tener código 401  (no autenticado)
     * Entonces la respuesta debe tener código 403  (sin permisos)
     * Entonces la respuesta debe tener código 404  (no encontrado)
     */
    @Then("la respuesta debe tener código {int}")
    public void verificarCodigo(int codigoEsperado) {
        assertThat(ctx.getUltimaRespuesta().statusCode(), equalTo(codigoEsperado));
    }

    /**
     * Paso: "Entonces la respuesta debe contener un token de acceso"
     * 
     * PROPÓSITO:
     * Verificar que la respuesta de login contiene un token JWT válido.
     * 
     * VERIFICACIONES:
     * 1. El campo "access_token" existe en la respuesta
     * 2. El token no es null
     * 3. El token no está vacío
     * 
     * EFECTO SECUNDARIO:
     * Guarda el token en ctx.tokenJwt para usarlo en peticiones posteriores.
     * 
     * USO:
     * Se usa después de un login exitoso para extraer y guardar el token.
     */
    @Then("la respuesta debe contener un token de acceso")
    public void verificarToken() {
        String token = ctx.getUltimaRespuesta().jsonPath().getString("access_token");
        assertThat("No se recibió access_token", token, notNullValue());
        assertThat("El token está vacío", token, not(emptyString()));
        ctx.setTokenJwt(token);
    }

    /**
     * Paso: "Entonces el token debe tener tipo {string}"
     * 
     * PROPÓSITO:
     * Verificar el tipo de token JWT (normalmente "bearer").
     * 
     * PARÁMETRO:
     * - tipo: Tipo de token esperado (ej: "bearer")
     * 
     * ESTRUCTURA DE RESPUESTA DE LOGIN:
     * {
     *   "access_token": "eyJ...",
     *   "token_type": "bearer",
     *   "rol": "ADMIN"
     * }
     * 
     * USO:
     * Entonces el token debe tener tipo "bearer"
     */
    @Then("el token debe tener tipo {string}")
    public void verificarTipoToken(String tipo) {
        String tokenType = ctx.getUltimaRespuesta().jsonPath().getString("token_type");
        assertThat(tokenType, equalToIgnoringCase(tipo));
    }

    /**
     * Paso: "Entonces el rol del usuario debe ser {string}"
     * 
     * PROPÓSITO:
     * Verificar que el rol del usuario en la respuesta de login es correcto.
     * 
     * PARÁMETRO:
     * - rolEsperado: Rol esperado ("ADMIN" o "USER")
     * 
     * ESTRUCTURA DE RESPUESTA DE LOGIN:
     * {
     *   "access_token": "eyJ...",
     *   "token_type": "bearer",
     *   "rol": "ADMIN"
     * }
     * 
     * USO:
     * Entonces el rol del usuario debe ser "ADMIN"
     * Entonces el rol del usuario debe ser "USER"
     */
    @Then("el rol del usuario debe ser {string}")
    public void verificarRol(String rolEsperado) {
        String rol = ctx.getUltimaRespuesta().jsonPath().getString("rol");
        assertThat(rol, equalTo(rolEsperado));
    }

    /**
     * Paso: "Entonces la respuesta debe contener el mensaje de recuperación"
     * 
     * PROPÓSITO:
     * Verificar que la respuesta de recuperación de contraseña contiene
     * el mensaje genérico esperado.
     * 
     * MENSAJE ESPERADO:
     * "Si el email está registrado, recibirás un correo con instrucciones"
     * 
     * SEGURIDAD:
     * Este mensaje genérico evita la enumeración de usuarios.
     * No revela si el email existe o no en el sistema.
     * 
     * VERIFICACIÓN:
     * - El campo "mensaje" existe
     * - El mensaje contiene la frase "Si el email está registrado"
     */
    @Then("la respuesta debe contener el mensaje de recuperación")
    public void verificarMensajeRecuperacion() {
        String mensaje = ctx.getUltimaRespuesta().jsonPath().getString("mensaje");
        assertThat(mensaje, notNullValue());
        assertThat(mensaje, containsString("Si el email está registrado"));
    }
}
