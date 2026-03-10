# Documentación y Verificación - Reto 3

Este documento detalla las implementaciones realizadas por nuestro grupo para resolver los requerimientos del Reto 3. A continuación, se explican las decisiones arquitectónicas y la ubicación exacta del código correspondiente para su revisión.

---

## Dónde encontrar las implementaciones en el código

### 1. Message Broker (RabbitMQ)
* **Ubicación:** Archivo `docker-compose.yml` (ver servicio `rabbitmq-broker`).
* **Implementación:** Añadimos la imagen oficial de RabbitMQ basada en Alpine. Configuramos los puertos `5672` (comunicación AMQP) y `15672` (panel de administración visual). Además, configuramos la variable de entorno `RABBITMQ_URL` en todos los servicios dependientes (`empleados`, `notificaciones`, `perfiles`).
* **Decisión arquitectónica:** En el repositorio documentamos la justificación técnica de usar RabbitMQ, priorizando el desacoplamiento entre componentes, el procesamiento asíncrono y la robustez del patrón publicador/suscriptor para notificaciones inter-servicio de manera escalable.

### 2. Publicación de Eventos (empleados-service)
* **Ubicación:** Archivos `app/routes/empleados.py` y `app/broker.py` dentro de `empleados-service`.
* **Implementación:** Se modificaron los endpoints `POST /empleados` y `DELETE /empleados/{id}`. Al guardar o eliminar exitosamente un empleado en PostgreSQL, el endpoint invoca a la función `rabbitmq_client.publish_event`, publicando el evento `empleado.creado` o `empleado.eliminado`. Esta lógica asíncrona está envuelta en bloques `try/except` para garantizar que un fallo repentino en la red interna del broker no impida la transacción sincrónica en la base de datos principal de recursos humanos.

### 3. Servicio de Notificaciones (Consumidor)
* **Ubicación:** Archivo `src/index.js` dentro de `notificaciones-service`.
* **Implementación:** Creamos un nuevo microservicio en Node.js con Express orientado enteramente puramente a eventos. Mediante la función `initRabbitMQ()`, el servicio se suscribe a los eventos respectivos del broker.
    * Al atrapar un evento, inserta un registro histórico en la tabla `notificaciones` de su propia base de datos (PostgreSQL aislada en un contenedor Docker distinto).
    * Simula el envío de un correo electrónico imprimiendo el formato exacto requerido como un log estructurado en la salida de comandos utilizando la librería `winston`.
    * Expone métodos GET sincrónicos independientes (`/notificaciones` y `/notificaciones/{id}`) para la consulta del historial generado desde otros posibles clientes.

### 4. Servicio de Perfiles (Consumidor Parcial y API REST)
* **Ubicación:** Archivo `src/index.js` dentro de `perfiles-service`.
* **Implementación:** Diseñamos un microservicio Node.js/Express ejecutando patrones mixtos de comunicación:
    * **Asíncrona**: Escucha únicamente el evento `empleado.creado` en RabbitMQ y realiza una inserción por defecto en su PostgreSQL con los campos básicos enviados en el payload de este evento de dominio.
    * **Sincrónica**: Además, expone endpoints REST (`GET` y `PUT` expuestos en `/perfiles/{id}`) para consultar y enriquecer la información extendida del trabajador de manera independiente, desacoplando este dominio del servicio primario.

### 5. Swagger / OpenAPI
* **Ubicación:** Archivos `src/index.js` de los respectivos microservicios nuevos.
* **Implementación:** Añadimos `swagger-jsdoc` y `swagger-ui-express` a las dependencias. Utilizando notación integrada de JSDoc, cada endpoint quedó documentado directamente desde las funciones lógicas, exponiéndose en los siguientes puertos:
    * API Swagger Perfiles: `http://localhost:8084/api-docs`
    * API Swagger Notificaciones: `http://localhost:8082/api-docs`

### 6. Dockerización Completa
* **Ubicación:** Multi-stage `Dockerfile` insertado en cada carpeta y archivo integrador `docker-compose.yml`.
* **Implementación:** Los dos microservicios adicionales NodeJS se empaquetan en base `node:18-alpine`. Todo el ecosistema de contenedores, que abarca las 4 bases de datos relacionales requeridas en total, el broker y los 4 backends fueron vinculados mediante dependencias de estado `depends_on`, habilitando el despliegue automático del laboratorio entero mediante la ejecución de un simple `docker-compose up -d`.

---
---

## Demostración Funcional en Vivo

A continuación, documentamos la secuencia de comandos utilizada para someter a prueba el funcionamiento de todos los microservicios y del broker asíncrono con un nuevo registro de empleado (ID 42).

### Paso 1: Verificación del Broker
Autenticación en el panel visual activo de RabbitMQ mediante el explorador web:
* **Ruta de acceso:** http://localhost:15672 (Usuario/Clave: `guest`)

**Puntos clave:**
1. En la pestaña **Exchanges**: El exchange principal llamado `rrhh_events` configurado como tipo `topic`.
2. En la pestaña **Queues**: Las colas dedicadas que crearon los consumidores, llamadas `notificaciones_queue` y `perfiles_queue` (ambas operando activamente).
3. En la sección de **Bindings** (dentro del exchange `rrhh_events`): Las reglas de ruteo (`empleado.creado` y `empleado.eliminado`) están suscritas y apuntando correctamente a las colas respectivas.

### Paso 2: Creación del Empleado
Ejecución de la API central para la persistencia del perfil e instanciamiento automático de los eventos asíncronos en RabbitMQ.

```powershell
$bodyEmp = @{
    id = 42
    nombre = "Evaluador Externo"
    email = "evaluador@universidad.edu.co"
    departamento_id = $null
    cargo = "Auditor"
    salario = 6000.0
    fecha_ingreso = "2024-03-15T00:00:00"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/empleados' -ContentType 'application/json' -Body $bodyEmp
```

### Paso 3: Confirmación de Reacción a Eventos Sincrónicos
Verificación instantánea evidenciando que tanto el perfil autogenerado por omisión como la alerta de notificación fueron salvados en las otras BDD asíncronamente.

```powershell
Invoke-RestMethod -Method Get -Uri 'http://localhost:8084/perfiles/42'
```

```powershell
Invoke-RestMethod -Method Get -Uri 'http://localhost:8082/notificaciones/42'
```

### Paso 4: Extensión del Perfil (Protocolo REST Sincrónico)
Inserción explícita de campos faltantes mediante el recurso PUT desacoplado en el servicio del Perfil:

```powershell
$bodyUpdate = @{
    telefono = "+57 321 000 0000"
    ciudad = "Bogota"
    biografia = "Evaluador del Reto 3 de Arquitectura"
} | ConvertTo-Json

Invoke-RestMethod -Method Put -Uri 'http://localhost:8084/perfiles/42' -ContentType 'application/json' -Body $bodyUpdate
```

### Paso 5: Evidencia de Envíos de Correo
Auditoría del log simulado de comunicaciones por consola:

```powershell
docker logs notificaciones-service
```

### Paso 6: Evento de Desvinculación
Prueba paralela sobre el flujo `empleado.eliminado` llamando al core primario API.

```powershell
Invoke-RestMethod -Method Delete -Uri 'http://localhost:8080/empleados/42'
```

Lectura final del API de notificaciones determinando el registro del segundo correo simulado consecutivo en base de datos:

```powershell
Invoke-RestMethod -Method Get -Uri 'http://localhost:8082/notificaciones/42'
```

Listamos los empleados para verificar que se haya eliminado:

```powershell
Invoke-RestMethod -Method Get -Uri 'http://localhost:8080/empleados'
```