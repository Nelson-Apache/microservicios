// Package main implementa el Servicio de Reportes en Go.
//
//	@title			Servicio de Reportes
//	@version		1.0.0
//	@description	## Microservicio de Reportes\n\nGenera estadísticas y reportes del sistema consultando los demás microservicios.\n\n### Funcionalidades\n- Resumen de empleados y departamentos\n- Estadísticas del sistema en tiempo real
//	@contact.name	Equipo de Microservicios
//	@contact.email	soporte@empresa.com
//	@license.name	MIT
//	@host			localhost:8083
//	@BasePath		/
package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	httpSwagger "github.com/swaggo/http-swagger"

	_ "reportes-service/docs"
)

// ─────────────────────────────────────────────
// Estructuras de datos
// ─────────────────────────────────────────────

// HealthResponse representa la respuesta del health check
type HealthResponse struct {
	Status  string `json:"status" example:"ok"`
	Service string `json:"service" example:"reportes-service"`
	Version string `json:"version" example:"1.0.0"`
	Docs    string `json:"docs" example:"/docs/index.html"`
}

// ResumenResponse representa el resumen del sistema
type ResumenResponse struct {
	TotalDepartamentos int       `json:"totalDepartamentos" example:"5"`
	TotalEmpleados     int       `json:"totalEmpleados" example:"20"`
	FechaConsulta      time.Time `json:"fechaConsulta"`
	FuenteEmpleados    string    `json:"fuenteEmpleados" example:"http://empleados-service:8000"`
	FuenteDepartamentos string   `json:"fuenteDepartamentos" example:"http://departamentos-service:8080"`
}

// ErrorResponse representa un error de la API
type ErrorResponse struct {
	Error  string `json:"error" example:"Error de comunicación"`
	Detail string `json:"detail" example:"No se pudo contactar el servicio de empleados"`
}

// Departamento estructura para deserializar respuesta del servicio de departamentos
type Departamento struct {
	ID     string `json:"id"`
	Nombre string `json:"nombre"`
}

// Empleado estructura para deserializar respuesta del servicio de empleados
type Empleado struct {
	ID     string `json:"id"`
	Nombre string `json:"nombre"`
}

// ─────────────────────────────────────────────
// Configuración de URLs
// ─────────────────────────────────────────────
func getEmpleadosURL() string {
	url := os.Getenv("EMPLEADOS_SERVICE_URL")
	if url == "" {
		url = "http://empleados-service:8000"
	}
	return url
}

func getDepartamentosURL() string {
	url := os.Getenv("DEPARTAMENTOS_SERVICE_URL")
	if url == "" {
		url = "http://departamentos-service:8080"
	}
	return url
}

// ─────────────────────────────────────────────
// Cliente HTTP con timeout
// ─────────────────────────────────────────────
var httpClient = &http.Client{
	Timeout: 5 * time.Second,
}

func fetchJSON(url string, target interface{}) error {
	resp, err := httpClient.Get(url)
	if err != nil {
		return fmt.Errorf("error de red al consultar %s: %w", url, err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("error al leer respuesta de %s: %w", url, err)
	}

	return json.Unmarshal(body, target)
}

// ─────────────────────────────────────────────
// Handlers
// ─────────────────────────────────────────────

// healthHandler muestra el estado del servicio
//
//	@Summary		Health Check
//	@Description	Verifica que el servicio de reportes está activo y operativo.
//	@Tags			Diagnóstico
//	@Produce		json
//	@Success		200	{object}	HealthResponse
//	@Router			/ [get]
func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(HealthResponse{
		Status:  "ok",
		Service: "reportes-service",
		Version: "1.0.0",
		Docs:    "/docs/index.html",
	})
}

// resumenHandler genera el resumen estadístico del sistema
//
//	@Summary		Obtener resumen del sistema
//	@Description	Consulta los servicios de empleados y departamentos para generar un resumen estadístico del sistema.
//	@Tags			Reportes
//	@Produce		json
//	@Success		200	{object}	ResumenResponse	"Resumen estadístico generado exitosamente"
//	@Failure		500	{object}	ErrorResponse	"Error al consultar uno o más servicios"
//	@Router			/reportes/resumen [get]
func resumenHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	var empleados []Empleado
	var departamentos []Departamento

	// Consultar servicio de empleados
	empleadosURL := getEmpleadosURL() + "/empleados"
	if err := fetchJSON(empleadosURL, &empleados); err != nil {
		log.Printf("Error consultando empleados: %v", err)
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ErrorResponse{
			Error:  "Error consultando servicio de empleados",
			Detail: err.Error(),
		})
		return
	}

	// Consultar servicio de departamentos
	departamentosURL := getDepartamentosURL() + "/departamentos"
	if err := fetchJSON(departamentosURL, &departamentos); err != nil {
		log.Printf("Error consultando departamentos: %v", err)
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ErrorResponse{
			Error:  "Error consultando servicio de departamentos",
			Detail: err.Error(),
		})
		return
	}

	resumen := ResumenResponse{
		TotalEmpleados:      len(empleados),
		TotalDepartamentos:  len(departamentos),
		FechaConsulta:       time.Now(),
		FuenteEmpleados:     getEmpleadosURL(),
		FuenteDepartamentos: getDepartamentosURL(),
	}

	json.NewEncoder(w).Encode(resumen)
}

// ─────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────
func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "3000"
	}

	mux := http.NewServeMux()

	// Endpoints de negocio
	mux.HandleFunc("/", healthHandler)
	mux.HandleFunc("/reportes/resumen", resumenHandler)

	// Swagger UI
	mux.Handle("/docs/", httpSwagger.Handler(
		httpSwagger.URL("/docs/doc.json"),
	))

	log.Printf("✅ reportes-service corriendo en http://localhost:%s", port)
	log.Printf("📄 Swagger UI disponible en http://localhost:%s/docs/index.html", port)

	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatalf("Error al iniciar servidor: %v", err)
	}
}
