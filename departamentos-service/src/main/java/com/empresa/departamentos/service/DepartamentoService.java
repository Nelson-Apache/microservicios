package com.empresa.departamentos.service;

import com.empresa.departamentos.dto.DepartamentoRequest;
import com.empresa.departamentos.dto.DepartamentoResponse;
import com.empresa.departamentos.model.Departamento;

import java.util.List;

/**
 * Interfaz del servicio para operaciones de negocio relacionadas con departamentos.
 */
public interface DepartamentoService {

    /**
     * Crea un nuevo departamento.
     *
     * @param request Datos del departamento a crear
     * @return El departamento creado
     * @throws IllegalArgumentException si el ID ya existe
     */
    DepartamentoResponse crear(DepartamentoRequest request);

    /**
     * Lista todos los departamentos.
     *
     * @return Lista de todos los departamentos
     */
    List<DepartamentoResponse> listarTodos();

    /**
     * Obtiene un departamento por su ID.
     *
     * @param id ID del departamento
     * @return El departamento encontrado
     * @throws jakarta.persistence.EntityNotFoundException si no existe
     */
    DepartamentoResponse obtenerPorId(String id);

    /**
     * Actualiza un departamento existente.
     *
     * @param id ID del departamento a actualizar
     * @param request Nuevos datos del departamento
     * @return El departamento actualizado
     * @throws jakarta.persistence.EntityNotFoundException si no existe
     */
    DepartamentoResponse actualizar(String id, DepartamentoRequest request);

    /**
     * Elimina un departamento por su ID.
     *
     * @param id ID del departamento a eliminar
     * @throws jakarta.persistence.EntityNotFoundException si no existe
     */
    void eliminar(String id);

    /**
     * Verifica si un departamento existe.
     *
     * @param id ID del departamento
     * @return true si existe, false si no
     */
    boolean existe(String id);
}
