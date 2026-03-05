package com.empresa.departamentos.model;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.persistence.*;
import jakarta.validation.constraints.NotBlank;
import lombok.*;

@Entity
@Table(name = "departamentos")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Entidad que representa un departamento organizacional")
public class Departamento {

    @Id
    @Column(nullable = false, unique = true)
    @Schema(description = "Identificador único del departamento", example = "IT")
    private String id;

    @NotBlank(message = "El nombre del departamento es obligatorio")
    @Column(nullable = false)
    @Schema(description = "Nombre del departamento", example = "Tecnología")
    private String nombre;

    @Schema(description = "Descripción de las funciones del departamento", example = "Departamento de TI")
    private String descripcion;
}
