package com.empresa.e2e.support;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;

import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

/**
 * Utilidades para generar tokens JWT en tests E2E.
 * 
 * PROBLEMA QUE RESUELVE:
 * El escenario "Empleado puede hacer login después de onboarding" requiere
 * establecer una contraseña usando un token de recuperación.
 * En producción, este token se envía por email.
 * En E2E tests, no tenemos acceso al email.
 * 
 * SOLUCIÓN:
 * Generar el token JWT directamente en el test usando la misma lógica
 * que auth-service/app/jwt_utils.py
 * 
 * JUSTIFICACIÓN:
 * ✅ Es aceptable en E2E tests generar el JWT con el mismo secreto (controlamos el entorno)
 * ✅ Evita dependencias externas (parsear logs, crear endpoints de test)
 * ✅ Replica exactamente la lógica del servicio de autenticación
 * ✅ Permite probar el flujo completo de establecimiento de contraseña
 * 
 * ALTERNATIVAS DESCARTADAS:
 * ❌ Parsear logs de Docker: Frágil, depende del formato de logs, lento
 * ❌ Endpoint de test en auth-service: Agrega código de test al servicio de producción
 * ❌ Mock del token: No prueba la validación real del JWT
 * 
 * IMPORTANTE:
 * El valor de JWT_SECRET debe coincidir EXACTAMENTE con el configurado
 * en docker-compose.yml y en el auth-service.
 */
public class JwtTestUtils {

    /**
     * Clave secreta compartida (debe coincidir con JWT_SECRET del auth-service).
     * 
     * RESOLUCIÓN:
     * 1. Variable de entorno JWT_SECRET
     * 2. Valor por defecto (para desarrollo local)
     * 
     * SEGURIDAD:
     * En producción, este valor debe ser un secreto fuerte y único.
     * En tests E2E, usamos el mismo valor que el sistema bajo prueba.
     */
    private static final String JWT_SECRET = System.getenv()
            .getOrDefault("JWT_SECRET", "changeme-super-secret-key-for-dev");

    /** Algoritmo de firma (debe coincidir con auth-service) */
    private static final String ALGORITHM = "HS256";
    
    /** Tiempo de expiración del token de recuperación (60 minutos) */
    private static final int RESET_TOKEN_EXPIRE_MINUTES = 60;

    /**
     * Genera un token de recuperación de contraseña (RESET_PASSWORD).
     * 
     * REPLICA LA LÓGICA DE: auth-service/app/jwt_utils.py::crear_token_recuperacion()
     * 
     * ESTRUCTURA DEL TOKEN:
     * {
     *   "sub": "usuario@empresa.com",  // Nombre de usuario (email)
     *   "type": "RESET_PASSWORD",       // Tipo de token
     *   "iat": 1234567890,              // Timestamp de emisión
     *   "exp": 1234571490               // Timestamp de expiración (60 min después)
     * }
     * 
     * FIRMA:
     * - Algoritmo: HS256 (HMAC con SHA-256)
     * - Secreto: JWT_SECRET (mismo que auth-service)
     * 
     * USO EN TESTS:
     * String token = JwtTestUtils.crearTokenRecuperacion("empleado@empresa.com");
     * // Usar el token para establecer contraseña vía POST /auth/reset-password
     * 
     * @param nombreUsuario El nombre de usuario (email) para el que se genera el token
     * @return Token JWT firmado con HS256, válido por 60 minutos
     */
    public static String crearTokenRecuperacion(String nombreUsuario) {
        long ahora = System.currentTimeMillis();
        long expiracion = ahora + (RESET_TOKEN_EXPIRE_MINUTES * 60 * 1000);

        // Claims del token (datos adicionales)
        Map<String, Object> claims = new HashMap<>();
        claims.put("type", "RESET_PASSWORD");

        // Construir y firmar el token
        return Jwts.builder()
                .setClaims(claims)
                .setSubject(nombreUsuario)              // "sub": nombre de usuario
                .setIssuedAt(new Date(ahora))           // "iat": timestamp de emisión
                .setExpiration(new Date(expiracion))    // "exp": timestamp de expiración
                .signWith(SignatureAlgorithm.HS256, JWT_SECRET.getBytes(StandardCharsets.UTF_8))
                .compact();
    }
}
