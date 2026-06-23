# Production-Grade Hybrid Movie Recommender (FastAPI + SQLite + React)

An advanced, production-grade **Decoupled Machine Learning Recommendation System** combining Collaborative Filtering (SVD Matrix Factorization) and Content-Based NLP Filtering (TF-IDF + Cosine Similarity) using the MovieLens-Latest-Small dataset (100,000 ratings).

This project transitions standard recommender architectures into a scalable, real-time online learning system utilizing:
1. **FastAPI Backend**: Serves ensembled recommendations and coordinates live update triggers.
2. **SQLite Database**: A persistent datastore capturing user interactions and dynamic movie catalog additions.
3. **Online SGD Matrix Factorization**: Triggers a sub-millisecond Stochastic Gradient Descent (SGD) learning step in RAM on every click to update User ($P$) and Item ($Q$) latent vectors immediately.
4. **Vite + React Frontend**: A modern glassmorphic dashboard showcasing horizontal carousels, settings sliders, dynamic onboarding, SVD diagnostics plots, and a live global activity stream.

---

## 🌟 Key Features

* **Real-Time SVD SGD Matrix Tuning**: Clicks (Like 👍/Dislike 👎) immediately run a gradient descent coordinate update step in memory, propagating changes instantly to other users.
* **Dynamic Guest Onboarding**: Resolves cold-start profiles by matching keywords/genres via Content NLP and saving initial mock likes to seed the user's SVD vector.
* **Persistent SQLite Store**: Keeps live transactions durable across server restarts, automatically replaying logs on startup to rebuild in-memory coordinates.
* **Explainable AI (XAI) Panels**: Explains *why* a movie is recommended by mapping overlapping TF-IDF tags or listing the closest latent SVD matches.
* **Diagnostics Dashboard**: Visualizes cumulative explained variance via SVG and shows real-time latent coordinate shifts using an animated equalizer.
* **Dynamic Catalog Admin Panel**: Enables administrators to add new movies (which dynamically registers vectors in RAM) and archive active ones.

---

## 📁 Repository Structure

```text
movie_recommender_ml/
│
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI API routing
│   │   ├── database.py         # SQLAlchemy connection configs
│   │   ├── models_db.py        # SQLite Database Schemas
│   │   └── schemas.py          # Request validation structures
│   ├── src/
│   │   ├── data_loader.py      # Automated dataset downloader
│   │   ├── models.py           # ML Model layers & SGD updates
│   │   ├── evaluation.py       # Metrics scoring (RMSE, MAP, NDCG)
│   │   └── train.py            # Offline batch training pipeline
│   ├── models/                 # Cached serialized model objects (.pkl)
│   ├── requirements.txt        # Backend dependencies
│   ├── run.py                  # Backend local server startup script
│   └── test_api.py             # Integration test script for the API endpoints
│
├── frontend/
│   ├── src/
│   │   ├── components/         # React Views (Shelves, LiveFeed, Settings)
│   │   ├── App.jsx             # Main dashboard controller
│   │   └── index.css           # Custom glassmorphic vanilla CSS theme
│   ├── package.json            # Node package specifications
│   └── vite.config.js          # Vite server configurations
│
├── test_pipeline.py            # Core ML math validation test script
└── README.md                   # Project documentation
```

---

## 🚀 Installation & Launch Guide

### 1. Pre-Train Batch SVD & NLP Models
Run the training pipeline from the project root to generate the serialized baseline models:
```bash
python -m backend.src.train
```

### 2. Start the Backend API
Install requirements and start the FastAPI local server:
```bash
cd backend
pip install -r requirements.txt
python run.py
```
*The API is now running on `http://127.0.0.1:8000`.*

### 3. Start the Frontend React App
Install packages and start the Vite development server:
```bash
cd frontend
npm install
npm run dev
```
*The React App is now running on `http://localhost:5173`.*

---

## 📡 API Endpoints Summary

* `GET /api/stats`: SVD explained variance, total users/movies, and RMSE.
* `GET /api/movies/popular`: Fallback universal shelf.
* `GET /api/movies/search?query=...`: Auto-complete title matches.
* `POST /api/onboarding`: Resolve cold-starts and retrieve a secure guest session ID.
* `GET /api/recommendations?userId=...`: Query ensembled predictions and XAI explanations.
* `POST /api/ratings`: Record likes/dislikes and trigger online SGD step.
* `GET /api/feed`: Real-time network stream of logs from all users.
* `POST /api/movies`: Admin add new movie.
* `DELETE /api/movies/{id}`: Admin soft delete/archive.
