package com.empresa.departamentos.controller;

import com.empresa.departamentos.dto.DepartamentoRequest;
import com.empresa.departamentos.dto.DepartamentoResponse;
import com.empresa.departamentos.service.DepartamentoService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.persistence.EntityNotFoundException;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@Tag(name = "Departamentos", description = "Operaciones CRUD sobre departamentos organizacionales")
public class DepartamentoController {

    private final DepartamentoService service;

    public DepartamentoController(DepartamentoService service) {
        this.service = service;
    }

    // ─────────────────────────────────────
    // Health Check
    // ─────────────────────────────────────
    @GetMapping("/")
    @Tag(name = "Diagnóstico")
    @Operation(summary = "Health Check", description = "Verifica que el servicio de departamentos está activo y responde correctamente.")
    @ApiResponse(responseCode = "200", description = "Servicio operativo")
    public Map<String, String> healthCheck() {
        return Map.of(
                "status", "ok",
                "service", "departamentos-service",
                "version", "1.1.0",
                "docs", "/docs");
    }

    // ─────────────────────────────────────
    // Crear departamento
    // ─────────────────────────────────────
    @PostMapping("/departamentos")
    @Operation(summary = "Crear un nuevo departamento", description = "Registra un nuevo departamento en la base de datos. "
            + "El campo id es definido manualmente y debe ser único.")
    @ApiResponses({
            @ApiResponse(responseCode = "201", description = "Departamento creado satisfactoriamente"),
            @ApiResponse(responseCode = "400", description = "El ID del departamento ya existe o datos inválidos", content = @Content(schema = @Schema(implementation = Map.class))),
            @ApiResponse(responseCode = "422", description = "Error de validación en los datos enviados"),
            @ApiResponse(responseCode = "500", description = "Error interno del servidor")
    })
    public ResponseEntity<DepartamentoResponse> crearDepartamento(
            @Valid @RequestBody DepartamentoRequest request) {
        DepartamentoResponse response = service.crear(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    // ─────────────────────────────────────
    // Listar todos los departamentos
    // ─────────────────────────────────────
    @GetMapping("/departamentos")
    @Operation(summary = "Listar todos los departamentos", description = "Retorna la lista completa de todos los departamentos registrados en el sistema.")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Lista de departamentos obtenida exitosamente"),
            @ApiResponse(responseCode = "500", description = "Error interno del servidor")
    })
    public List<DepartamentoResponse> listarDepartamentos() {
        return service.listarTodos();
    }

    // ─────────────────────────────────────
    // Obtener departamento por ID
    // ─────────────────────────────────────
    @GetMapping("/departamentos/{id}")
    @Operation(summary = "Obtener un departamento por ID", description = "Busca y retorna un departamento específico mediante su identificador único.")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Departamento encontrado y retornado exitosamente"),
            @ApiResponse(responseCode = "404", description = "No existe ningún departamento con el ID proporcionado", content = @Content(schema = @Schema(implementation = Map.class))),
            @ApiResponse(responseCode = "500", description = "Error interno del servidor")
    })
    public DepartamentoResponse obtenerDepartamento(@PathVariable String id) {
        return service.obtenerPorId(id);
    }

    // ─────────────────────────────────────
    // Actualizar departamento
    // ─────────────────────────────────────
    @PutMapping("/departamentos/{id}")
    @Operation(summary = "Actualizar un departamento", description = "Actualiza la información de un departamento existente.")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Departamento actualizado exitosamente"),
            @ApiResponse(responseCode = "404", description = "No existe ningún departamento con el ID proporcionado"),
            @ApiResponse(responseCode = "422", description = "Error de validación en los datos enviados"),
            @ApiResponse(responseCode = "500", description = "Error interno del servidor")
    })
    public ResponseEntity<DepartamentoResponse> actualizarDepartamento(
            @PathVariable String id,
            @Valid @RequestBody DepartamentoRequest request) {
        DepartamentoResponse response = service.actualizar(id, request);
        return ResponseEntity.ok(response);
    }

    // ─────────────────────────────────────
    // Eliminar departamento
    // ─────────────────────────────────────
    @DeleteMapping("/departamentos/{id}")
    @Operation(summary = "Eliminar un departamento", description = "Elimina un departamento del sistema por su ID.")
    @ApiResponses({
            @ApiResponse(responseCode = "204", description = "Departamento eliminado exitosamente"),
            @ApiResponse(responseCode = "404", description = "No existe ningún departamento con el ID proporcionado"),
            @ApiResponse(responseCode = "500", description = "Error interno del servidor")
    })
    public ResponseEntity<Void> eliminarDepartamento(@PathVariable String id) {
        service.eliminar(id);
        return ResponseEntity.noContent().build();
    }
}
