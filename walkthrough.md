# Project Walkthrough: Production Recommender System (FastAPI + React)

This document details the completed implementation of the production-grade **Hybrid Movie Recommendation Engine** with a decoupled backend and frontend architecture.

---

## 🎬 Architecture & Completed Components

We transitioned the project from a monolithic Streamlit layout to a distributed **FastAPI Backend + PostgreSQL (Neon Cloud) + Redis + React Frontend** system:

### 1. Backend API (`backend/`)
* **FastAPI Service (`backend/app/main.py`)**: Serves recommendations, logs clicks, performs online learning updates, and acts as the central orchestrator. Optimized with a sub-second startup sequence by decoupling database seeding.
* **PostgreSQL & SQLite Database (`backend/app/database.py`, `backend/app/models_db.py`)**: Connects to a cloud-hosted Neon PostgreSQL database by default, falling back gracefully to local **SQLite** (`live_ratings.db`) if unconfigured. Stores live user ratings, catalog additions/deletions, cached movie poster paths, and **explicit user onboarding preferences** (genres, keywords, and seed movies).
* **Onboarding Preferences & Clean Genre Boosting**: Stores onboarding selections in a dedicated `user_preferences` table. During recommendation generation, the recommender queries these preferences, applies a direct boost (`+30.0` content weight) to explicitly selected genres, and filters the genre boosts of the onboarding seed movies so that incidental genres (like Comedy and Drama) do not pollute the user's content profile.
* **Online FunkSVD Matrix Factorization (`backend/src/models.py`)**: Implements FunkSVD (Matrix Factorization on observed ratings only) using pure NumPy/Pandas, completely removing dense matrix imputation bias. Exposes User ($P$) and Item ($Q$) latent factor matrices, updating vectors on rating submissions dynamically using Stochastic Gradient Descent (SGD) in-memory.
* **Distributed Cache (`backend/app/cache.py`)**: Stores serialization states inside a distributed **Redis** database if `REDIS_URL` is set, falling back to a local **in-memory SimpleLRUCache** with a TTL. Caches are invalidated instantly when ratings are updated.
* **Model Retraining & Scheduler (`backend/src/retrain.py`)**: A background retraining script that fetches live ratings and custom movies from the active database, combines them with baseline data, retrains SVD/TF-IDF models, and performs an atomic in-memory swap on the running FastAPI application with zero server downtime. It runs automatically every 24 hours via a background daemon thread.
* **WebSocket Broadcasting Hub (`backend/app/ws_manager.py`)**: Manages active client WebSocket sockets and broadcasts system updates in real-time when ratings are posted, user onboarding is completed, or catalog items are modified.
* **TMDB Image Poster Integration (`backend/app/tmdb.py`)**: Queries the TMDB API (`api.tmdb.org`) using `TMDB_API_KEY` or `TMDB_ACCESS_TOKEN` to retrieve and cache movie poster images on-demand.

### 2. Frontend Application (`frontend/`)
* **Vite + React Template**: Replaces Streamlit with a highly performant, responsive React app.
* **Decoupled API Client (`api.js`)**: All `fetch()` API calls are consolidated in a central client, reading `VITE_API_BASE` from environment files (`.env`).
* **Zustand Store (`store/useAppStore.js`)**: State management is fully decoupled from components. UI state, session profiles, algorithm controls, and recommendation data slices are handled in a single atom. Houses a persistent WebSocket stream handler `initWebSocket()` to synchronize client data.
* **Settings Control Center (`SidebarSettings.jsx`)**: Real-time sliders to tune Collaborative weight, Novelty penalty, and Genre diversity penalty.
* **Onboarding Module (`Onboarding.jsx`)**: Cold-start resolver mapping queries through Content TF-IDF similarities to bootstrap guest profiles.
* **Real-Time WebSocket Activity Feed (`LiveFeed.jsx`)**: Replaced inefficient 5-second HTTP polling with a persistent WebSocket client connecting to `/api/v1/ws/feed` that syncs global feed logs and diagnostics instantly on changes.
* **Diagnostics Dashboard (`VisualCharts.jsx`)**: SVG line plots displaying SVD explained variance and an animated coordinate equalizer showing latent user coordinate shifts.
* **Movie Poster Render Grid (`MovieShelf.jsx`)**: Renders high-quality TMDB movie posters dynamically with an elegant hover micro-animation.


