package com.empresa.departamentos.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import io.swagger.v3.oas.models.Components;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("Servicio de Departamentos")
                        .version("1.1.0")
                        .description(
                                "## Microservicio de Gestión de Departamentos\n\n"
                                        + "Permite crear, consultar y listar departamentos organizacionales.\n\n"
                                        + "Implementado en **Java** con **Spring Boot 3** y persistencia en **PostgreSQL**.\n\n"
                                        + "### Características\n"
                                        + "- Persistencia en base de datos PostgreSQL con JPA/Hibernate\n"
                                        + "- Comunicación REST con otros microservicios\n"
                                        + "- Documentación OpenAPI integrada con SpringDoc\n"
                                        + "- Dockerfile multi-stage (Maven builder + JRE runtime)")
                        .contact(new Contact()
                                .name("Equipo de Microservicios")
                                .email("soporte@empresa.com"))
                        .license(new License()
                                .name("MIT")))
                .addSecurityItem(new SecurityRequirement().addList("BearerAuth"))
                .components(new Components()
                        .addSecuritySchemes("BearerAuth", new SecurityScheme()
                                .name("BearerAuth")
                                .type(SecurityScheme.Type.HTTP)
                                .scheme("bearer")
                                .bearerFormat("JWT")
                                .description("Token JWT obtenido desde POST /auth/login")));
    }
}
