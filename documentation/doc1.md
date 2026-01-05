# Getting Started (Local Development)

This guide will help you set up the project on your local machine.

---

## 1. Clone the Repository

First, clone the repo and move into the project directory:

```bash
git clone https://github.com/yale-swe/f25-Course-Sidekick
cd f25-Course-Sidekick
```

---

## 2. Why Docker Compose?

We use **Docker Compose** to run both the backend (Python/FastAPI) and frontend (React) services together.

* Without Compose, you’d need to start each service manually with separate commands.
* With Compose, you define everything in one `docker-compose.yml` file and bring up the whole stack with a single command.
* Services automatically share a network, so the frontend can talk to the backend via its service name (e.g., `http://backend:8000`).
* It keeps environments consistent across all developers’ machines.

---

## 3. Build and Run with Docker Compose

To build the images and start the containers:

```bash
docker compose up --build
```

This will:

* Build the **backend** image and start it on port 8000
* Build the **frontend** image and start it on port 3000
* Connect them on the same internal network

Access the app at:

* Frontend: [http://localhost:3000](http://localhost:3000)
* Backend API: [http://localhost:8000](http://localhost:8000)

---

## 4. Stopping Services

To stop all running containers:

```bash
docker compose down
```

---

## 5. Development Notes

* If you change backend code, restart with `docker compose up --build backend`
* If you change frontend code, restart with `docker compose up --build frontend`
* Logs for a specific service can be viewed with:

  ```bash
  docker compose logs backend
  docker compose logs frontend
  ```

## 6. Running Without Docker

If you prefer to run the services directly, follow these steps.

### Backend (FastAPI)

1. Create and activate a virtual environment:

   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
3. Start the FastAPI app with Uvicorn:

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
4. Backend will be available at [http://localhost:8000](http://localhost:8000).

### Frontend (React)

1. Move into the frontend directory:

   ```bash
   cd frontend
   ```
2. Install dependencies:

   ```bash
   npm install
   ```
3. Start the React dev server:

   ```bash
   npm start
   ```
4. Frontend will be available at [http://localhost:3000](http://localhost:3000).

Note: If running without Docker, you may need to configure the frontend `package.json` proxy to point to `http://localhost:8000` for API calls.
