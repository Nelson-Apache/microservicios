package com.empresa.e2e.step_definitions;

import com.empresa.e2e.support.ConfiguracionBase;
import com.empresa.e2e.support.TestContext;
import com.empresa.e2e.support.WaitUtils;
import io.cucumber.java.es.Cuando;
import io.cucumber.java.es.Dado;
import io.cucumber.java.es.Entonces;
import io.restassured.response.Response;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;

import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.*;

/**
 * Step definitions para escenarios de GESTIÓN DE VACACIONES.
 *
 * FLUJO DE VACACIONES:
 * 1. ADMIN programa vacaciones → POST /vacaciones
 * 2. vacaciones-service publica "vacaciones.programadas" en RabbitMQ
 * 3. auth-service desactiva la cuenta del empleado (asincrónico)
 * 4. notificaciones-service envía confirmación (asincrónico)
 * 5. Al finalizar → PUT /vacaciones/{id} con estado FINALIZADA
 * 6. vacaciones-service publica "vacaciones.finalizadas"
 * 7. auth-service reactiva la cuenta del empleado (asincrónico)
 */
public class VacacionesSteps extends ConfiguracionBase {

    public VacacionesSteps(TestContext ctx) {
        super(ctx);
    }

    /**
     * Paso: "Cuando programo vacaciones para el empleado"
     *
     * Crea un período de vacaciones para el empleado del contexto actual.
     * Usa fechas futuras para evitar conflictos con la lógica de negocio.
     * El ID de vacación se genera con timestamp para garantizar unicidad.
     * Publica el evento "vacaciones.programadas" al completarse.
     */
    @Cuando("programo vacaciones para el empleado")
    public void programarVacaciones() {
        Integer empleadoId = ctx.getEmpleadoId();
        assertThat("No se guardó el ID del empleado", empleadoId, notNullValue());

        int vacacionId = (int) (System.currentTimeMillis() % 1000000);
        LocalDate inicio = LocalDate.now().plusDays(30);
        LocalDate fin    = LocalDate.now().plusDays(44);

        Map<String, Object> body = new HashMap<>();
        body.put("id", vacacionId);
        body.put("empleado_id", empleadoId);
        body.put("fecha_inicio", inicio.toString());
        body.put("fecha_fin", fin.toString());
        body.put("motivo", "Vacaciones programadas e2e " + vacacionId);

        Response respuesta = requestAutenticado().body(body).post("/vacaciones");
        ctx.setUltimaRespuesta(respuesta);

        if (respuesta.statusCode() == 201) {
            ctx.setVacacionId(vacacionId);
        }
    }

    /**
     * Paso: "Dado que el empleado ya tiene vacaciones programadas"
     *
     * Pre-condición: crea una vacación antes de ejecutar el escenario.
     * Reutiliza la lógica de programarVacaciones() y verifica que fue exitosa.
     */
    @Dado("que el empleado ya tiene vacaciones programadas")
    public void empleadoTieneVacacionesProgramadas() {
        programarVacaciones();
        assertThat(
            "No se pudieron programar las vacaciones de precondición",
            ctx.getUltimaRespuesta().statusCode(), equalTo(201)
        );
    }

    /**
     * Paso: "Cuando programo vacaciones que se solapan para el mismo empleado"
     *
     * Intenta crear un período que se solapa con el ya existente en ctx.
     * Debe retornar 409 Conflict según la lógica de negocio.
     */
    @Cuando("programo vacaciones que se solapan para el mismo empleado")
    public void programarVacacionesSolapadas() {
        Integer empleadoId = ctx.getEmpleadoId();
        assertThat("No se guardó el ID del empleado", empleadoId, notNullValue());

        int otroId = (int) (System.currentTimeMillis() % 1000000) + 1;
        // Solapamiento: inicia 5 días después del inicio de la vacación existente
        LocalDate inicio = LocalDate.now().plusDays(35);
        LocalDate fin    = LocalDate.now().plusDays(50);

        Map<String, Object> body = new HashMap<>();
        body.put("id", otroId);
        body.put("empleado_id", empleadoId);
        body.put("fecha_inicio", inicio.toString());
        body.put("fecha_fin", fin.toString());
        body.put("motivo", "Vacación solapada e2e");

        ctx.setUltimaRespuesta(requestAutenticado().body(body).post("/vacaciones"));
    }

