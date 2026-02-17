# Servidor de Empleados - API REST

Sistema backend para la gestión de empleados desarrollado con FastAPI y Docker.

## 📁 Estructura del Proyecto

```
reto1/
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── empleado.py          # Modelos Pydantic
│   ├── routes/
│   │   ├── __init__.py
│   │   └── empleados.py         # Endpoints de empleados
│   └── database.py              # Almacenamiento en memoria
├── main.py                      # Punto de entrada de la aplicación
├── requirements.txt             # Dependencias
├── Dockerfile                   # Configuración Docker
└── .dockerignore               # Exclusiones Docker
```

## 🚀 Endpoints Disponibles

### 1. Registrar un empleado
- **Método**: `POST`
- **Ruta**: `/empleados`
- **Body**:
```json
{
  "id": 1,
  "nombre": "Juan Pérez",
  "cargo": "Desarrollador"
}
```
- **Respuesta**: `200 OK` con los datos del empleado registrado

### 2. Obtener todos los empleados
- **Método**: `GET`
- **Ruta**: `/empleados`
- **Respuesta**: `200 OK` con array de empleados (puede estar vacío)

### 3. Consultar empleado por ID
- **Método**: `GET`
- **Ruta**: `/empleados/{id}`
- **Respuesta**: 
  - `200 OK` con datos del empleado
  - `404 Not Found` si no existe: `{"detail": "El empleado con id {id} no existe"}`

### 4. Rutas no soportadas
- **Respuesta**: `404 Not Found` con `{"detail": "Recurso no encontrado"}`

## 🐳 Ejecución con Docker

```bash
# Construir la imagen
docker build -t servidor-empleados .

# Ejecutar el contenedor
docker run -p 8080:8080 servidor-empleados
```

El servidor estará disponible en `http://localhost:8080`

## 💻 Ejecución Local (Sin Docker)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
uvicorn main:app --host 0.0.0.0 --port 8080
```

## 📚 Documentación Interactiva

FastAPI genera documentación automática:
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

## 🧪 Ejemplos de Pruebas

### Usando curl

```bash
# Registrar empleado
curl -X POST http://localhost:8080/empleados \
  -H "Content-Type: application/json" \
  -d '{"id": 1, "nombre": "Juan Pérez", "cargo": "Desarrollador"}'

# Obtener todos los empleados
curl http://localhost:8080/empleados

# Consultar empleado específico
curl http://localhost:8080/empleados/1

# Probar empleado inexistente
curl http://localhost:8080/empleados/999
```

## 🏗️ Arquitectura

El proyecto sigue las buenas prácticas de desarrollo con FastAPI:

- **Separación de responsabilidades**: Modelos, rutas y lógica de datos en módulos independientes
- **Validación automática**: Uso de Pydantic para validación de datos
- **Documentación automática**: OpenAPI/Swagger generado automáticamente
- **Código limpio**: Estructura modular y escalable

## 🛠️ Tecnologías

- **FastAPI**: Framework web moderno y rápido
- **Uvicorn**: Servidor ASGI de alto rendimiento
- **Pydantic**: Validación de datos con Python type hints
- **Docker**: Contenedorización de la aplicación
