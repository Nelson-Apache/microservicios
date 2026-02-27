# 🔌 Circuit Breaker - Guía de Pruebas

Esta guía muestra cómo probar el Circuit Breaker y el sistema de caché implementado en el servicio de empleados.

## 🎯 Objetivo

El Circuit Breaker protege al servicio de empleados cuando el servicio de departamentos está caído o experimentando problemas. Utiliza una caché TTL como fallback para mantener el servicio operativo incluso cuando las dependencias fallan.

## 🏗️ Arquitectura

```
empleados-service
    ↓
DepartamentosClient
    ├── Circuit Breaker (pybreaker)
    │   ├── Estado: closed / open / half-open
    │   ├── Umbral: 5 fallos
    │   └── Timeout: 60 segundos
    │
    ├── Retry Logic (tenacity)
    │   ├── Intentos: 3
    │   └── Backoff: exponencial
    │
    └── Cache TTL (cachetools)
        ├── Tamaño: 100 departamentos
        └── TTL: 5 minutos
```

## 📋 Escenarios de Prueba

### Escenario 1: Funcionamiento Normal (Circuit Closed)

**Estado esperado**: Circuit Breaker cerrado, todas las peticiones van al servicio de departamentos.

```bash
# 1. Asegurarse de que todos los servicios están corriendo
docker-compose ps

# 2. Crear un departamento
curl -X POST http://localhost:8080/departamentos \
  -H "Content-Type: application/json" \
  -d '{"id":"IT","nombre":"Tecnología","descripcion":"TI"}'

# 3. Crear un empleado (debería validar contra el servicio)
curl -X POST http://localhost:8000/empleados \
  -H "Content-Type: application/json" \
  -d '{"id":"E001","nombre":"Juan Pérez","email":"juan@test.com","departamentoId":"IT","fechaIngreso":"2024-01-15"}'

# 4. Verificar estado del Circuit Breaker
curl http://localhost:8000/empleados/debug/circuit-breaker

# Resultado esperado:
# {
#   "circuit_breaker": {
#     "state": "closed",
#     "fail_counter": 0,
#     "cache_size": 1  ← IT está en cache
#   }
# }
```

**Logs esperados** (empleados-service):
```json
{
  "message": "Departamento validado exitosamente",
  "departamento_id": "IT",
  "source": "service",
  "circuit_state": "closed"
}
```

---

### Escenario 2: Cache Hit (Servicio Funcionando)

**Estado esperado**: El departamento ya está en cache, respuesta más rápida.

```bash
# 1. Crear otro empleado del mismo departamento
curl -X POST http://localhost:8000/empleados \
  -H "Content-Type: application/json" \
  -d '{"id":"E002","nombre":"María García","email":"maria@test.com","departamentoId":"IT","fechaIngreso":"2024-01-20"}'

# 2. Verificar logs - debería mostrar cache hit
docker-compose logs empleados-service | grep -i cache
```

**Logs esperados**:
```json
{
  "message": "Cache HIT para departamento",
  "departamento_id": "IT",
  "source": "cache"
}
```

---

### Escenario 3: Servicio Caído - Circuit Breaker Abre

**Estado esperado**: Después de 5 fallos, el Circuit Breaker se abre y usa cache.

```bash
# 1. Detener el servicio de departamentos
docker-compose stop departamentos-service

# 2. Intentar crear 5 empleados para diferentes departamentos sin cache
# (Esto forzará 5 fallos consecutivos)

for i in {1..5}; do
  curl -X POST http://localhost:8000/empleados \
    -H "Content-Type: application/json" \
    -d "{\"id\":\"E00$i\",\"nombre\":\"Test$i\",\"email\":\"test$i@test.com\",\"departamentoId\":\"HR\",\"fechaIngreso\":\"2024-01-15\"}"
  echo ""
done

# 3. Verificar estado del Circuit Breaker
curl http://localhost:8000/empleados/debug/circuit-breaker

# Resultado esperado después de 5 fallos:
# {
#   "circuit_breaker": {
#     "state": "open",  ← Cambió a open
#     "fail_counter": 5,
#     "fail_max": 5
#   }
# }

# 4. Ver logs del Circuit Breaker
docker-compose logs empleados-service | grep -i "circuit"
```

**Logs esperados**:
```json
{
  "message": "Circuit Breaker ABIERTO - usando cache como fallback",
  "departamento_id": "HR",
  "circuit_state": "open",
  "fail_counter": 5
}
```

---

### Escenario 4: Fallback a Cache (Circuit Abierto)

**Estado esperado**: Con Circuit Breaker abierto, usar cache para departamentos que ya consultamos antes.

```bash
# 1. Con departamentos-service aún detenido, crear empleado para departamento en cache
curl -X POST http://localhost:8000/empleados \
  -H "Content-Type: application/json" \
  -d '{"id":"E100","nombre":"Ana López","email":"ana@test.com","departamentoId":"IT","fechaIngreso":"2024-01-25"}'

# Resultado esperado: HTTP 201 Created ✓
# (Usó cache del departamento IT sin llamar al servicio)

# 2. Intentar con departamento NO en cache
curl -X POST http://localhost:8000/empleados \
  -H "Content-Type: application/json" \
  -d '{"id":"E101","nombre":"Carlos Ruiz","email":"carlos@test.com","departamentoId":"SALES","fechaIngreso":"2024-01-25"}'

# Resultado esperado: HTTP 503 Service Unavailable
# {
#   "detail": "Servicio de departamentos no disponible y no hay datos en cache para ID SALES"
# }
```

---

### Escenario 5: Recuperación (Circuit Half-Open → Closed)

