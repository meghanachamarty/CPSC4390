############################
# 1. Build React frontend
############################
FROM node:20-alpine AS frontend-builder

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install

COPY frontend ./
RUN npm run build


############################
# 2. FastAPI + Nginx
############################
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# --- Install ONLY nginx ---
RUN apt-get update \
 && apt-get install -y --no-install-recommends nginx \
 && rm -rf /var/lib/apt/lists/*

# --- Backend deps ---
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Backend source ---
COPY backend .

# --- Nginx config ---
RUN rm -rf /etc/nginx/sites-enabled/* \
    && rm -f /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf

# --- React build into Nginx root ---
COPY --from=frontend-builder /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["sh", "-c", "nginx && uvicorn main:app --host 127.0.0.1 --port 8000"]
