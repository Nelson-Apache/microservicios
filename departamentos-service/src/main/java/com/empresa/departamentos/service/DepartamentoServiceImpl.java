package com.empresa.departamentos.service;

import com.empresa.departamentos.dto.DepartamentoRequest;
import com.empresa.departamentos.dto.DepartamentoResponse;
import com.empresa.departamentos.model.Departamento;
import com.empresa.departamentos.repository.DepartamentoRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

/**
 * Implementación del servicio de departamentos.
 * Contiene la lógica de negocio para las operaciones CRUD.
 */
@Service
@Transactional
@Slf4j
public class DepartamentoServiceImpl implements DepartamentoService {

    private final DepartamentoRepository repository;

    public DepartamentoServiceImpl(DepartamentoRepository repository) {
        this.repository = repository;
    }

    @Override
    public DepartamentoResponse crear(DepartamentoRequest request) {
        log.info("Creando departamento con ID: {}", request.getId());

        // Validar que el ID no exista
        if (repository.existsById(request.getId())) {
            log.warn("Intento de crear departamento con ID duplicado: {}", request.getId());
            throw new IllegalArgumentException(
                    "Ya existe un departamento con el ID '" + request.getId() + "'."
            );
        }

        Departamento departamento = Departamento.builder()
                .id(request.getId())
                .nombre(request.getNombre())
                .descripcion(request.getDescripcion())
                .build();

        Departamento guardado = repository.save(departamento);
        log.info("Departamento creado exitosamente: {}", guardado.getId());

        return toResponse(guardado);
    }

    @Override
    @Transactional(readOnly = true)
    public List<DepartamentoResponse> listarTodos() {
        log.debug("Listando todos los departamentos");
        return repository.findAll().stream()
                .map(this::toResponse)
                .collect(Collectors.toList());
    }

    @Override
    @Transactional(readOnly = true)
    public DepartamentoResponse obtenerPorId(String id) {
        log.debug("Buscando departamento con ID: {}", id);
        Departamento departamento = repository.findById(id)
                .orElseThrow(() -> {
                    log.warn("Departamento no encontrado: {}", id);
                    return new EntityNotFoundException(
                            "Departamento con ID '" + id + "' no encontrado"
                    );
                });
        return toResponse(departamento);
    }

    @Override
    public DepartamentoResponse actualizar(String id, DepartamentoRequest request) {
        log.info("Actualizando departamento con ID: {}", id);

        Departamento departamento = repository.findById(id)
                .orElseThrow(() -> {
                    log.warn("Intento de actualizar departamento inexistente: {}", id);
                    return new EntityNotFoundException(
                            "Departamento con ID '" + id + "' no encontrado"
                    );
                });

        // Actualizar campos
        departamento.setNombre(request.getNombre());
        departamento.setDescripcion(request.getDescripcion());

        Departamento actualizado = repository.save(departamento);
        log.info("Departamento actualizado exitosamente: {}", actualizado.getId());

        return toResponse(actualizado);
    }

    @Override
    public void eliminar(String id) {
        log.info("Eliminando departamento con ID: {}", id);

        if (!repository.existsById(id)) {
            log.warn("Intento de eliminar departamento inexistente: {}", id);
            throw new EntityNotFoundException(
                    "Departamento con ID '" + id + "' no encontrado"
            );
        }

        repository.deleteById(id);
        log.info("Departamento eliminado exitosamente: {}", id);
    }

    @Override
    @Transactional(readOnly = true)
    public boolean existe(String id) {
        return repository.existsById(id);
    }

    /**
     * Convierte una entidad Departamento a su DTO de respuesta.
     */
    private DepartamentoResponse toResponse(Departamento entity) {
        return DepartamentoResponse.builder()
                .id(entity.getId())
                .nombre(entity.getNombre())
                .descripcion(entity.getDescripcion())
                .build();
    }
}
