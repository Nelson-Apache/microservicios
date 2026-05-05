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
 * Step definitions para escenarios de GESTIÓN DE EMPLEADOS (CRUD).
 * 
 * PROPÓSITO:
 * Verificar las operaciones básicas de consulta y gestión de empleados:
 * - Consultar lista de empleados (GET /empleados)
 * - Consultar empleado por ID (GET /empleados/{id})
 * - Crear empleado (POST /empleados)
 * - Eliminar empleado (DELETE /empleados/{id})
 * 
 * ESCENARIOS CUBIERTOS:
 * 1. Consultar lista de empleados (requiere autenticación)
 * 2. Consultar empleado inexistente → 404 Not Found
 * 
 * NOTA:
 * Los pasos de creación y eliminación se usan principalmente en otros features
 * (onboarding, offboarding, security) donde se necesita setup de datos.
 */
public class EmpleadosSteps extends ConfiguracionBase {

    public EmpleadosSteps(TestContext ctx) {
        super(ctx);
    }

    /**
     * Paso: "Dado estoy autenticado como administrador"
     * 
     * PROPÓSITO:
     * Autenticar al usuario con rol ADMIN y guardar el token JWT.
     * 
     * DIFERENCIA CON OTROS PASOS DE AUTENTICACIÓN:
     * - "estoy autenticado como administrador" → Específico para ADMIN (sin parámetro)
     * - "estoy autenticado como usuario" → Específico para USER (sin parámetro)
     * - "que estoy autenticado como {string}" → Parametrizado (ADMIN/USER)
     * 
     * USO:
     * Se usa en empleados.feature donde siempre se necesita rol ADMIN.
     * 
     * FLUJO:
     * 1. Obtener credenciales de ADMIN desde TestContext
     * 2. Hacer login vía POST /auth/login
     * 3. Verificar que el login fue exitoso (200)
     * 4. Guardar el token JWT en ctx.tokenJwt
     */
    @Given("estoy autenticado como administrador")
    public void autenticarAdmin() {
        Map<String, String> body = new HashMap<>();
        body.put("nombre_usuario", ctx.adminUser);
        body.put("contrasena", ctx.adminPassword);

        Response response = request().body(body).post("/auth/login");
        assertThat("Login de admin falló", response.statusCode(), equalTo(200));
        ctx.setTokenJwt(response.jsonPath().getString("access_token"));
    }

    /**
     * Paso: "Cuando creo un empleado con nombre {string}, email {string} y departamento {int}"
     * 
     * PROPÓSITO:
     * Crear un empleado con datos específicos proporcionados como parámetros.
     * 
     * PARÁMETROS:
     * - nombre: Nombre completo del empleado
     * - email: Email del empleado (debe ser único)
     * - departamentoId: ID del departamento al que pertenece
     * 
     * ENDPOINT:
     * POST /empleados
     * Body: { "nombre": "...", "email": "...", "departamento_id": ... }
     * 
     * PREREQUISITO:
     * El usuario debe estar autenticado (token en ctx.tokenJwt)
     * 
     * RESULTADO ESPERADO:
     * - Código: 201 Created (si es exitoso)
     * - Código: 400 Bad Request (si el departamento no existe o datos inválidos)
     * 
     * USO:
     * Este paso se usa cuando se necesitan datos específicos del empleado.
     * Para datos generados automáticamente, ver OnboardingSteps.registrarEmpleado()
     */
    @When("creo un empleado con nombre {string}, email {string} y departamento {int}")
    public void crearEmpleado(String nombre, String email, int departamentoId) {
        Map<String, Object> body = new HashMap<>();
        body.put("nombre", nombre);
        body.put("email", email);
        body.put("departamento_id", departamentoId);

        ctx.setUltimaRespuesta(requestAutenticado().body(body).post("/empleados"));
    }

    /**
     * Paso: "Cuando consulto la lista de empleados"
     * 
     * PROPÓSITO:
     * Obtener la lista paginada de todos los empleados del sistema.
     * 
     * ENDPOINT:
     * GET /empleados
     * 
     * PREREQUISITO:
     * El usuario debe estar autenticado (token en ctx.tokenJwt)
     * 
     * ESTRUCTURA DE RESPUESTA:
     * {
     *   "total": 100,
     *   "pagina": 1,
     *   "por_pagina": 10,
     *   "total_paginas": 10,
     *   "empleados": [
     *     { "id": 1, "nombre": "Juan", "email": "juan@empresa.com", ... },
     *     ...
     *   ]
     * }
     * 
     * RESULTADO ESPERADO:
     * - Código: 200 OK (si está autenticado)
     * - Código: 401 Unauthorized (si no está autenticado)
     * 
     * USO:
     * Se usa en empleados.feature para verificar que el endpoint funciona
     * y requiere autenticación.
     */
    @When("consulto la lista de empleados")
    public void consultarEmpleados() {
        ctx.setUltimaRespuesta(requestAutenticado().get("/empleados"));
    }

