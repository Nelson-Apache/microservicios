# =====================================================
# Jenkins CI — Imagen personalizada para el proyecto
# =====================================================
# Incluye:
#   - Plugins pre-instalados (pipeline, Docker, SonarQube, JCasC)
#   - Cliente Docker (Docker Socket Mount strategy)
#   - Setup Wizard desactivado
#   - Configuración como Código (JCasC)
# =====================================================
FROM jenkins/jenkins:lts-jdk17

# ─── Instalar plugins necesarios de forma automatizada ───
RUN jenkins-plugin-cli --plugins \
    workflow-aggregator \
    docker-workflow \
    pipeline-stage-view \
    git \
    configuration-as-code \
    sonar \
    pipeline-utility-steps \
    ws-cleanup \
    timestamper \
    ansicolor \
    job-dsl

# ─── Instalar cliente Docker dentro del contenedor Jenkins ───
USER root

RUN apt-get update && \
    apt-get install -y docker.io docker-compose && \
    rm -rf /var/lib/apt/lists/*

# Agregar usuario jenkins al grupo docker para acceder al socket
RUN groupadd -f docker && usermod -aG docker jenkins

# ─── Copiar configuración JCasC ───
COPY casc.yaml /var/jenkins_home/casc.yaml

# ─── Variables de entorno ───
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"
ENV CASC_JENKINS_CONFIG="/var/jenkins_home/casc.yaml"

# USER jenkins
