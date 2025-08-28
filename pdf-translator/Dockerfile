# Etapa 1: Construcción de la aplicación con Node.js 22
FROM node:22-alpine AS build

# Crear directorio de trabajo en el contenedor
WORKDIR /app

# Copiar los archivos de dependencias primero para aprovechar la cache
COPY package*.json ./

# Instalar las dependencias del proyecto
RUN npm install

# Copiar el resto de los archivos del proyecto
COPY . .

# Construir la aplicación (salida estará en /app/dist)
RUN npm run build

# Etapa 2: Servir los archivos estáticos con Nginx
FROM nginx:stable-alpine

# Copiar los archivos generados desde la etapa de construcción
COPY --from=build /app/dist /usr/share/nginx/html

# Copiar configuración personalizada de nginx
COPY ../nginx.conf /etc/nginx/conf.d/default.conf

# Exponer el puerto 80
EXPOSE 80

# Arrancar Nginx en modo no daemon
CMD ["nginx", "-g", "daemon off;"]