    /**
     * Paso: "Cuando consulto el empleado con id {int}"
     * 
     * PROPÓSITO:
     * Obtener los detalles de un empleado específico por su ID.
     * 
     * PARÁMETRO:
     * - id: ID del empleado a consultar
     * 
     * ENDPOINT:
     * GET /empleados/{id}
     * 
     * PREREQUISITO:
     * El usuario debe estar autenticado (token en ctx.tokenJwt)
     * 
     * RESULTADO ESPERADO:
     * - Código: 200 OK (si el empleado existe)
     * - Código: 404 Not Found (si el empleado no existe)
     * - Código: 401 Unauthorized (si no está autenticado)
     * 
     * USO:
     * Se usa en empleados.feature para verificar el manejo de errores 404
     * cuando se consulta un empleado inexistente.
     */
    @When("consulto el empleado con id {int}")
    public void consultarEmpleadoPorId(int id) {
        ctx.setUltimaRespuesta(requestAutenticado().get("/empleados/" + id));
    }

    /**
     * Paso: "Cuando elimino el empleado con id {int}"
     * 
     * PROPÓSITO:
     * Eliminar un empleado del sistema por su ID.
     * 
     * PARÁMETRO:
     * - id: ID del empleado a eliminar
     * 
     * ENDPOINT:
     * DELETE /empleados/{id}
     * 
     * PREREQUISITO:
     * El usuario debe estar autenticado con rol ADMIN (token en ctx.tokenJwt)
     * 
     * RESULTADO ESPERADO:
     * - Código: 204 No Content (si se eliminó exitosamente)
     * - Código: 404 Not Found (si el empleado no existe)
     * - Código: 403 Forbidden (si el usuario no tiene permisos)
     * - Código: 401 Unauthorized (si no está autenticado)
     * 
     * EFECTO SECUNDARIO:
     * Al eliminar un empleado, se publica el evento "empleado.eliminado" en RabbitMQ,
     * que dispara acciones asincrónicas:
     * - auth-service deshabilita las credenciales del empleado
     * - notificaciones-service envía notificación de desvinculación
     * 
     * USO:
     * Se usa en security.feature y offboarding.feature para verificar
     * permisos y flujo de desvinculación.
     */
    @When("elimino el empleado con id {int}")
    public void eliminarEmpleado(int id) {
        ctx.setUltimaRespuesta(requestAutenticado().delete("/empleados/" + id));
    }

    /**
     * Paso: "Entonces la respuesta debe contener una lista de empleados"
     * 
     * PROPÓSITO:
     * Verificar que la respuesta contiene el campo "empleados" con una lista.
     * 
     * VERIFICACIÓN:
     * - El campo "empleados" existe en la respuesta JSON
     * - El campo "empleados" no es null
     * - El campo "empleados" es una lista (puede estar vacía)
     * 
     * ESTRUCTURA ESPERADA:
     * {
     *   "total": 100,
     *   "pagina": 1,
     *   "por_pagina": 10,
     *   "total_paginas": 10,
     *   "empleados": [ ... ]  ← Este campo se verifica
     * }
     * 
     * NOTA:
     * No verifica el contenido de la lista, solo que existe y es una lista.
     * Para verificar contenido específico, usar otros pasos de verificación.
     */
    @Then("la respuesta debe contener una lista de empleados")
    public void verificarListaEmpleados() {
        // La respuesta es paginada: { total, pagina, por_pagina, total_paginas, empleados: [...] }
        assertThat(ctx.getUltimaRespuesta().jsonPath().getList("empleados"), notNullValue());
    }

    /**
     * Paso: "Entonces el empleado creado debe tener el nombre {string}"
     * 
     * PROPÓSITO:
     * Verificar que el nombre del empleado en la respuesta coincide con el esperado.
     * 
     * PARÁMETRO:
     * - nombre: Nombre esperado del empleado
     * 
     * VERIFICACIÓN:
     * Extrae el campo "nombre" de la respuesta JSON y lo compara con el valor esperado.
     * 
     * ESTRUCTURA ESPERADA:
     * {
     *   "id": 123,
     *   "nombre": "Juan Pérez",  ← Este campo se verifica
     *   "email": "juan@empresa.com",
     *   ...
     * }
     * 
     * USO:
     * Se usa después de crear un empleado para verificar que los datos
     * se guardaron correctamente.
     */
    @Then("el empleado creado debe tener el nombre {string}")
    public void verificarNombreEmpleado(String nombre) {
        String nombreRespuesta = ctx.getUltimaRespuesta().jsonPath().getString("nombre");
        assertThat(nombreRespuesta, equalTo(nombre));
    }
}
