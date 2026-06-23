# Project Walkthrough: Production Recommender System (FastAPI + React)

This document details the completed implementation of the production-grade **Hybrid Movie Recommendation Engine** with a decoupled backend and frontend architecture.

---

## 🎬 Architecture & Completed Components

We transitioned the project from a monolithic Streamlit layout to a distributed **FastAPI Backend + SQLite Database + React Frontend** system:

### 1. Backend API (`backend/`)
* **FastAPI Service (`backend/app/main.py`)**: Serves recommendations, logs clicks, performs online learning updates, and acts as the central orchestrator.
* **SQLite Persistence (`backend/app/database.py`, `backend/app/models_db.py`)**: Stores live user interaction logs and catalog modifications. Ensures data is persistent across server restarts.
* **Online SGD Matrix Factorization (`backend/src/models.py`)**: Exposes latent User ($P$) and Item ($Q$) matrices. When a user rates a movie, it runs a real-time Stochastic Gradient Descent step in memory to update coordinates:
  $$P_u \leftarrow P_u + \gamma \cdot (e_{ui} \cdot Q_i - \lambda \cdot P_u)$$
  $$Q_i \leftarrow Q_i + \gamma \cdot (e_{ui} \cdot P_u - \lambda \cdot Q_i)$$

### 2. Frontend Application (`frontend/`)
* **Vite + React Template**: Replaces Streamlit with a highly performant, responsive React app.
* **Settings Control Center (`SidebarSettings.jsx`)**: Real-time sliders to tune Collaborative weight, Novelty penalty, and Genre diversity penalty.
* **Onboarding Module (`Onboarding.jsx`)**: Cold-start resolver mapping queries through Content TF-IDF similarities to bootstrap guest profiles.
* **Global Activity Feed (`LiveFeed.jsx`)**: Live sidebar component polling the backend SQLite logs every 5 seconds to display updates from *all* active user sessions.
* **Diagnostics Dashboard (`VisualCharts.jsx`)**: SVG line plots displaying SVD explained variance and an animated coordinate equalizer showing latent user coordinate shifts.
* **Dynamic Catalog Manager**: Admin panel to add new movies (dynamically vectorizing text and expanding SVD matrices in RAM) and soft-delete/hide movies.

---

## 📈 Integration & API Test Results

We ran automated integration tests covering the database operations, online SGD learning updates, and API endpoint routing.

### API Integration Test Output (`backend/test_api.py`):
```text
=== RUNNING API ENDPOINT TESTS ===

1. Testing GET /api/stats...
[OK] Stats check passed. Total Ratings: 100836, RMSE: 0.9366

2. Testing POST /api/onboarding...
[OK] Onboarding passed. Generated Guest User ID: guest_8a2d131f
     Matched Movies: ['Back to the Future (1985)', 'Star Wars: Episode IV - A New Hope (1977)', 'Terminator 2: Judgment Day (1991)', 'Matrix, The (1999)', 'Interstellar (2014)']

3. Testing GET /api/recommendations...
[OK] Recommendations passed. Received 10 personalized items.

4. Testing POST /api/ratings (Online SGD step)...
[OK] Rating submission processed successfully.

5. Testing GET /api/feed (Network Feed)...
[OK] Global network feed verified. Last action: User guest_8a2d131f rated movie 1270 (Back to the Future (1985)).

=== ALL FastAPI ENDPOINT INTEGRATION TESTS PASSED ===
```

### Core Pipeline Test Output (`test_pipeline.py`):
```text
=== STARTING AUTOMATED PIPELINE TESTS ===

1. Testing Ingestion and Data Loading...
[OK] Ingestion passed. Loaded 100836 ratings, 9742 movies.

2. Testing Collaborative Model (SVD)...
[CollaborativeModel] Trained SVD. P shape: (346, 10), Q shape: (786, 10)
[OK] SVD collaborative fitting passed. Predict sample rating: 3.83

3. Testing Content-Based Model (TF-IDF)...
[ContentModel] Fitted TF-IDF matrix of shape (9742, 9947)
[OK] TF-IDF content fitting passed. Vocabulary size: 9947

4. Testing Evaluation Metrics Math...
[OK] Accuracy (RMSE) and Ranking (MAP, NDCG) math checked successfully.

5. Testing Hybrid Recommender Assembly...
[OK] Hybrid Recommender recommendations retrieved successfully.

6. Testing Online SVD SGD Updates...
[OK] Online SVD SGD rating updates shift latent vectors successfully.

=== ALL PIPELINE TESTS PASSED SUCCESSFULLY ===
```

---

## 🚀 Running the Project

### 1. Install Dependencies
```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Start the Backend API Server
```bash
cd backend
python run.py
# Server starts on http://127.0.0.1:8000
```

### 3. Start the Frontend Dev Server
```bash
cd frontend
npm run dev
# React App starts on http://localhost:5173
```
