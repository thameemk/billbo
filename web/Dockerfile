FROM node:24-alpine AS build
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store pnpm install --frozen-lockfile
COPY . .
# baked into the bundle at build time
ARG VITE_API_URL=http://localhost:8000/api/v1
ENV VITE_API_URL=$VITE_API_URL
RUN pnpm build
# let the CSP allow fetches to the API origin baked into the bundle
RUN sed "s|__API_ORIGIN__|$(node -p 'new URL(process.env.VITE_API_URL).origin')|" nginx.conf > nginx.out.conf

FROM nginxinc/nginx-unprivileged:alpine-slim
COPY --from=build /app/nginx.out.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD ["wget", "-qO", "/dev/null", "http://127.0.0.1:8080/"]
