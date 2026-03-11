FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci --production --ignore-scripts 2>/dev/null || npm install --production

# Copy source
COPY src/ ./src/

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:3000/api/health || exit 1

EXPOSE 3000

CMD ["node", "src/server.js"]
