package com.empresa.departamentos.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.*;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Schema(description = "Esquema de respuesta de un departamento")
public class DepartamentoResponse {

    @Schema(description = "Identificador único del departamento", example = "IT")
    private String id;

    @Schema(description = "Nombre del departamento", example = "Tecnología")
    private String nombre;

    @Schema(description = "Descripción de las funciones del departamento", example = "Departamento de TI")
    private String descripcion;
}
