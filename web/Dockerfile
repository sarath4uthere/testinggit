# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------
# Web image: 2 stages
#   build   -> Node runs the build script and stamps the version
#   runtime -> nginx (unprivileged, port 8080) serves only the built files
# ---------------------------------------------------------------
FROM node:20-alpine AS build
WORKDIR /web
ARG APP_VERSION=dev
ENV VERSION=${APP_VERSION}
COPY package.json build.js ./
COPY src ./src
RUN node build.js

FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime
ARG APP_VERSION=dev
LABEL org.opencontainers.image.title="shop-web" \
      org.opencontainers.image.version="${APP_VERSION}"
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=5 \
  CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
