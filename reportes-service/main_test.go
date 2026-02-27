package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"go.uber.org/zap"
)

// ─────────────────────────────────────────────────────────────────────────────
// Configuración de tests
// ─────────────────────────────────────────────────────────────────────────────

func init() {
	// Inicializar logger para tests (modo development)
	var err error
	logger, err = zap.NewDevelopment()
	if err != nil {
		panic(err)
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests de Health Check básico
// ─────────────────────────────────────────────────────────────────────────────

func TestHealthHandler(t *testing.T) {
	t.Run("debe retornar estado OK", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/", nil)
		rec := httptest.NewRecorder()

		healthHandler(rec, req)

		// Verificar código de estado
		if rec.Code != http.StatusOK {
			t.Errorf("esperaba status %d, obtuvo %d", http.StatusOK, rec.Code)
		}

		// Verificar Content-Type
		contentType := rec.Header().Get("Content-Type")
		if contentType != "application/json" {
			t.Errorf("esperaba Content-Type application/json, obtuvo %s", contentType)
		}

		// Deserializar respuesta
		var response HealthResponse
		if err := json.NewDecoder(rec.Body).Decode(&response); err != nil {
			t.Fatalf("error al decodificar respuesta: %v", err)
		}

		// Verificar campos
		if response.Status != "ok" {
			t.Errorf("esperaba status 'ok', obtuvo '%s'", response.Status)
		}
		if response.Service != "reportes-service" {
			t.Errorf("esperaba service 'reportes-service', obtuvo '%s'", response.Service)
		}
		if response.Version != "1.0.0" {
			t.Errorf("esperaba version '1.0.0', obtuvo '%s'", response.Version)
		}
		if response.Docs != "/docs/index.html" {
			t.Errorf("esperaba docs '/docs/index.html', obtuvo '%s'", response.Docs)
		}
	})
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests de Health Check detallado
// ─────────────────────────────────────────────────────────────────────────────

func TestDetailedHealthHandler(t *testing.T) {
	t.Run("debe retornar healthy cuando los servicios están disponibles", func(t *testing.T) {
		// Mock del servicio de empleados
		empleadosServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode([]Empleado{
				{ID: "1", Nombre: "Juan"},
			})
		}))
		defer empleadosServer.Close()

		// Mock del servicio de departamentos
		departamentosServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode([]Departamento{
				{ID: "IT", Nombre: "Tecnología"},
			})
		}))
		defer departamentosServer.Close()

		// Configurar variables de entorno para tests
		t.Setenv("EMPLEADOS_SERVICE_URL", empleadosServer.URL)
		t.Setenv("DEPARTAMENTOS_SERVICE_URL", departamentosServer.URL)

		req := httptest.NewRequest(http.MethodGet, "/health", nil)
		rec := httptest.NewRecorder()

		detailedHealthHandler(rec, req)

		// Verificar código de estado
		if rec.Code != http.StatusOK {
			t.Errorf("esperaba status %d, obtuvo %d", http.StatusOK, rec.Code)
		}

		// Deserializar respuesta
		var response DetailedHealthResponse
		if err := json.NewDecoder(rec.Body).Decode(&response); err != nil {
			t.Fatalf("error al decodificar respuesta: %v", err)
		}

		// Verificar estado
		if response.Status != "healthy" {
			t.Errorf("esperaba status 'healthy', obtuvo '%s'", response.Status)
		}

		// Verificar checks
		if response.Checks["empleados_service"] != "ok" {
			t.Errorf("esperaba empleados_service 'ok', obtuvo '%s'", response.Checks["empleados_service"])
		}
		if response.Checks["departamentos_service"] != "ok" {
			t.Errorf("esperaba departamentos_service 'ok', obtuvo '%s'", response.Checks["departamentos_service"])
		}
	})

	t.Run("debe retornar degraded cuando un servicio no está disponible", func(t *testing.T) {
		// Mock del servicio de empleados que falla
		empleadosServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusInternalServerError)
		}))
		defer empleadosServer.Close()

		// Mock del servicio de departamentos OK
		departamentosServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode([]Departamento{})
		}))
		defer departamentosServer.Close()

		// Configurar variables de entorno
		t.Setenv("EMPLEADOS_SERVICE_URL", empleadosServer.URL)
		t.Setenv("DEPARTAMENTOS_SERVICE_URL", departamentosServer.URL)

		req := httptest.NewRequest(http.MethodGet, "/health", nil)
		rec := httptest.NewRecorder()

		detailedHealthHandler(rec, req)

		// Verificar código de estado
		if rec.Code != http.StatusServiceUnavailable {
			t.Errorf("esperaba status %d, obtuvo %d", http.StatusServiceUnavailable, rec.Code)
		}

		// Deserializar respuesta
		var response DetailedHealthResponse
		if err := json.NewDecoder(rec.Body).Decode(&response); err != nil {
			t.Fatalf("error al decodificar respuesta: %v", err)
		}

		// Verificar estado
		if response.Status != "degraded" {
			t.Errorf("esperaba status 'degraded', obtuvo '%s'", response.Status)
		}

		// Verificar que se detectó el error
		if response.Checks["empleados_service"] == "ok" {
			t.Error("esperaba que empleados_service tenga error, pero está 'ok'")
		}
	})
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests de Resumen
// ─────────────────────────────────────────────────────────────────────────────