    /**
     * Paso: "Cuando consulto las vacaciones del empleado"
     *
     * Hace GET /vacaciones filtrando por el empleado_id del contexto.
     */
    @Cuando("consulto las vacaciones del empleado")
    public void consultarVacaciones() {
        Integer empleadoId = ctx.getEmpleadoId();
        assertThat("No se guardó el ID del empleado", empleadoId, notNullValue());

        ctx.setUltimaRespuesta(
            requestAutenticado().get("/vacaciones?empleado_id=" + empleadoId)
        );
    }

    /**
     * Paso: "Y la respuesta debe contener la lista de vacaciones"
     *
     * Verifica que la respuesta es una estructura paginada con al menos un elemento.
     */
    @Entonces("la respuesta debe contener la lista de vacaciones")
    public void verificarListaVacaciones() {
        Response respuesta = ctx.getUltimaRespuesta();
        assertThat(respuesta.statusCode(), equalTo(200));
        Integer total = respuesta.jsonPath().get("total");
        assertThat("La lista de vacaciones debe tener al menos un elemento", total, greaterThan(0));
    }

    /**
     * Paso: "Cuando finalizo las vacaciones del empleado"
     *
     * Actualiza la vacación del contexto a estado FINALIZADA.
     * Esto publica el evento "vacaciones.finalizadas" que reactiva la cuenta.
     */
    @Cuando("finalizo las vacaciones del empleado")
    public void finalizarVacaciones() {
        Integer vacacionId = ctx.getVacacionId();
        assertThat("No se guardó el ID de vacación", vacacionId, notNullValue());

        Map<String, Object> body = new HashMap<>();
        body.put("estado", "FINALIZADA");

        ctx.setUltimaRespuesta(
            requestAutenticado().body(body).put("/vacaciones/" + vacacionId)
        );
    }

    /**
     * Paso: "Y eventualmente la cuenta del empleado debe estar desactivada por vacaciones"
     *
     * Polling: verifica que auth-service procesó el evento "vacaciones.programadas"
     * y desactivó la cuenta. Se intenta login con las credenciales reales.
     * Retorno esperado: 401 con "inhabilitado".
     *
     * TIMEOUT: 30 intentos × 2s = 60 segundos.
     */
    @Entonces("eventualmente la cuenta del empleado debe estar desactivada por vacaciones")
    public void verificarCuentaDesactivadaPorVacaciones() {
        String email    = ctx.getEmpleadoEmail();
        String password = ctx.getEmpleadoPassword();
        assertThat("No se guardó el email del empleado", email, notNullValue());
        assertThat("No se guardó la contraseña del empleado", password, notNullValue());

        WaitUtils.waitUntil(() -> {
            Map<String, String> loginBody = new HashMap<>();
            loginBody.put("nombre_usuario", email);
            loginBody.put("contrasena", password);

            Response respuesta = request().body(loginBody).post("/auth/login");
            if (respuesta.statusCode() == 401) {
                String detalle = respuesta.jsonPath().getString("detail");
                return detalle != null && detalle.contains("inhabilitado");
            }
            return false;
        }, 30, 2000);
    }

    /**
     * Paso: "Y eventualmente la cuenta del empleado debe estar reactivada"
     *
     * Polling: verifica que auth-service procesó el evento "vacaciones.finalizadas"
     * y reactivó la cuenta. Se intenta login con las credenciales reales.
     * Retorno esperado: 200.
     *
     * TIMEOUT: 30 intentos × 2s = 60 segundos.
     */
    @Entonces("eventualmente la cuenta del empleado debe estar reactivada")
    public void verificarCuentaReactivada() {
        String email    = ctx.getEmpleadoEmail();
        String password = ctx.getEmpleadoPassword();
        assertThat("No se guardó el email del empleado", email, notNullValue());
        assertThat("No se guardó la contraseña del empleado", password, notNullValue());

        WaitUtils.waitUntil(() -> {
            Map<String, String> loginBody = new HashMap<>();
            loginBody.put("nombre_usuario", email);
            loginBody.put("contrasena", password);

            Response respuesta = request().body(loginBody).post("/auth/login");
            return respuesta.statusCode() == 200;
        }, 30, 2000);

        // Verificación final afirmativa
        Map<String, String> loginBody = new HashMap<>();
        loginBody.put("nombre_usuario", email);
        loginBody.put("contrasena", password);
        Response respuestaFinal = request().body(loginBody).post("/auth/login");
        assertThat("La cuenta del empleado no fue reactivada", respuestaFinal.statusCode(), equalTo(200));
    }
}
