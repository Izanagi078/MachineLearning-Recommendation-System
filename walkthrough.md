# Project Walkthrough: Production Recommender System (FastAPI + React)

This document details the completed implementation of the production-grade **Hybrid Movie Recommendation Engine** with a decoupled backend and frontend architecture.

---

## 🎬 Architecture & Completed Components

We transitioned the project from a monolithic Streamlit layout to a distributed **FastAPI Backend + PostgreSQL (Neon Cloud) + Redis + React Frontend** system:

### 1. Backend API (`backend/`)
* **FastAPI Service (`backend/app/main.py`)**: Serves recommendations, logs clicks, performs online learning updates, and acts as the central orchestrator.
* **PostgreSQL & SQLite Database (`backend/app/database.py`, `backend/app/models_db.py`)**: Connects to a cloud-hosted Neon PostgreSQL database by default, falling back gracefully to local **SQLite** (`live_ratings.db`) if unconfigured. Stores live user ratings, catalog additions/deletions, and cached movie poster paths.
* **Online SGD Matrix Factorization (`backend/src/models.py`)**: Exposes User ($P$) and Item ($Q$) latent factor matrices, updating vectors on rating submissions dynamically. Runs SGD for 5 epochs to speed up profile convergence.
* **Distributed Cache (`backend/app/cache.py`)**: Stores serialization states inside a distributed **Redis** database if `REDIS_URL` is set, falling back to a local **in-memory SimpleLRUCache** with a TTL. Caches are invalidated instantly when ratings are updated.
* **Model Retraining & Scheduler (`backend/src/retrain.py`)**: A background retraining script that fetches live ratings and custom movies from the active database, combines them with baseline data, retrains SVD/TF-IDF models, and performs an atomic in-memory swap on the running FastAPI application with zero server downtime. It runs automatically every 24 hours via a background daemon thread.
* **TMDB Image Poster Integration (`backend/app/tmdb.py`)**: Queries the TMDB API (`api.tmdb.org`) using `TMDB_API_KEY` or `TMDB_ACCESS_TOKEN` to retrieve and cache movie poster images on-demand.

### 2. Frontend Application (`frontend/`)
* **Vite + React Template**: Replaces Streamlit with a highly performant, responsive React app.
* **Decoupled API Client (`api.js`)**: All `fetch()` API calls are consolidated in a central client, reading `VITE_API_BASE` from environment files (`.env`).
* **Zustand Store (`store/useAppStore.js`)**: State management is fully decoupled from components. UI state, session profiles, algorithm controls, and recommendation data slices are handled in a single atom.
* **Settings Control Center (`SidebarSettings.jsx`)**: Real-time sliders to tune Collaborative weight, Novelty penalty, and Genre diversity penalty.
* **Onboarding Module (`Onboarding.jsx`)**: Cold-start resolver mapping queries through Content TF-IDF similarities to bootstrap guest profiles.
* **Global Activity Feed (`LiveFeed.jsx`)**: Live sidebar component polling the backend active database logs every 5 seconds to display updates from *all* active user sessions.
* **Diagnostics Dashboard (`VisualCharts.jsx`)**: SVG line plots displaying SVD explained variance and an animated coordinate equalizer showing latent user coordinate shifts.
* **Movie Poster Render Grid (`MovieShelf.jsx`)**: Renders high-quality TMDB movie posters dynamically with an elegant hover micro-animation.


---

## 🧪 Automated Testing Suite

We implemented an extensive pytest suite under `backend/tests/` with 74 fully passing unit, integration, and ML math tests.

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
