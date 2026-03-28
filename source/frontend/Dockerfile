# Stage 1: Build (se usi React/Vue, altrimenti usa solo lo Stage 2)
FROM node:18-alpine as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Production
FROM nginx:stable-alpine
# Copia i file compilati nella cartella di Nginx
COPY --from=build-stage /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]