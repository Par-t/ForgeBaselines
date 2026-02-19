FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
EXPOSE 3000
ENV WATCHPACK_POLLING=true
ENV NEXT_TELEMETRY_DISABLED=1
CMD ["npm", "run", "dev"]
