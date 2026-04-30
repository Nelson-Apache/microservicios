package com.empresa.departamentos.service;

import com.empresa.departamentos.dto.DepartamentoRequest;
import com.empresa.departamentos.dto.DepartamentoResponse;
import com.empresa.departamentos.model.Departamento;
import com.empresa.departamentos.repository.DepartamentoRepository;
import jakarta.persistence.EntityNotFoundException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Arrays;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

/**
 * Pruebas unitarias para DepartamentoServiceImpl.
 * Utiliza Mockito para aislar la lógica de negocio.
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("Pruebas del Servicio de Departamentos")
class DepartamentoServiceImplTest {

    @Mock
    private DepartamentoRepository repository;

    @InjectMocks
    private DepartamentoServiceImpl service;

    private DepartamentoRequest validRequest;
    private Departamento departamento;

    @BeforeEach
    void setUp() {
        validRequest = new DepartamentoRequest();
        validRequest.setId("IT");
        validRequest.setNombre("Tecnología");
        validRequest.setDescripcion("Departamento de TI");

        departamento = new Departamento();
        departamento.setId("IT");
        departamento.setNombre("Tecnología");
        departamento.setDescripcion("Departamento de TI");
    }

    // ─────────────────────────────────────────────────────────────────
    // Tests de creación
    // ─────────────────────────────────────────────────────────────────

    @Test
    @DisplayName("Debe crear un departamento exitosamente")
    void testCrearDepartamento_Success() {
        // Arrange
        when(repository.existsById(anyString())).thenReturn(false);
        when(repository.save(any(Departamento.class))).thenReturn(departamento);

        // Act
        DepartamentoResponse response = service.crear(validRequest);

        // Assert
        assertThat(response).isNotNull();
        assertThat(response.getId()).isEqualTo("IT");
        assertThat(response.getNombre()).isEqualTo("Tecnología");
        assertThat(response.getDescripcion()).isEqualTo("Departamento de TI");
        
        verify(repository, times(1)).existsById("IT");
        verify(repository, times(1)).save(any(Departamento.class));
    }

    @Test
    @DisplayName("Debe lanzar excepción si el ID ya existe")
    void testCrearDepartamento_IdDuplicado() {
        // Arrange
        when(repository.existsById(anyString())).thenReturn(true);

        // Act & Assert
        assertThatThrownBy(() -> service.crear(validRequest))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Ya existe");

        verify(repository, times(1)).existsById("IT");
        verify(repository, never()).save(any(Departamento.class));
    }

    // ─────────────────────────────────────────────────────────────────
    // Tests de consulta
    // ─────────────────────────────────────────────────────────────────

    @Test
    @DisplayName("Debe listar todos los departamentos")
    void testListarTodos_Success() {
        // Arrange
        Departamento dept2 = new Departamento();
        dept2.setId("HR");
        dept2.setNombre("Recursos Humanos");
        dept2.setDescripcion("Gestión de personal");

        List<Departamento> departamentos = Arrays.asList(departamento, dept2);
        when(repository.findAll()).thenReturn(departamentos);

        // Act
        List<DepartamentoResponse> responses = service.listarTodos();

        // Assert
        assertThat(responses).hasSize(2);
        assertThat(responses.get(0).getId()).isEqualTo("IT");
        assertThat(responses.get(1).getId()).isEqualTo("HR");
        
        verify(repository, times(1)).findAll();
    }

    @Test
    @DisplayName("Debe obtener un departamento por ID")
    void testObtenerPorId_Success() {
        // Arrange
        when(repository.findById("IT")).thenReturn(Optional.of(departamento));

        // Act
        DepartamentoResponse response = service.obtenerPorId("IT");

        // Assert
        assertThat(response).isNotNull();
        assertThat(response.getId()).isEqualTo("IT");
        assertThat(response.getNombre()).isEqualTo("Tecnología");
        
        verify(repository, times(1)).findById("IT");
    }

    @Test
    @DisplayName("Debe lanzar excepción si el departamento no existe")
    void testObtenerPorId_NoEncontrado() {
        // Arrange
        when(repository.findById("INVALID")).thenReturn(Optional.empty());

        // Act & Assert
        assertThatThrownBy(() -> service.obtenerPorId("INVALID"))
                .isInstanceOf(EntityNotFoundException.class)
                .hasMessageContaining("no encontrado");

        verify(repository, times(1)).findById("INVALID");
    }

    // ─────────────────────────────────────────────────────────────────
    // Tests de actualización
    // ─────────────────────────────────────────────────────────────────

    @Test
    @DisplayName("Debe actualizar un departamento exitosamente")
    void testActualizar_Success() {
        // Arrange
        DepartamentoRequest updateRequest = new DepartamentoRequest();
        updateRequest.setNombre("Tecnología e Innovación");
        updateRequest.setDescripcion("TI actualizado");

        when(repository.findById("IT")).thenReturn(Optional.of(departamento));
        when(repository.save(any(Departamento.class))).thenReturn(departamento);

        // Act
        DepartamentoResponse response = service.actualizar("IT", updateRequest);

        // Assert
        assertThat(response).isNotNull();
        verify(repository, times(1)).findById("IT");
        verify(repository, times(1)).save(any(Departamento.class));
    }

    @Test
    @DisplayName("Debe lanzar excepción al actualizar departamento inexistente")
    void testActualizar_NoEncontrado() {
        // Arrange
        when(repository.findById("INVALID")).thenReturn(Optional.empty());

        DepartamentoRequest updateRequest = new DepartamentoRequest();
        updateRequest.setNombre("Test");

        // Act & Assert
        assertThatThrownBy(() -> service.actualizar("INVALID", updateRequest))
                .isInstanceOf(EntityNotFoundException.class);

        verify(repository, times(1)).findById("INVALID");
        verify(repository, never()).save(any(Departamento.class));
    }

    // ─────────────────────────────────────────────────────────────────
    // Tests de eliminación
    // ─────────────────────────────────────────────────────────────────

    @Test
    @DisplayName("Debe eliminar un departamento exitosamente")
    void testEliminar_Success() {
        // Arrange
        when(repository.existsById("IT")).thenReturn(true);
        doNothing().when(repository).deleteById("IT");

        // Act
        service.eliminar("IT");

        // Assert
        verify(repository, times(1)).existsById("IT");
        verify(repository, times(1)).deleteById("IT");
    }

    @Test
    @DisplayName("Debe lanzar excepción al eliminar departamento inexistente")
    void testEliminar_NoEncontrado() {
        // Arrange
        when(repository.existsById("INVALID")).thenReturn(false);

        // Act & Assert
        assertThatThrownBy(() -> service.eliminar("INVALID"))
                .isInstanceOf(EntityNotFoundException.class);

        verify(repository, times(1)).existsById("INVALID");
        verify(repository, never()).deleteById(anyString());
    }

    // ─────────────────────────────────────────────────────────────────
    // Tests de existencia
    // ─────────────────────────────────────────────────────────────────

    @Test
    @DisplayName("Debe retornar true si el departamento existe")
    void testExiste_True() {
        // Arrange
        when(repository.existsById("IT")).thenReturn(true);

        // Act
        boolean existe = service.existe("IT");

        // Assert
        assertThat(existe).isTrue();
        verify(repository, times(1)).existsById("IT");
    }

    @Test
    @DisplayName("Debe retornar false si el departamento no existe")
    void testExiste_False() {
        // Arrange
        when(repository.existsById("INVALID")).thenReturn(false);

        // Act
        boolean existe = service.existe("INVALID");

        // Assert
        assertThat(existe).isFalse();
        verify(repository, times(1)).existsById("INVALID");
    }
}
