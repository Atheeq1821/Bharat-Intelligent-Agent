FROM node:20-bookworm-slim

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend ./

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
