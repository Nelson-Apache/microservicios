FROM node:18-alpine

# Establecer directorio de trabajo en el contenedor
WORKDIR /usr/src/app

# Copiar archivos de dependencias
COPY package*.json ./

# Instalar dependencias solo para producción
RUN npm install --only=production

# Copiar el código fuente
COPY src/ ./src/

# Exponer el puerto
EXPOSE 3000

# Añadir un healthcheck
HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

# Comando para iniciar la aplicación
CMD ["npm", "start"]
