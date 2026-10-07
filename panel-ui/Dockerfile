FROM node:20-alpine AS build

# Адрес Panel API, доступный из браузера (НЕ docker-service-name) —
# Vite "запекает" его в статику на этапе build, runtime ENV на SPA уже не влияет.
ARG VITE_PANEL_API_URL=http://localhost:8001

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
ENV VITE_PANEL_API_URL=${VITE_PANEL_API_URL}
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
