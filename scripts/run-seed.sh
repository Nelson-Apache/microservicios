#!/bin/bash
# Carga los datos semilla en las bases de datos para demo
# Uso: bash scripts/run-seed.sh
# Requisito: docker-compose up -d debe estar ejecutándose

set -e

echo "Esperando que las bases de datos estén disponibles..."
sleep 5

echo "Cargando datos en departamentosdb..."
docker-compose exec -T database-departamentos psql -U postgres -d departamentosdb \
  -c "$(sed -n '/departamentosdb/,/empleadosdb/p' scripts/seed-data.sql | head -n -1)"

echo "Cargando datos en empleadosdb..."
docker-compose exec -T db-empleados psql -U postgres -d empleadosdb \
  -c "$(sed -n '/empleadosdb/,/authdb/p' scripts/seed-data.sql | head -n -1)"

echo "Cargando datos en vacacionesdb..."
docker-compose exec -T database-vacaciones psql -U postgres -d vacacionesdb \
  -c "INSERT INTO vacaciones (id, empleado_id, fecha_inicio, fecha_fin, motivo, estado, created_at) VALUES (1, 101, CURRENT_DATE + INTERVAL '7 days', CURRENT_DATE + INTERVAL '14 days', 'Vacaciones anuales', 'PROGRAMADA', NOW()) ON CONFLICT (id) DO NOTHING;"

echo "Datos semilla cargados correctamente."
echo ""
echo "Credenciales disponibles:"
echo "  Admin:   admin / admin123"
echo "  Gateway: http://localhost:8000"
echo "  Grafana: http://localhost:3001 (admin/admin)"
