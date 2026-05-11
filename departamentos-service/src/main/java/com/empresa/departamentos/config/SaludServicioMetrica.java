package com.empresa.departamentos.config;

import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.binder.MeterBinder;
import org.springframework.stereotype.Component;

import javax.sql.DataSource;
import java.sql.Connection;

@Component
public class SaludServicioMetrica implements MeterBinder {

    private final DataSource dataSource;

    public SaludServicioMetrica(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public void bindTo(MeterRegistry registry) {
        Gauge.builder("servicio_saludable", this, SaludServicioMetrica::verificarSalud)
                .description("Servicio y dependencias operativas: 1=sí, 0=no")
                .tag("service", "departamentos-service")
                .register(registry);
    }

    private double verificarSalud() {
        try (Connection conn = dataSource.getConnection()) {
            return conn.isValid(1) ? 1.0 : 0.0;
        } catch (Exception e) {
            return 0.0;
        }
    }
}
