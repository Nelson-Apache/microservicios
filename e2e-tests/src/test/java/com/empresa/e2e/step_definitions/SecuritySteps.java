package com.empresa.e2e.step_definitions;

import com.empresa.e2e.support.ConfiguracionBase;
import com.empresa.e2e.support.TestContext;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;

import java.util.HashMap;
import java.util.Map;

import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.equalTo;

/**
 * Step definitions para escenarios de SEGURIDAD y CONTROL DE ACCESO (RBAC).
 * 
 * PROPÓSITO:
 * Verificar que el sistema implementa correctamente:
 * - Autenticación JWT (401 sin token o con token inválido)
 * - Autorización basada en roles (403 cuando el rol no tiene permisos)
 * 
 * ROLES DEL SISTEMA:
 * - ADMIN: Permisos completos (crear, leer, actualizar, eliminar)
 * - USER: Permisos limitados (solo lectura)
 * 
 * ESCENARIOS CUBIERTOS:
 * 1. Acceso sin token → 401 Unauthorized
 * 2. Acceso con token inválido → 401 Unauthorized
 * 3. Usuario USER intenta eliminar → 403 Forbidden
 * 4. Usuario ADMIN puede eliminar → 204 No Content
 */
public class SecuritySteps extends ConfiguracionBase {

    public SecuritySteps(TestContext ctx) {
        super(ctx);
    }

    /**
     * Paso: "Dado que el sistema está desplegado"
     * 
     * PROPÓSITO:
     * Verificar que el API Gateway está accesible antes de ejecutar el escenario.
     * 
     * IMPORTANTE:
     * No guarda la respuesta en ctx.ultimaRespuesta porque los Antecedentes
     * no deben pisar la respuesta del escenario principal.
     * 
     * VERIFICACIÓN:
     * - GET /health debe retornar código < 500
     * - Si falla, el escenario se detiene inmediatamente
     */
    @Given("que el sistema está desplegado")
    public void sistemaDeplegado() {
        // Solo verifica que el gateway responde — no guarda respuesta en ctx
        // porque los Antecedentes no deben pisar la respuesta del escenario
        request().get("/health").then().statusCode(org.hamcrest.Matchers.lessThan(500));
    }

    /**
     * Paso: "Cuando consulto la lista de empleados sin token de autenticación"
     * 
     * PROPÓSITO:
     * Verificar que el sistema rechaza peticiones sin autenticación.
     * 
     * TÉCNICA:
     * Usa request() en lugar de requestAutenticado() para NO incluir
     * el header Authorization.
     * 
     * RESULTADO ESPERADO:
     * - Código: 401 Unauthorized
     * - Mensaje: "No se proporcionó token de autenticación" o similar
     */
    @When("consulto la lista de empleados sin token de autenticación")
    public void consultarEmpleadosSinToken() {
        // Petición deliberadamente sin header Authorization
        ctx.setUltimaRespuesta(request().get("/empleados"));
    }

    /**
     * Paso: "Cuando consulto la lista de empleados con un token inválido"
     * 
     * PROPÓSITO:
     * Verificar que el sistema valida correctamente la firma del token JWT.
     * 
     * TÉCNICA:
     * Envía un token JWT con formato válido pero firma incorrecta.
     * 
     * RESULTADO ESPERADO:
     * - Código: 401 Unauthorized
     * - Mensaje: "Token inválido" o "Firma inválida"
     */
    @When("consulto la lista de empleados con un token inválido")
    public void consultarEmpleadosConTokenInvalido() {
        ctx.setUltimaRespuesta(
            request()
                .header("Authorization", "Bearer token.invalido.firmado")
                .get("/empleados")
        );
    }

