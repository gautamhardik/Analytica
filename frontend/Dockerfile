# Stage 1: build the static export
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Bake the API base the browser will call (Compose publishes the backend on :8000)
ENV NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
RUN npm run build

# Stage 2: serve the static build with nginx
FROM nginx:1.27-alpine
COPY --from=build /app/out /usr/share/nginx/html
COPY docker/frontend-nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
