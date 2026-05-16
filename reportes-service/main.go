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
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	httpSwagger "github.com/swaggo/http-swagger"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/zipkin"
	"go.opentelemetry.io/otel/propagation"
	sdkresource "go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
	"go.uber.org/zap"

	_ "reportes-service/docs"
)

// Logger global estructurado en JSON
var logger *zap.Logger

// ── Métricas Prometheus ──
var (
	peticionesTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "http_requests_total",
		Help: "Total de peticiones HTTP recibidas",
	}, []string{"method", "path", "status_code"})

	duracionPeticion = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "http_request_duration_seconds",
		Help:    "Duración de peticiones HTTP en segundos",
		Buckets: prometheus.DefBuckets,
	}, []string{"method", "path"})
)

// escritorRespuesta captura el código de estado HTTP para las métricas
type escritorRespuesta struct {
	http.ResponseWriter
	codigo int
}

func (e *escritorRespuesta) WriteHeader(codigo int) {
	e.codigo = codigo
	e.ResponseWriter.WriteHeader(codigo)
}

// middlewareMetricas registra métricas HTTP por cada petición
func middlewareMetricas(ruta string, siguiente http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		inicio := time.Now()
		ew := &escritorRespuesta{ResponseWriter: w, codigo: http.StatusOK}
		siguiente.ServeHTTP(ew, r)
		duracion := time.Since(inicio).Seconds()
		duracionPeticion.WithLabelValues(r.Method, ruta).Observe(duracion)
		peticionesTotal.WithLabelValues(r.Method, ruta, strconv.Itoa(ew.codigo)).Inc()
	})
}

// iniciarTrazabilidad configura OpenTelemetry con exportador Zipkin
func iniciarTrazabilidad() (func(context.Context) error, error) {
	endpointZipkin := os.Getenv("OTEL_EXPORTER_ZIPKIN_ENDPOINT")
	if endpointZipkin == "" {
		endpointZipkin = "http://zipkin:9411/api/v2/spans"
	}
	nombreServicio := os.Getenv("OTEL_SERVICE_NAME")
	if nombreServicio == "" {
		nombreServicio = "reportes-service"
	}

	exportador, err := zipkin.New(endpointZipkin)
	if err != nil {
		return nil, err
	}

	recurso, _ := sdkresource.New(context.Background(),
		sdkresource.WithAttributes(semconv.ServiceName(nombreServicio)),
	)

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exportador),
		sdktrace.WithResource(recurso),
	)
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.TraceContext{})
	return tp.Shutdown, nil
}

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

// DetailedHealthResponse representa el health check detallado
type DetailedHealthResponse struct {
	Status  string            `json:"status" example:"healthy"`
	Service string            `json:"service" example:"reportes-service"`
	Version string            `json:"version" example:"1.0.0"`
	Checks  map[string]string `json:"checks"`
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

// detailedHealthHandler verifica la conectividad con servicios dependientes
//
//	@Summary		Health Check detallado
//	@Description	Verifica el estado del servicio y la conectividad con empleados y departamentos.
//	@Tags			Diagnóstico
//	@Produce		json
//	@Success		200	{object}	DetailedHealthResponse	"Servicio saludable"
//	@Failure		503	{object}	DetailedHealthResponse	"Servicio degradado"
//	@Router			/health [get]
func detailedHealthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	checks := make(map[string]string)
	allHealthy := true

	// Verificar conectividad con servicio de empleados
	empleadosURL := getEmpleadosURL() + "/empleados?pagina=1&por_pagina=1"
	if err := testConnection(empleadosURL); err != nil {
		checks["empleados_service"] = fmt.Sprintf("error: %v", err)
		allHealthy = false
	} else {
		checks["empleados_service"] = "ok"
	}

	// Verificar conectividad con servicio de departamentos
	departamentosURL := getDepartamentosURL() + "/departamentos"
	if err := testConnection(departamentosURL); err != nil {
		checks["departamentos_service"] = fmt.Sprintf("error: %v", err)
		allHealthy = false
	} else {
		checks["departamentos_service"] = "ok"
	}

	status := "healthy"
	statusCode := http.StatusOK
	if !allHealthy {
		status = "degraded"
		statusCode = http.StatusServiceUnavailable
	}

	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(DetailedHealthResponse{
		Status:  status,
		Service: "reportes-service",
		Version: "1.0.0",
		Checks:  checks,
	})
}

// testConnection verifica si un endpoint responde
func testConnection(url string) error {
	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 500 {
		return fmt.Errorf("service returned %d", resp.StatusCode)
	}
	return nil
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

	logger.Info("Solicitud de resumen del sistema", zap.String("event", "resumen_request"))

	var empleados []Empleado
	var departamentos []Departamento

	// Consultar servicio de empleados
	empleadosURL := getEmpleadosURL() + "/empleados"
	if err := fetchJSON(empleadosURL, &empleados); err != nil {
		logger.Error("Error consultando empleados",
			zap.Error(err),
			zap.String("event", "empleados_fetch_error"),
			zap.String("url", empleadosURL),
		)
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
		logger.Error("Error consultando departamentos",
			zap.Error(err),
			zap.String("event", "departamentos_fetch_error"),
			zap.String("url", departamentosURL),
		)
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ErrorResponse{
			Error:  "Error consultando servicio de departamentos",
			Detail: err.Error(),
		})
		return
	}

	logger.Info("Resumen generado exitosamente",
		zap.String("event", "resumen_created"),
		zap.Int("total_empleados", len(empleados)),
		zap.Int("total_departamentos", len(departamentos)),
	)

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
	// Inicializar logger estructurado en JSON
	var err error
	logger, err = zap.NewProduction()
	if err != nil {
		panic(fmt.Sprintf("No se pudo inicializar el logger: %v", err))
	}
	defer logger.Sync()

	logger.Info("Inicializando reportes-service", zap.String("service", "reportes-service"))

	// Inicializar trazabilidad OpenTelemetry + Zipkin
	shutdownTracer, err := iniciarTrazabilidad()
	if err != nil {
		logger.Warn("No se pudo inicializar trazabilidad", zap.Error(err))
	} else {
		defer shutdownTracer(context.Background())
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "3000"
	}

	mux := http.NewServeMux()

	// Endpoints de negocio envueltos con métricas y tracing
	mux.Handle("/", middlewareMetricas("/", otelhttp.NewHandler(http.HandlerFunc(healthHandler), "/")))
	mux.Handle("/health", middlewareMetricas("/health", otelhttp.NewHandler(http.HandlerFunc(detailedHealthHandler), "/health")))
	mux.Handle("/reportes/resumen", middlewareMetricas("/reportes/resumen", otelhttp.NewHandler(http.HandlerFunc(resumenHandler), "/reportes/resumen")))

	// Endpoint de métricas Prometheus
	mux.Handle("/metrics", promhttp.Handler())

	// Swagger UI
	mux.Handle("/docs/", httpSwagger.Handler(
		httpSwagger.URL("/docs/doc.json"),
	))

	logger.Info("reportes-service corriendo",
		zap.String("url", fmt.Sprintf("http://localhost:%s", port)),
		zap.String("event", "server_started"),
		zap.String("port", port),
	)
	logger.Info("Swagger UI disponible",
		zap.String("url", fmt.Sprintf("http://localhost:%s/docs/index.html", port)),
		zap.String("event", "swagger_ready"),
	)

	if err := http.ListenAndServe(":"+port, mux); err != nil {
		logger.Fatal("Error al iniciar servidor",
			zap.Error(err),
			zap.String("event", "server_start_error"),
		)
	}
}
