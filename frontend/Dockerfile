# syntax=docker/dockerfile:1
# ---- Build stage ----
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# Relative by default: nginx proxies /api to the backend on the same origin.
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# ---- Runtime stage (unprivileged nginx, listens on 8080) ----
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