---

## 🧪 Automated Testing Suite

We implemented an extensive pytest suite under `backend/tests/` with 75 fully passing unit, integration, and ML math tests.

### Running Pytest Suite
```bash
python -m pytest backend/tests/ -v
```

### Coverage Details:
1. **Authentication (`test_auth.py`)**: Registration success, duplicate usernames, password validation, login credentials checks, token issuance, and demo profile access.
2. **Dependencies (`test_dependencies.py`)**: Secure PBKDF2 password hashing, salt validation, token signing/verification, and header parsing.
3. **Activity Feed (`test_feed.py`)**: Stats dashboard serialization, movies count active filters, global activity feed serialization, limit caps, and pagination.
4. **Movies Catalog (`test_movies.py`)**: Popular movie listings, title search query logic, case insensitivity, admin movie additions, SVD registry registration, and soft deletion.
5. **Onboarding (`test_onboarding.py`)**: Guest ID boots, registered profile matching, input validator schemas, and SVD profile bootstrapping.
6. **Ratings (`test_ratings.py`)**: Guest/registered user ratings submissions, SVD real-time SGD vector shift validation, dislikes weighting, and rating history listings.
7. **Recommendations (`test_recommendations.py`)**: Guest recommendations, user token authorizations, algorithm weights, and Explainable AI (XAI) explanation blocks.
8. **Admin Operations (`test_admin.py`)**: Retrain authorization guards, trigger batch retraining checks, and model swap verifications.
9. **ML Pipeline Math (`test_ml_math.py`)**: Collaborative SVD fit accuracy, online SGD parameter tuning correctness, and content TF-IDF sparse matrix vectorization.

---

## 🚀 Running the Project

### 1. Pre-Train Batch SVD & NLP Models
Run the training pipeline from the project root to generate baseline models:
```bash
python -m backend.src.train
```

### 2. Start the Backend API
```bash
cd backend
pip install -r requirements.txt
python run.py
```
*API runs on `http://127.0.0.1:8000`.*

### 3. Start the Frontend React App
```bash
cd frontend
npm install
npm run dev
```
*Vite dev server starts on `http://localhost:5173`.*

---

## 🌐 Cloud Deployment Guide (Render / Railway / Heroku)

Here is how to configure and deploy the project in a cloud hosting environment:

### 1. Backend Service (Web Service)
* **Build Command**:
  ```bash
  pip install -r backend/requirements.txt && python -m backend.src.train
  ```
  *(This installs dependencies and seeds/trains the base models and database on the remote server during build).*
* **Start Command**:
  ```bash
  python backend/run.py
  ```
* **Environment Variables**:
  * `ENVIRONMENT`: Set to `production` *(disables code reloading, binds host to `0.0.0.0`)*
  * `JWT_SECRET`: A secure random string for signing user tokens
  * `DATABASE_URL`: Your PostgreSQL DSN (e.g. Neon Cloud connection string)
  * `REDIS_URL`: *(Optional)* Your Redis URL for caching
  * `TMDB_API_KEY` or `TMDB_ACCESS_TOKEN`: *(Optional)* Your TMDB API key to render movie posters

---

### 2. Frontend App (Static Site)
* **Build Command**:
  ```bash
  cd frontend && npm install && npm run build
  ```
* **Publish/Output Directory**:
  `frontend/dist`
* **Environment Variables**:
  * `VITE_API_BASE`: Set to the public HTTPS URL of your deployed backend service (e.g. `https://your-backend.onrender.com`). No trailing slash.
