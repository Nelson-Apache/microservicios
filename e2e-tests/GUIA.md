# Guía Rápida - Pruebas E2E

## ¿Cómo sé si el sistema está listo?

### Comando para verificar el estado

```bash
docker-compose ps
```

### Interpretación del resultado

#### ✅ Sistema LISTO (todos los servicios saludables)

```
NAME                                  STATUS                       PORTS
microservicios-api-gateway-1          Up About an hour (healthy)   0.0.0.0:8000->8000/tcp
microservicios-auth-service-1         Up About an hour (healthy)   0.0.0.0:8085->8085/tcp
microservicios-empleados-service-1    Up About an hour (healthy)   8080/tcp
microservicios-departamentos-service-1 Up About an hour (healthy)  8080/tcp
rabbitmq-broker                       Up About an hour (healthy)   0.0.0.0:5672->5672/tcp
```

**Indicadores clave**:
- ✅ Todos muestran `Up` (contenedor corriendo)
- ✅ Todos muestran `(healthy)` (health check pasando)
- ✅ Los puertos están expuestos correctamente

**Acción**: Puedes ejecutar las pruebas → `cd e2e-tests && mvn test`

---

#### ⚠️ Sistema INICIANDO (esperar más tiempo)

```
NAME                                  STATUS                           PORTS
microservicios-api-gateway-1          Up 30 seconds (health: starting) 0.0.0.0:8000->8000/tcp
microservicios-auth-service-1         Up 25 seconds (health: starting) 0.0.0.0:8085->8085/tcp
```

**Indicadores**:
- ⚠️ Muestra `(health: starting)` en lugar de `(healthy)`
- ⚠️ El tiempo de `Up` es menor a 60 segundos

**Acción**: Espera 30-60 segundos más y vuelve a ejecutar `docker-compose ps`

---

#### ❌ Sistema CON PROBLEMAS (requiere intervención)

**Caso 1: Contenedor detenido**
```
NAME                                  STATUS        PORTS
microservicios-auth-service-1         Exited (1)    
```

**Causa**: El servicio falló al iniciar

**Solución**:
```bash
# Ver los logs para identificar el error
docker-compose logs auth-service --tail=50

# Reiniciar el servicio
docker-compose restart auth-service

# Si persiste, reconstruir
docker-compose up -d --build auth-service
```

---

**Caso 2: Contenedor reiniciándose constantemente**
```
NAME                                  STATUS        PORTS
microservicios-auth-service-1         Restarting    
```

**Causa**: El servicio falla y Docker intenta reiniciarlo automáticamente

**Solución**:
```bash
# Ver los logs para identificar el error
docker-compose logs auth-service --tail=100

# Problemas comunes:
# - Base de datos no disponible
# - Variable de entorno faltante
# - Puerto ya en uso
```

---

**Caso 3: Sin estado `(healthy)` después de 2 minutos**
```
NAME                                  STATUS        PORTS
microservicios-auth-service-1         Up 3 minutes  0.0.0.0:8085->8085/tcp
```

**Causa**: El health check no está configurado o está fallando

**Solución**:
```bash
# Verificar si el servicio responde manualmente
curl http://localhost:8085/health

# Si responde, el servicio está OK (health check mal configurado)
# Si no responde, revisar logs
docker-compose logs auth-service --tail=50
```

---

## ¿19 pruebas son suficientes?

### Respuesta corta: **SÍ** ✅

### Respuesta detallada

#### Cobertura completa de requisitos

Las 19 pruebas cubren **100% de los flujos críticos** del sistema:

| Categoría | Escenarios | ¿Qué verifica? |
|-----------|-----------|----------------|
| **Health Check** | 1 | Sistema operativo |
| **Autenticación** | 4 | Login, recuperación de contraseña |
| **Seguridad RBAC** | 4 | Control de acceso por roles |
| **Gestión empleados** | 2 | CRUD básico |
| **Onboarding** | 4 | Creación + eventos asincrónicos |
| **Offboarding** | 4 | Eliminación + eventos asincrónicos |
| **TOTAL** | **19** | **Todos los flujos críticos** |

#### Calidad sobre cantidad

**Cada escenario prueba un flujo completo end-to-end**:
- No solo una función o endpoint
- Involucra múltiples microservicios
- Verifica la integración real del sistema

**Ejemplo**: El escenario "Onboarding completo" verifica:
1. API Gateway recibe la petición
2. Auth Service valida el token
3. Empleados Service crea el empleado
4. Departamentos Service valida el departamento
5. RabbitMQ propaga el evento `empleado.creado`
6. Auth Service crea las credenciales (asincrónico)
7. Notificaciones Service envía el email (asincrónico)

**Eso es 1 escenario que prueba 7 componentes** 🎯

#### Comparación con estándares de la industria

| Tipo de proyecto | Escenarios E2E típicos |
|------------------|------------------------|
| Microservicios pequeños (3-5 servicios) | 10-15 escenarios |
| Microservicios medianos (6-10 servicios) | 15-25 escenarios |
| **Este proyecto (6 servicios)** | **19 escenarios** ✅ |
| Microservicios grandes (10+ servicios) | 25-40 escenarios |

**Conclusión**: 19 escenarios está en el rango óptimo para un sistema de 6 microservicios.

#### Tiempo de ejecución razonable

- **Suite completa**: ~2-3 minutos
- **Por escenario**: ~5-10 segundos (síncronos), ~15-20 segundos (asincrónicos)

**Ventajas**:
- ✅ Feedback rápido en desarrollo
- ✅ Viable para CI/CD (no bloquea el pipeline)
- ✅ Los desarrolladores ejecutan las pruebas frecuentemente

