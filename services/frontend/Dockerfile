FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .

# Baked in at build time for production (set via docker-compose build args)
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

EXPOSE 3000
ENV WATCHPACK_POLLING=true
ENV NEXT_TELEMETRY_DISABLED=1
CMD ["npm", "run", "dev"]
