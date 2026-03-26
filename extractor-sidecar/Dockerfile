# Build
FROM node:20-bookworm-slim AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

# Run
FROM node:20-bookworm-slim
WORKDIR /app
ENV NODE_ENV=production
RUN groupadd -r app && useradd -r -g app app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=builder /app/dist ./dist
USER app
EXPOSE 3000
CMD ["node", "dist/index.js"]
