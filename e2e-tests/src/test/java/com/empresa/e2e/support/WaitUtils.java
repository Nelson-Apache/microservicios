package com.empresa.e2e.support;

import java.util.function.Supplier;

/**
 * Utilidades para esperar condiciones asíncronas en pruebas E2E.
 * 
 * PROBLEMA QUE RESUELVE:
 * En sistemas basados en eventos (RabbitMQ), las operaciones son asíncronas.
 * Ejemplo: Al crear un empleado, el evento "empleado.creado" se procesa después.
 * No podemos verificar inmediatamente que se crearon las credenciales.
 * 
 * SOLUCIÓN: POLLING CON REINTENTOS
 * En lugar de Thread.sleep() fijo, consultamos repetidamente hasta que:
 * - La condición se cumple → éxito
 * - Se agotan los intentos → fallo
 * 
 * VENTAJAS SOBRE Thread.sleep():
 * ✅ La prueba termina más rápido si el evento se procesa rápidamente
 * ✅ Tolera variaciones de tiempo sin fallar de forma intermitente
 * ✅ Proporciona mensaje de error claro al agotar el timeout
 * 
 * EJEMPLO DE USO:
 * WaitUtils.waitUntil(() -> {
 *     Response response = request().get("/auth/users/" + email);
 *     return response.statusCode() == 200;
 * }, 10, 2000);  // 10 intentos × 2 segundos = 20 segundos timeout
 */
public class WaitUtils {

    /**
     * Espera hasta que una condición se cumpla, con reintentos.
     * 
     * FUNCIONAMIENTO:
     * 1. Ejecuta la condición (lambda)
     * 2. Si retorna true → éxito, termina inmediatamente
     * 3. Si retorna false → espera intervaloMs y reintenta
     * 4. Si se agotan los intentos → lanza AssertionError
     * 
     * PARÁMETROS RECOMENDADOS:
     * - maxIntentos: 10-15 (suficiente para la mayoría de eventos)
     * - intervaloMs: 2000 (2 segundos, balance entre velocidad y carga)
     * - Timeout total: maxIntentos × intervaloMs (ej: 10 × 2s = 20s)
     * 
     * CALIBRACIÓN:
     * Los valores se calibraron midiendo tiempos de procesamiento de eventos:
     * - Promedio: 3-5 segundos
     * - Margen de seguridad: ×4 = 20 segundos
     * 
     * @param condicion Lambda que retorna true cuando la condición se cumple
     * @param maxIntentos Número máximo de intentos antes de fallar
     * @param intervaloMs Tiempo de espera entre intentos en milisegundos
     * @throws AssertionError si la condición no se cumple tras todos los intentos
     */
    public static void waitUntil(Supplier<Boolean> condicion, int maxIntentos, long intervaloMs) {
        for (int intento = 1; intento <= maxIntentos; intento++) {
            // Ejecutar la condición
            if (condicion.get()) {
                return; // ✅ Condición cumplida → éxito
            }
            
            // Si no es el último intento, esperar antes de reintentar
            if (intento < maxIntentos) {
                try {
                    Thread.sleep(intervaloMs);
                } catch (InterruptedException e) {
                    // Si el thread es interrumpido, restaurar el flag y fallar
                    Thread.currentThread().interrupt();
                    throw new AssertionError("Espera interrumpida durante el intento " + intento, e);
                }
            }
        }
        
        // ❌ Se agotaron los intentos → fallo
        throw new AssertionError(
            String.format("La condición no se cumplió tras %d intentos (intervalo: %dms, timeout total: %dms)",
                maxIntentos, intervaloMs, maxIntentos * intervaloMs)
        );
    }

    /**
     * Sobrecarga con valores por defecto optimizados.
     * 
     * VALORES POR DEFECTO:
     * - maxIntentos: 10
     * - intervaloMs: 2000 (2 segundos)
     * - Timeout total: 20 segundos
     * 
     * USO:
     * WaitUtils.waitUntil(() -> {
     *     Response response = request().get("/empleados/" + id);
     *     return response.statusCode() == 200;
     * });
     * 
     * @param condicion Lambda que retorna true cuando la condición se cumple
     */
    public static void waitUntil(Supplier<Boolean> condicion) {
        waitUntil(condicion, 10, 2000);
    }
}
