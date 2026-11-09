# Pinned to Node patch version + Alpine release. To update: check the new tag exists
# (docker buildx imagetools inspect <tag>), bump it in both FROM lines, then rebuild.
FROM node:22.23.4-alpine3.24 AS base
RUN corepack enable
WORKDIR /app

FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM base AS build
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
# Optional cap for Node's heap while building (MB); unset keeps Node's default
ARG NODE_BUILD_MEMORY_MB
COPY . .
RUN if [ -n "$NODE_BUILD_MEMORY_MB" ]; then export NODE_OPTIONS="--max-old-space-size=$NODE_BUILD_MEMORY_MB"; fi && pnpm build

FROM node:22.23.4-alpine3.24 AS runtime
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
WORKDIR /app
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