func TestResumenHandler(t *testing.T) {
	t.Run("debe generar resumen correctamente", func(t *testing.T) {
		// Mock del servicio de empleados
		empleadosServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			empleados := []Empleado{
				{ID: "1", Nombre: "Juan Pérez"},
				{ID: "2", Nombre: "María García"},
				{ID: "3", Nombre: "Carlos López"},
			}
			json.NewEncoder(w).Encode(empleados)
		}))
		defer empleadosServer.Close()

		// Mock del servicio de departamentos
		departamentosServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			departamentos := []Departamento{
				{ID: "IT", Nombre: "Tecnología"},
				{ID: "HR", Nombre: "Recursos Humanos"},
			}
			json.NewEncoder(w).Encode(departamentos)
		}))
		defer departamentosServer.Close()

		// Configurar variables de entorno
		t.Setenv("EMPLEADOS_SERVICE_URL", empleadosServer.URL)
		t.Setenv("DEPARTAMENTOS_SERVICE_URL", departamentosServer.URL)

		req := httptest.NewRequest(http.MethodGet, "/reportes/resumen", nil)
		rec := httptest.NewRecorder()

		resumenHandler(rec, req)

		// Verificar código de estado
		if rec.Code != http.StatusOK {
			t.Errorf("esperaba status %d, obtuvo %d", http.StatusOK, rec.Code)
		}

		// Deserializar respuesta
		var response ResumenResponse
		if err := json.NewDecoder(rec.Body).Decode(&response); err != nil {
			t.Fatalf("error al decodificar respuesta: %v", err)
		}

		// Verificar conteos
		if response.TotalEmpleados != 3 {
			t.Errorf("esperaba 3 empleados, obtuvo %d", response.TotalEmpleados)
		}
		if response.TotalDepartamentos != 2 {
			t.Errorf("esperaba 2 departamentos, obtuvo %d", response.TotalDepartamentos)
		}

		// Verificar fuentes
		if response.FuenteEmpleados != empleadosServer.URL {
			t.Errorf("esperaba fuente empleados '%s', obtuvo '%s'", empleadosServer.URL, response.FuenteEmpleados)
		}
		if response.FuenteDepartamentos != departamentosServer.URL {
			t.Errorf("esperaba fuente departamentos '%s', obtuvo '%s'", departamentosServer.URL, response.FuenteDepartamentos)
		}

		// Verificar que la fecha es reciente
		if time.Since(response.FechaConsulta) > 5*time.Second {
			t.Error("la fecha de consulta no es reciente")
		}
	})

	t.Run("debe retornar error cuando servicio de empleados falla", func(t *testing.T) {
		// Mock del servicio de empleados que falla
		empleadosServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusInternalServerError)
		}))
		defer empleadosServer.Close()

		// Mock del servicio de departamentos OK
		departamentosServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode([]Departamento{})
		}))
		defer departamentosServer.Close()

		t.Setenv("EMPLEADOS_SERVICE_URL", empleadosServer.URL)
		t.Setenv("DEPARTAMENTOS_SERVICE_URL", departamentosServer.URL)

		req := httptest.NewRequest(http.MethodGet, "/reportes/resumen", nil)
		rec := httptest.NewRecorder()

		resumenHandler(rec, req)

		// Verificar código de estado
		if rec.Code != http.StatusInternalServerError {
			t.Errorf("esperaba status %d, obtuvo %d", http.StatusInternalServerError, rec.Code)
		}

		// Deserializar respuesta de error
		var response ErrorResponse
		if err := json.NewDecoder(rec.Body).Decode(&response); err != nil {
			t.Fatalf("error al decodificar respuesta: %v", err)
		}

		// Verificar mensaje de error
		if response.Error == "" {
			t.Error("esperaba mensaje de error, obtuvo cadena vacía")
		}
	})

	t.Run("debe retornar error cuando servicio de departamentos falla", func(t *testing.T) {
		// Mock del servicio de empleados OK
		empleadosServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode([]Empleado{})
		}))
		defer empleadosServer.Close()

		// Mock del servicio de departamentos que falla
		departamentosServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusInternalServerError)
		}))
		defer departamentosServer.Close()

		t.Setenv("EMPLEADOS_SERVICE_URL", empleadosServer.URL)
		t.Setenv("DEPARTAMENTOS_SERVICE_URL", departamentosServer.URL)

		req := httptest.NewRequest(http.MethodGet, "/reportes/resumen", nil)
		rec := httptest.NewRecorder()

		resumenHandler(rec, req)

		// Verificar código de estado
		if rec.Code != http.StatusInternalServerError {
			t.Errorf("esperaba status %d, obtuvo %d", http.StatusInternalServerError, rec.Code)
		}

		// Deserializar respuesta de error
		var response ErrorResponse
		if err := json.NewDecoder(rec.Body).Decode(&response); err != nil {
			t.Fatalf("error al decodificar respuesta: %v", err)
		}

		// Verificar mensaje de error
		if response.Error == "" {
			t.Error("esperaba mensaje de error, obtuvo cadena vacía")
		}
	})

	t.Run("debe manejar correctamente respuestas vacías", func(t *testing.T) {
		// Mock con arrays vacíos
		empleadosServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode([]Empleado{})
		}))
		defer empleadosServer.Close()

		departamentosServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode([]Departamento{})
		}))
		defer departamentosServer.Close()

		t.Setenv("EMPLEADOS_SERVICE_URL", empleadosServer.URL)
		t.Setenv("DEPARTAMENTOS_SERVICE_URL", departamentosServer.URL)

		req := httptest.NewRequest(http.MethodGet, "/reportes/resumen", nil)
		rec := httptest.NewRecorder()

		resumenHandler(rec, req)

		// Verificar código de estado
		if rec.Code != http.StatusOK {
			t.Errorf("esperaba status %d, obtuvo %d", http.StatusOK, rec.Code)
		}

		// Deserializar respuesta
		var response ResumenResponse
		if err := json.NewDecoder(rec.Body).Decode(&response); err != nil {
			t.Fatalf("error al decodificar respuesta: %v", err)
		}

		// Verificar conteos
		if response.TotalEmpleados != 0 {
			t.Errorf("esperaba 0 empleados, obtuvo %d", response.TotalEmpleados)
		}
		if response.TotalDepartamentos != 0 {
			t.Errorf("esperaba 0 departamentos, obtuvo %d", response.TotalDepartamentos)
		}
	})
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests de funciones auxiliares
// ─────────────────────────────────────────────────────────────────────────────

