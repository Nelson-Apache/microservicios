package com.empresa.departamentos.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.*;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Esquema de entrada para crear un departamento")
public class DepartamentoRequest {

    @NotBlank(message = "El ID del departamento es obligatorio")
    @Schema(description = "Identificador único manual para el departamento", example = "IT", requiredMode = Schema.RequiredMode.REQUIRED)
    private String id;

    @NotBlank(message = "El nombre del departamento es obligatorio")
    @Schema(description = "Nombre del departamento", example = "Tecnología", requiredMode = Schema.RequiredMode.REQUIRED)
    private String nombre;

    @Schema(description = "Breve descripción de las funciones del departamento", example = "Departamento de TI")
    private String descripcion;
}
