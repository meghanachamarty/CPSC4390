# Updated Deployment (doc2.md)

This document describes the **new unified deployment workflow** where the entire application
(frontend + backend) is bundled into **one Docker image**, served through **Nginx**, and no longer
uses two separate Dockerfiles or Docker Compose for deployment.

---

# 1. Overview of the New Deployment Model

Previously, the project used:

- Two Dockerfiles  
  - One for React (frontend)  
  - One for FastAPI (backend)  
- Docker Compose to run two containers  
- Ports 3000 and 8000 exposed separately  

Now the project uses:

### ✅ A **single** Dockerfile in the project root  
This image includes:

1. **React Build Stage (Node)**  
   - Builds the optimized production frontend (`npm run build`)

2. **Runtime Stage (Python + FastAPI + Nginx)**  
   - Serves the React app using Nginx  
   - Proxies requests to FastAPI  
   - Handles environment variables like API keys  
   - Eliminates multi-container complexity  

This simplifies deployment and ensures all developers run *exactly the same environment*.

---

# 2. How the New Dockerfile Works (Step-by-Step)

---

## 2.1 Stage 1 — Build React Frontend

```Dockerfile
FROM node:20-alpine AS frontend-builder

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install

COPY frontend ./
RUN npm run build
```

This step:

- Installs frontend dependencies  
- Builds the React SPA  
- Outputs files to `/app/build`  

---

## 2.2 Stage 2 — Runtime: FastAPI + Nginx

```Dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends nginx \
 && rm -rf /var/lib/apt/lists/*
```

This step:

- Installs Python + FastAPI environment  
- Installs Nginx  
- Cleans leftover apt cache  

### Backend Setup

```Dockerfile
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend .
```

### Nginx Setup

```Dockerfile
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

### React Build Injection

```Dockerfile
COPY --from=frontend-builder /app/build /usr/share/nginx/html
```

### Start Command

```Dockerfile
CMD ["sh", "-c", "nginx && uvicorn main:app --host 127.0.0.1 --port 8000"]
```

Nginx listens on port **80**, proxies to Uvicorn on **8000**.

---

# 3. Running the New Deployment

## 3.1 Build the Image

```bash
docker build -t fullstack-app .
```

## 3.2 Run the Container

```bash
docker run -p 80:80 \
  -e OPENAI_API_KEY=yourkey \
  -e ANTHROPIC_API_KEY=yourkey \
  -e USER_AGENT="my-fullstack-app/1.0" \
  fullstack-app
```

Then visit:

- React UI → http://localhost  
- Backend API → http://localhost/api  

---

# 4. How Runtime Routing Works

## 4.1 Nginx Serves the React App

Static files live at:

```
/usr/share/nginx/html
```

Nginx handles all normal browser routes using:

```nginx
try_files $uri /index.html;
```

This is required for React Router.

---

## 4.2 API Routes

All API calls must begin with:

```
/api/
```

because the Nginx config contains:

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
}
```

Examples:

| Function | Route |
|---------|-------|
| Ask chatbot | POST /api/ask |
| Summaries | POST /api/summarize |
| Deadlines | GET /api/deadlines |

---

## 4.3 WebSocket Removal (Important)

Previously:

```
/ws/ask
```

This caused problems behind Nginx → WS Upgrade headers, 101 switching protocol, etc.

### We replaced all WebSockets with REST:

```
POST /api/ask
```

Benefits:

- Simpler to deploy  
- Works everywhere (Nginx, AWS, etc.)  
- No more WS proxy configuration  
- Stateless, easier logging  

---

# 5. Full nginx.conf Reference

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # React SPA
    location / {
        try_files $uri /index.html;
    }

    # FastAPI Backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

# 6. Running Without Docker (Optional)

If you need direct development mode:

### Backend
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm start
```

Your frontend must point to:

```
http://localhost:8000/api
```

---

# 7. Additional Notes

### ✔ All API Routes Must Start with `/api`
Because Nginx proxies only `/api/*`.

### ✔ WebSockets Removed → REST Only
More stable for deployment.

### ✔ Single Dockerfile Deployment Is Now Standard
Docker Compose is no longer required for production.

---