func TestGetEmpleadosURL(t *testing.T) {
	t.Run("debe usar variable de entorno si está configurada", func(t *testing.T) {
		expected := "http://custom-empleados:9000"
		t.Setenv("EMPLEADOS_SERVICE_URL", expected)

		url := getEmpleadosURL()
		if url != expected {
			t.Errorf("esperaba URL '%s', obtuvo '%s'", expected, url)
		}
	})

	t.Run("debe usar URL por defecto si variable de entorno no está configurada", func(t *testing.T) {
		// Limpiar variable de entorno
		t.Setenv("EMPLEADOS_SERVICE_URL", "")

		expected := "http://empleados-service:8000"
		url := getEmpleadosURL()
		if url != expected {
			t.Errorf("esperaba URL por defecto '%s', obtuvo '%s'", expected, url)
		}
	})
}

func TestGetDepartamentosURL(t *testing.T) {
	t.Run("debe usar variable de entorno si está configurada", func(t *testing.T) {
		expected := "http://custom-departamentos:9080"
		t.Setenv("DEPARTAMENTOS_SERVICE_URL", expected)

		url := getDepartamentosURL()
		if url != expected {
			t.Errorf("esperaba URL '%s', obtuvo '%s'", expected, url)
		}
	})

	t.Run("debe usar URL por defecto si variable de entorno no está configurada", func(t *testing.T) {
		// Limpiar variable de entorno
		t.Setenv("DEPARTAMENTOS_SERVICE_URL", "")

		expected := "http://departamentos-service:8080"
		url := getDepartamentosURL()
		if url != expected {
			t.Errorf("esperaba URL por defecto '%s', obtuvo '%s'", expected, url)
		}
	})
}

func TestTestConnection(t *testing.T) {
	t.Run("debe retornar nil cuando la conexión es exitosa", func(t *testing.T) {
		server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusOK)
		}))
		defer server.Close()

		err := testConnection(server.URL)
		if err != nil {
			t.Errorf("esperaba nil, obtuvo error: %v", err)
		}
	})

	t.Run("debe retornar error cuando el servicio responde 500", func(t *testing.T) {
		server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusInternalServerError)
		}))
		defer server.Close()

		err := testConnection(server.URL)
		if err == nil {
			t.Error("esperaba error, obtuvo nil")
		}
	})

	t.Run("debe retornar error cuando la URL es inválida", func(t *testing.T) {
		err := testConnection("http://localhost:99999/invalid")
		if err == nil {
			t.Error("esperaba error por URL inválida, obtuvo nil")
		}
	})
}