    /**
     * Paso: "Dado que estoy autenticado como {string}"
     * 
     * PROPÓSITO:
     * Autenticar al usuario con el rol especificado y guardar el token JWT.
     * 
     * PARÁMETROS:
     * - rol: "ADMIN" o "USER"
     * 
     * FLUJO:
     * 1. Seleccionar credenciales según el rol (desde TestContext)
     * 2. Hacer login vía POST /auth/login
     * 3. Extraer el token JWT de la respuesta
     * 4. Guardar el token en ctx.tokenJwt
     * 
     * USO EN ESCENARIOS:
     * Dado que estoy autenticado como "ADMIN"
     * Dado que estoy autenticado como "USER"
     * 
     * REUTILIZACIÓN:
     * Este paso se usa en múltiples escenarios (onboarding, offboarding, security)
     * para establecer el contexto de autenticación.
     */
    @Given("que estoy autenticado como {string}")
    public void autenticarComoRol(String rol) {
        Map<String, String> body = new HashMap<>();
        
        // Seleccionar credenciales según el rol
        switch (rol.toUpperCase()) {
            case "ADMIN" -> {
                body.put("nombre_usuario", ctx.adminUser);
                body.put("contrasena", ctx.adminPassword);
            }
            case "USER" -> {
                body.put("nombre_usuario", ctx.userUser);
                body.put("contrasena", ctx.userPassword);
            }
            default -> throw new IllegalArgumentException("Rol no reconocido: " + rol);
        }
        
        // Hacer login
        io.restassured.response.Response response = request().body(body).post("/auth/login");
        assertThat("Login falló para rol " + rol, response.statusCode(), equalTo(200));
        
        // Guardar token en el contexto
        ctx.setTokenJwt(response.jsonPath().getString("access_token"));
    }

    /**
     * Paso: "Cuando intento eliminar un empleado"
     * 
     * PROPÓSITO:
     * Verificar que el sistema rechaza la operación si el usuario no tiene permisos.
     * 
     * TÉCNICA:
     * Usa un ID arbitrario (1) porque el 403 se produce ANTES de buscar el recurso.
     * El API Gateway verifica el rol antes de reenviar la petición al servicio.
     * 
     * RESULTADO ESPERADO (con rol USER):
     * - Código: 403 Forbidden
     * - Mensaje: "No tiene permisos para realizar esta acción"
     */
    @When("intento eliminar un empleado")
    public void intentarEliminarEmpleado() {
        // Usa un ID arbitrario — el 403 se produce antes de buscar el recurso
        ctx.setUltimaRespuesta(requestAutenticado().delete("/empleados/1"));
    }

    /**
     * Paso: "Dado existe un empleado creado para eliminar"
     * 
     * PROPÓSITO:
     * Crear un empleado temporal para probar la eliminación exitosa.
     * 
     * TÉCNICA:
     * - ID único con timestamp para evitar colisiones
     * - Email único para evitar duplicados
     * - Se guarda el ID en ctx.empleadoId para eliminarlo después
     * 
     * PREREQUISITO:
     * El usuario debe estar autenticado como ADMIN (se hace en Antecedentes)
     */
    @Given("existe un empleado creado para eliminar")
    public void crearEmpleadoParaEliminar() {
        int empleadoId = (int) (System.currentTimeMillis() % 1000000);
        
        Map<String, Object> body = new HashMap<>();
        body.put("id", empleadoId);
        body.put("nombre", "Empleado Temporal");
        body.put("email", "temporal_" + System.currentTimeMillis() + "@empresa.com");
        body.put("cargo", "Temporal");
        // departamento_id es opcional

        io.restassured.response.Response response = requestAutenticado()
                .body(body)
                .post("/empleados");
        assertThat("No se pudo crear el empleado de prueba", response.statusCode(), equalTo(201));
        
        // Guardar ID para eliminarlo después
        ctx.setEmpleadoId(empleadoId);
    }

    /**
     * Paso: "Cuando elimino un empleado existente"
     * 
     * PROPÓSITO:
     * Eliminar el empleado creado en el paso anterior.
     * 
     * PREREQUISITO:
     * - ctx.empleadoId debe estar configurado
     * - El usuario debe estar autenticado como ADMIN
     * 
     * RESULTADO ESPERADO:
     * - Código: 204 No Content (eliminación exitosa)
     */
    @When("elimino un empleado existente")
    public void eliminarEmpleadoExistente() {
        ctx.setUltimaRespuesta(requestAutenticado().delete("/empleados/" + ctx.getEmpleadoId()));
    }
}