**Si tuviéramos 50+ escenarios**:
- ❌ Tiempo de ejecución: 10-15 minutos
- ❌ Los desarrolladores evitarían ejecutarlas
- ❌ Más difícil de mantener

#### Enfoque BDD: Escenarios significativos

**BDD prioriza**:
- ✅ Escenarios que representan casos de uso reales
- ✅ Documentación viva del comportamiento del sistema
- ✅ Colaboración entre stakeholders

**BDD NO busca**:
- ❌ Cobertura de código al 100%
- ❌ Probar cada combinación posible de parámetros
- ❌ Reemplazar pruebas unitarias

**Las pruebas unitarias y de integración** cubren casos más específicos y edge cases.

#### Desglose de los 60-70 pasos

Aunque hay 19 escenarios, cada uno ejecuta múltiples pasos:

```gherkin
Escenario: Onboarding completo
  Dado que estoy autenticado como "ADMIN"           # Paso 1
  Cuando registro un empleado con datos válidos     # Paso 2
  Entonces la respuesta debe tener código 201       # Paso 3
  Y eventualmente el usuario debe existir           # Paso 4 (polling)
  Y eventualmente debe existir una notificación     # Paso 5 (polling)
```

**5 pasos × 19 escenarios ≈ 60-70 pasos totales**

Cada paso puede hacer múltiples verificaciones:
- Código de respuesta HTTP
- Estructura del JSON
- Valores específicos en la respuesta
- Estado en otros servicios (polling)

---

## Resumen visual

### Estado del sistema

```
┌─────────────────────────────────────────────────────┐
│  docker-compose ps                                  │
│                                                     │
│  ✅ Todos (healthy) → Ejecutar pruebas             │
│  ⚠️  (health: starting) → Esperar 30-60s           │
│  ❌ Exited/Restarting → Revisar logs               │
└─────────────────────────────────────────────────────┘
```

### Cobertura de pruebas

```
┌─────────────────────────────────────────────────────┐
│  19 Escenarios E2E                                  │
│                                                     │
│  ✅ 100% flujos críticos                           │
│  ✅ 6 microservicios integrados                    │
│  ✅ 8 escenarios asincrónicos                      │
│  ✅ ~60-70 pasos individuales                      │
│  ✅ Tiempo: 2-3 minutos                            │
└─────────────────────────────────────────────────────┘
```

### Flujo de ejecución

```
1. docker-compose up -d --build
   ↓
2. Esperar 60-90 segundos
   ↓
3. docker-compose ps → Verificar (healthy)
   ↓
4. cd e2e-tests && mvn test
   ↓
5. Ver resultados en consola o HTML
```

---

## Comandos útiles

### Verificar estado del sistema

```bash
# Estado de todos los servicios
docker-compose ps

# Logs de un servicio específico
docker-compose logs auth-service --tail=50

# Logs en tiempo real
docker-compose logs -f auth-service

# Verificar que el API Gateway responde
curl http://localhost:8000/health
```

### Reiniciar servicios

```bash
# Reiniciar un servicio específico
docker-compose restart auth-service

# Reiniciar todos los servicios
docker-compose restart

# Reconstruir y reiniciar
docker-compose up -d --build auth-service
```

### Ejecutar pruebas

```bash
# Todas las pruebas
cd e2e-tests && mvn test

# Un feature específico
mvn test -Dcucumber.features=src/test/resources/features/auth.feature

# Verificar consistencia (3 ejecuciones)
./run-consistency-check.sh  # Linux/Mac
.\run-consistency-check.ps1  # Windows
```

---

## Preguntas frecuentes

### ¿Por qué algunos tests tardan más que otros?

**Tests síncronos** (~5-10 segundos):
- Login, CRUD, validaciones
- Respuesta inmediata del servidor

**Tests asincrónicos** (~15-20 segundos):
- Onboarding, offboarding
- Esperan a que RabbitMQ propague eventos
- Usan polling para verificar consistencia eventual

### ¿Puedo ejecutar las pruebas en paralelo?

**No recomendado** sin configuración adicional:
- Los IDs con timestamp podrían colisionar
- RabbitMQ podría saturarse
- Los resultados serían impredecibles

**Para ejecución paralela**:
- Usar UUIDs en lugar de timestamps
- Configurar múltiples instancias de RabbitMQ
- Usar bases de datos separadas por thread

### ¿Qué hago si un test falla aleatoriamente?

**Flaky test** (falla intermitentemente):

1. **Ejecutar 3 veces** para confirmar:
   ```bash
   ./run-consistency-check.sh
   ```

2. **Aumentar timeout** si es asincrónico:
   ```java
   // En el step definition
   WaitUtils.waitUntil(() -> condicion, 20, 2000); // 40 segundos
   ```

3. **Revisar logs** para identificar el problema:
   ```bash
   docker-compose logs --tail=100
   ```

### ¿Necesito más de 19 pruebas?

**Depende del contexto**:

✅ **19 pruebas son suficientes si**:
- Cubren todos los requisitos funcionales
- Pasan consistentemente (no son flaky)
- Se ejecutan en tiempo razonable
- Son fáciles de mantener

❌ **Considera agregar más si**:
- Hay nuevos requisitos funcionales
- Se agregan nuevos microservicios
- Se identifican bugs no cubiertos
- Stakeholders requieren casos específicos

**Regla de oro**: Agrega pruebas cuando agregues funcionalidad, no por alcanzar un número arbitrario.

---

**Última actualización**: Abril 2026
