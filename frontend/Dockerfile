FROM node:18-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
# The entrypoint substitutes ${PORT}, ${API_HOST} and ${API_PORT} (and nothing else) into the config.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
ENV PORT=80 API_HOST=backend API_PORT=8000 NGINX_ENVSUBST_FILTER="^(PORT|API_HOST|API_PORT)$"
EXPOSE 80
