# Reto 2 -- Orquestación de Servicios y Persistencia de Datos

## Contexto

Este reto continúa el desarrollo del sistema de onboarding y offboarding
de empleados. En el reto anterior se construyó un servicio básico para
la gestión de empleados y su despliegue en un contenedor Docker.

En este segundo reto se avanzará hacia una arquitectura más realista,
incorporando:

-   Orquestación de múltiples contenedores con Docker Compose
-   Persistencia de datos mediante una base de datos containerizada
-   Comunicación entre servicios independientes
-   Gestión de configuración mediante variables de entorno

------------------------------------------------------------------------

## Objetivo

Evolucionar el sistema desarrollado en el reto anterior hacia una
arquitectura de múltiples servicios orquestados, donde cada componente
se ejecute de forma aislada en su propio contenedor, se comuniquen entre
sí mediante la red interna de Docker, y los datos persistan más allá del
ciclo de vida de los contenedores.

------------------------------------------------------------------------

## Requisitos Generales

La solución desarrollada debe cumplir con los siguientes requisitos:

-   Definir la infraestructura completa en un archivo
    `docker-compose.yml`.
-   Implementar al menos dos servicios de negocio que se comuniquen
    entre sí.
-   Incluir una base de datos como servicio independiente para cada
    microservicio.
-   Garantizar la persistencia de datos mediante volúmenes Docker.
-   Utilizar variables de entorno para la configuración de los
    servicios.
-   Documentar los endpoints de ambos servicios utilizando OpenAPI
    (Swagger).
-   Permitir el despliegue completo mediante un único comando.

------------------------------------------------------------------------

## 1. Docker Compose

Crear un archivo `docker-compose.yml`, en este archivo se debe definir
toda la infraestructura:

### Servicios a incluir

``` yaml
services:
  empleados-service:
    # Servicio de gestión de empleados
    
  departamentos-service:
    # Servicio de gestión de departamentos
    
  database-empleados:
    # Base de datos (PostgreSQL, MySQL, MongoDB, etc.)

  database-departamentos:
    # Base de datos (PostgreSQL, MySQL, MongoDB, etc.)
```

Inicialmente empiece por registrar en su docker compose el servicio de
empleados desarrollado en el reto anterior.

### Requisitos del Compose

  Aspecto                Requisito
  ---------------------- --------------------------------------------------------------
  Redes                  Definir una red interna para la comunicación entre servicios
  Volúmenes              Configurar volumen para persistencia de la base de datos
  Variables de entorno   Configurar credenciales y URLs de conexión
  Dependencias           Usar `depends_on` para ordenar el inicio de servicios
  Puertos                Exponer solo los puertos necesarios al host

### Comandos

``` bash
docker-compose up --build
docker-compose down
```

------------------------------------------------------------------------

## 2. Servicio de Departamentos

Implementar un nuevo microservicio encargado de la gestión de
departamentos.

### Endpoints requeridos

  Método   Ruta                  Descripción
  -------- --------------------- --------------------------------
  POST     /departamentos        Registra un nuevo departamento
  GET      /departamentos/{id}   Consulta un departamento
  GET      /departamentos        Lista todos los departamentos

### Estructura

``` json
{
  "id": "string",
  "nombre": "string",
  "descripcion": "string"
}
```

### Respuestas

-   201 Created
-   200 OK
-   404 Not Found

### Base de datos

-   Base de datos independiente
-   Volumen persistente
-   Variables de entorno

------------------------------------------------------------------------

## 3. Servicio de Empleados

Evolucionar el servicio para:

-   Persistir datos en base de datos
-   Consultar servicio de departamentos
-   Usar variables de entorno

### Endpoints

  Método   Ruta
  -------- -----------------
  POST     /empleados
  GET      /empleados/{id}
  GET      /empleados

### Estructura

``` json
{
  "id": "string",
  "nombre": "string",
  "email": "string",
  "departamentoId": "string",
  "fechaIngreso": "date"
}
```

### Validación

Debe:

1.  Consultar servicio departamentos
2.  Retornar 400 si no existe
3.  Crear empleado si existe

Ejemplo URL interna:

    http://departamentos-service:8080/departamentos/{id}

------------------------------------------------------------------------

## 4. Resiliencia

Implementar:

-   Manejo de errores
-   Timeouts
-   Reintentos
-   Circuit breaker

------------------------------------------------------------------------

## 5. OpenAPI (Swagger)

Debe:

-   Documentar endpoints
-   Exponer Swagger UI
-   Definir schemas

Ejemplos:

    http://localhost:8080/docs
    http://localhost:8080/swagger-ui.html

------------------------------------------------------------------------

## 6. Pruebas

### Flujo

``` bash
docker-compose up --build
```

Crear departamento:

``` bash
curl -X POST http://localhost:8081/departamentos -H "Content-Type: application/json" -d '{"id":"IT","nombre":"Tecnologia","descripcion":"TI"}'
```

Crear empleado:

``` bash
curl -X POST http://localhost:8080/empleados
```

Verificar persistencia reiniciando contenedores.

------------------------------------------------------------------------

## Arquitectura

-   empleados-service
-   departamentos-service
-   database-empleados
-   database-departamentos
-   Docker Network
-   Volúmenes persistentes

------------------------------------------------------------------------

## Entregables

-   Código en GitHub
-   README.md por servicio
-   README.md sistema completo

------------------------------------------------------------------------

## Criterios de Evaluación

  Elemento                 Valor
  ------------------------ -------
  Docker Compose           1.0
  Servicio Departamentos   1.0
  Servicio Empleados       1.0
  Resiliencia              1.0
  Pruebas                  1.0

------------------------------------------------------------------------

**Fin del documento**
