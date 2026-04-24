package com.empresa.e2e.support;

import io.cucumber.junit.Cucumber;
import io.cucumber.junit.CucumberOptions;
import org.junit.runner.RunWith;

/**
 * Runner de JUnit para ejecutar todos los escenarios Cucumber.
 * 
 * PROPÓSITO:
 * - Punto de entrada único para Maven Surefire (mvn test)
 * - Configura la ubicación de features y step definitions
 * - Configura los plugins de reportes
 * 
 * CONFIGURACIÓN:
 * 
 * RunWith(Cucumber.class):
 * - Indica a JUnit que use el runner de Cucumber
 * 
 * REPORTES GENERADOS:
 * - target/cucumber-reports/report.html (abrir en navegador)
 * - target/cucumber-reports/report.json (para herramientas de CI/CD)
 */
@RunWith(Cucumber.class)
@CucumberOptions(
        features = "src/test/resources/features",
        glue = {"com.empresa.e2e.step_definitions", "com.empresa.e2e.support"},
        plugin = {
                "pretty",
                "html:target/cucumber-reports/report.html",
                "json:target/cucumber-reports/report.json"
        },
        monochrome = true
)
public class CucumberRunner {
    // Clase vacía - solo sirve como punto de entrada para JUnit
    // Toda la lógica está en las anotaciones
}
