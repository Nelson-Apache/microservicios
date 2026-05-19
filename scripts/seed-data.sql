-- =====================================================================
-- Datos semilla para demo del sistema de microservicios
-- =====================================================================
-- Ejecución:
--   docker-compose exec db-empleados psql -U postgres -d empleadosdb -f /seed-data.sql
--   docker-compose exec db-auth psql -U postgres -d authdb -f /seed-data.sql
--   docker-compose exec database-departamentos psql -U postgres -d departamentosdb -f /seed-data.sql
--
-- O desde el host (con las BDs ya levantadas):
--   psql postgresql://postgres:postgres@localhost:5432/empleadosdb -f scripts/seed-data.sql
-- =====================================================================

-- ─── Base de datos: departamentosdb ───────────────────────────────
\connect departamentosdb

INSERT INTO departamentos (id, nombre, descripcion, activo)
VALUES
    (1, 'Tecnología',      'Desarrollo de software y sistemas',      true),
    (2, 'Recursos Humanos','Gestión del talento humano',              true),
    (3, 'Finanzas',        'Contabilidad y gestión financiera',       true),
    (4, 'Operaciones',     'Logística y operaciones diarias',         true)
ON CONFLICT (id) DO NOTHING;

-- ─── Base de datos: empleadosdb ───────────────────────────────────
\connect empleadosdb

INSERT INTO empleados (id, nombre, cargo, departamento_id, email, salario, fecha_ingreso, activo, estado, created_at, updated_at)
VALUES
    (101, 'Ana García',     'Desarrolladora Senior', 1, 'ana.garcia@empresa.com',    5500.00, NOW(), true, 'ACTIVO', NOW(), NOW()),
    (102, 'Carlos López',   'Analista de RRHH',      2, 'carlos.lopez@empresa.com',  4200.00, NOW(), true, 'ACTIVO', NOW(), NOW()),
    (103, 'María Rodríguez','Gerente de Finanzas',    3, 'maria.rodriguez@empresa.com',6000.00, NOW(), true, 'ACTIVO', NOW(), NOW()),
    (104, 'Juan Martínez',  'Coordinador TI',        1, 'juan.martinez@empresa.com', 4800.00, NOW(), true, 'ACTIVO', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- ─── Base de datos: authdb ────────────────────────────────────────
-- Nota: el usuario admin se crea automáticamente al arrancar auth-service.
-- Aquí solo se documentan los usuarios de empleados para referencia.
-- Los usuarios reales se crean automáticamente cuando auth-service
-- consume el evento 'empleado.creado' (flujo de onboarding).
--
-- Si necesitas crear los usuarios manualmente:
--   POST /auth/establecer-contrasena con el token de recuperación enviado
--   al email del empleado (visible en los logs de notificaciones-service).
--
-- Usuario admin (creado automáticamente por auth-service al arrancar):
--   usuario: admin
--   contraseña: admin123
--   rol: ADMIN
-- =====================================================================

-- ─── Base de datos: vacacionesdb ──────────────────────────────────
\connect vacacionesdb

-- Vacación de ejemplo para usar en demos
INSERT INTO vacaciones (id, empleado_id, fecha_inicio, fecha_fin, motivo, estado, created_at)
VALUES
    (1, 101, CURRENT_DATE + INTERVAL '7 days', CURRENT_DATE + INTERVAL '14 days',
     'Vacaciones anuales', 'PROGRAMADA', NOW())
ON CONFLICT (id) DO NOTHING;