**Estado esperado**: Después de 60 segundos, el Circuit Breaker prueba recovery.

```bash
# 1. Reiniciar el servicio de departamentos
docker-compose start departamentos-service

# 2. Esperar 60 segundos (timeout_duration del Circuit Breaker)
sleep 60

# 3. Verificar estado - debería estar en half-open
curl http://localhost:8000/empleados/debug/circuit-breaker

# Resultado después de timeout:
# {
#   "circuit_breaker": {
#     "state": "half-open"  ← Probando recovery
#   }
# }

# 4. Crear un empleado (esto probará si el servicio se recuperó)
curl -X POST http://localhost:8000/empleados \
  -H "Content-Type: application/json" \
  -d '{"id":"E200","nombre":"Pedro Sánchez","email":"pedro@test.com","departamentoId":"IT","fechaIngreso":"2024-01-26"}'

# 5. Si tiene éxito, verificar que el Circuit Breaker volvió a closed
curl http://localhost:8000/empleados/debug/circuit-breaker

# Resultado esperado:
# {
#   "circuit_breaker": {
#     "state": "closed",  ← Volvió a funcionamiento normal
#     "fail_counter": 0   ← Contador reseteado
#   }
# }
```

---

### Escenario 6: Cache TTL (Expiración)

**Estado esperado**: Después de 5 minutos, el cache expira.

```bash
# 1. Crear un departamento y un empleado
curl -X POST http://localhost:8080/departamentos \
  -H "Content-Type: application/json" \
  -d '{"id":"FINANCE","nombre":"Finanzas","descripcion":"Dept Finanzas"}'

curl -X POST http://localhost:8000/empleados \
  -H "Content-Type: application/json" \
  -d '{"id":"E300","nombre":"Laura Gómez","email":"laura@test.com","departamentoId":"FINANCE","fechaIngreso":"2024-01-26"}'

# 2. Verificar que está en cache
curl http://localhost:8000/empleados/debug/circuit-breaker
# cache_size debería ser > 0

# 3. Esperar 5 minutos (300 segundos) para que expire el TTL
sleep 300

# 4. Verificar cache de nuevo
curl http://localhost:8000/empleados/debug/circuit-breaker
# cache_size podría ser 0 si no hay otras entradas

# 5. El próximo empleado forzará una nueva consulta al servicio
curl -X POST http://localhost:8000/empleados \
  -H "Content-Type: application/json" \
  -d '{"id":"E301","nombre":"Sofía Martínez","email":"sofia@test.com","departamentoId":"FINANCE","fechaIngreso":"2024-01-26"}'

# Logs mostrarán consulta al servicio (no cache hit)
```

---

## 📊 Monitoreo en Tiempo Real

### Ver logs del Circuit Breaker

```bash
# Logs generales del servicio
docker-compose logs -f empleados-service

# Filtrar solo eventos de Circuit Breaker
docker-compose logs -f empleados-service | grep -E "circuit|cache|fallback"

# Ver estado JSON estructurado
docker-compose logs empleados-service --tail=50 | jq 'select(.circuit_state != null)'
```

### Dashboard de estado

```bash
# Script para monitoreo continuo
watch -n 2 'curl -s http://localhost:8000/empleados/debug/circuit-breaker | jq'
```

---

## 🔧 Configuración Personalizada

Las siguientes variables pueden configurarse en el código:

```python
# En departamentos_client.py

# Circuit Breaker
fail_max=5           # Número de fallos antes de abrir (default: 5)
timeout_duration=60  # Segundos en estado abierto (default: 60)

# Cache
maxsize=100          # Máximo de departamentos en cache (default: 100)
ttl=300              # Tiempo de vida en segundos (default: 300 = 5 min)

# Timeout
timeout=5.0          # Timeout por request en segundos (default: 5.0)
```

---

## ✅ Checklist de Pruebas

- [ ] Circuit Breaker inicia en estado `closed`
- [ ] Cache almacena departamentos consultados
- [ ] Después de 5 fallos, Circuit Breaker pasa a `open`
- [ ] Con Circuit Breaker abierto, usa cache como fallback
- [ ] Sin cache disponible, retorna HTTP 503
- [ ] Después de 60s, Circuit Breaker pasa a `half-open`
- [ ] Si la prueba tiene éxito, vuelve a `closed`
- [ ] Cache expira después de 5 minutos (TTL)
- [ ] Logs muestran eventos del Circuit Breaker
- [ ] Endpoint de debug retorna información precisa

---

## 🎓 Conceptos Clave

### ¿Por qué Circuit Breaker?

Previene **cascading failures** (fallos en cascada). Si el servicio de departamentos está caído, sin Circuit Breaker:

1. Cada request espera timeout (5s)
2. Reintenta 3 veces (15s total)
3. Cientos de requests → Congestión masiva
4. El servicio de empleados también colapsa

**Con Circuit Breaker**:
1. Detecta fallos rápidamente
2. Abre el circuito después de 5 fallos
3. Usa cache como fallback
4. El servicio de empleados sigue funcionando ✓

### ¿Por qué Cache con TTL?

- **Performance**: Reduce latencia y carga en departamentos-service
- **Resiliencia**: Permite operación degradada cuando el servicio falla
- **TTL**: Evita datos obsoletos (5 minutos es balance entre freshness y resiliencia)

---

## 📚 Referencias

- **pybreaker**: https://github.com/danielfm/pybreaker
- **cachetools**: https://github.com/tkem/cachetools
- **tenacity**: https://github.com/jd/tenacity
- **Circuit Breaker Pattern**: https://martinfowler.com/bliki/CircuitBreaker.html
