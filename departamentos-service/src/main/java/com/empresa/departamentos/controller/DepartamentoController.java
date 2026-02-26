package com.empresa.departamentos.controller;

import com.empresa.departamentos.dto.DepartamentoRequest;
import com.empresa.departamentos.dto.DepartamentoResponse;
import com.empresa.departamentos.model.Departamento;
import com.empresa.departamentos.repository.DepartamentoRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;

@RestController
@Tag(name = "Departamentos", description = "Operaciones CRUD sobre departamentos organizacionales")
public class DepartamentoController {

    private final DepartamentoRepository repository;

    public DepartamentoController(DepartamentoRepository repository) {
        this.repository = repository;
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

        // Verificar si el ID ya existe
        if (repository.existsById(request.getId())) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Ya existe un departamento con el ID '" + request.getId() + "'.");
        }

        Departamento departamento = Departamento.builder()
                .id(request.getId())
                .nombre(request.getNombre())
                .descripcion(request.getDescripcion())
                .build();

        Departamento guardado = repository.save(departamento);

        return ResponseEntity.status(HttpStatus.CREATED)
                .body(toResponse(guardado));
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
        return repository.findAll().stream()
                .map(this::toResponse)
                .toList();
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
        Departamento departamento = repository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "Departamento con ID '" + id + "' no encontrado"));
        return toResponse(departamento);
    }

    // ─────────────────────────────────────
    // Helper: Entity → DTO
    // ─────────────────────────────────────
    private DepartamentoResponse toResponse(Departamento entity) {
        return DepartamentoResponse.builder()
                .id(entity.getId())
                .nombre(entity.getNombre())
                .descripcion(entity.getDescripcion())
                .build();
    }
}
