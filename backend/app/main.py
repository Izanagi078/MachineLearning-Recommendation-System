import os
import pickle
import time
import uuid
import numpy as np
import pandas as pd
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.app.database import engine, SessionLocal, get_db, Base
from backend.app.models_db import DBMovie, DBRating, DBUser
from backend.app.schemas import OnboardingRequest, RatingCreate, MovieCreate, UserAuth, TokenResponse
from backend.src.models import CollaborativeModel, ContentModel, HybridRecommender
import hmac
import hashlib
import base64
import json
import secrets

SECRET_KEY = os.environ.get("JWT_SECRET", "super-secret-key-12345")

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${key.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, key_hex = hashed.split("$")
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hmac.compare_digest(key.hex(), key_hex)
    except Exception:
        return False

def generate_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": int(time.time()) + 86400 * 7  # 7 days validity
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return f"{payload_b64}.{sig_b64}"

def verify_token(token: str) -> Optional[str]:
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig_b64 = parts[0], parts[1]
        
        pad = len(payload_b64) % 4
        payload_b64_padded = payload_b64 + ("=" * (4 - pad) if pad else "")
        payload_bytes = base64.urlsafe_b64decode(payload_b64_padded)
        payload = json.loads(payload_bytes.decode())
        
        if payload.get("exp", 0) < time.time():
            return None
            
        expected_sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
        
        if hmac.compare_digest(sig_b64, expected_sig_b64):
            return payload.get("sub")
    except Exception:
        return None
    return None

def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[str]:
    if not authorization:
        return None
    try:
        if authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            return verify_token(token)
    except Exception:
        return None
    return None

# Initialize FastAPI App
app = FastAPI(
    title="🎬 Production Recommendation Engine API",
    description="FastAPI Backend with Real-Time Online SVD learning, SQLite persistence, and Hybrid filtering.",
    version="1.0.0"
)

# Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-User-ID"]
)

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')

# Load and Synchronize Model States on Startup
@app.on_event("startup")
def startup_event():
    # 1. Initialize SQLite Database
    Base.metadata.create_all(bind=engine)
    
    col_path = os.path.join(MODELS_DIR, 'collaborative_model.pkl')
    content_path = os.path.join(MODELS_DIR, 'content_model.pkl')
    cache_path = os.path.join(MODELS_DIR, 'data_cache.pkl')
    
    if not (os.path.exists(col_path) and os.path.exists(content_path) and os.path.exists(cache_path)):
        raise RuntimeError("Cached models not found in models/ directory. Run batch training first.")
        
    print("[Startup] Loading batch-trained models and dataset cache...")
    with open(col_path, 'rb') as f:
        app.state.col_model = pickle.load(f)
    with open(content_path, 'rb') as f:
        app.state.content_model = pickle.load(f)
    with open(cache_path, 'rb') as f:
        app.state.cache = pickle.load(f)
        
    db = SessionLocal()
    try:
        # 2. Seed SQLite movies table if empty
        db_movie_count = db.query(DBMovie).count()
        if db_movie_count == 0:
            print("[Startup] Seeding database movies table from cached data...")
            movies_to_insert = []
            for _, row in app.state.cache['movies'].iterrows():
                # Extract year and cleanup
                title_str = str(row['title'])
                genres_str = str(row['genres'])
                metadata_text = row.get('metadata_text', f"{title_str} {genres_str.replace('|', ' ')}")
                
                # Fetch tmdbId from links cache
                links_df = app.state.cache['links']
                tmdb_row = links_df[links_df['movieId'] == row['movieId']]
                tmdb_id = int(tmdb_row['tmdbId'].values[0]) if not tmdb_row.empty and not pd.isna(tmdb_row['tmdbId'].values[0]) else None
                
                movies_to_insert.append(DBMovie(
                    movieId=int(row['movieId']),
                    title=title_str,
                    genres=genres_str,
                    metadata_text=str(metadata_text),
                    tmdbId=tmdb_id,
                    is_active=True
                ))
            db.bulk_save_objects(movies_to_insert)
            db.commit()
            print(f"[Startup] Seeded {len(movies_to_insert)} movies successfully.")

        # 3. Load catalog movies from database into memory (including any added dynamically)
        all_movies = db.query(DBMovie).all()
        movies_list = []
        for m in all_movies:
            movies_list.append({
                'movieId': m.movieId,
                'title': m.title,
                'genres': m.genres,
                'metadata_text': m.metadata_text,
                'tmdbId': m.tmdbId,
                'is_active': m.is_active
            })
        app.state.movies_df = pd.DataFrame(movies_list)
        
        # Fit ContentModel with full current catalog
        app.state.content_model.fit(app.state.movies_df)
        
        # Sync CollaborativeModel movie mappings
        for m in all_movies:
            app.state.col_model.register_new_movie(m.movieId)
            
        # 4. Replay live user ratings from database to update user/movie vectors
        db_ratings = db.query(DBRating).order_by(DBRating.timestamp.asc()).all()
        print(f"[Startup] Replaying {len(db_ratings)} live interactions to SVD matrices...")
        for r in db_ratings:
            app.state.col_model.update_rating_online(r.userId, r.movieId, r.rating)
            
        # Build composite ratings dataframe (base dataset + dynamic db ratings)
        base_ratings = app.state.cache['ratings'].copy()
        # Ensure base columns match types
        base_ratings['userId'] = base_ratings['userId'].astype(str)
        
        if db_ratings:
            live_ratings_list = [{
                'userId': str(r.userId),
                'movieId': int(r.movieId),
                'rating': float(r.rating),
                'timestamp': int(r.timestamp)
            } for r in db_ratings]
            live_ratings_df = pd.DataFrame(live_ratings_list)
            app.state.ratings_df = pd.concat([base_ratings, live_ratings_df], ignore_index=True)
        else:
            app.state.ratings_df = base_ratings

        # Initialize Hybrid Coordination
        app.state.hybrid_recommender = HybridRecommender(app.state.col_model, app.state.content_model)
        print("[Startup] Backend successfully synchronized and ready.")
        
    finally:
        db.close()

# API Routes

@app.post("/api/auth/register", response_model=TokenResponse)
def register(auth: UserAuth, db: Session = Depends(get_db)):
    username = auth.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty.")
    if len(auth.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters long.")
    
    existing = db.query(DBUser).filter(DBUser.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists.")
        
    hashed = hash_password(auth.password)
    new_user = DBUser(username=username, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    
    token = generate_token(username)
    return {"token": token, "username": username}

@app.post("/api/auth/login", response_model=TokenResponse)
def login(auth: UserAuth, db: Session = Depends(get_db)):
    username = auth.username.strip()
    user = db.query(DBUser).filter(DBUser.username == username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid username or password.")
        
    if not verify_password(auth.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid username or password.")
        
    token = generate_token(username)
    return {"token": token, "username": username}

@app.post("/api/auth/demo", response_model=TokenResponse)
def login_demo(auth: UserAuth):
    username = auth.username.strip()
    if not username.startswith("User ") and not username.startswith("guest_"):
        raise HTTPException(status_code=400, detail="Not a valid demo or guest username.")
    
    token = generate_token(username)
    return {"token": token, "username": username}

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """
    Returns data pipeline diagnostics, metrics, and models state sizing.
    """
    db_ratings_count = db.query(DBRating).count()
    db_movies_count = db.query(DBMovie).filter(DBMovie.is_active == True).count()
    
    total_ratings = len(app.state.ratings_df)
    total_users = len(app.state.col_model.user_mapper)
    
    return {
        "total_ratings": total_ratings,
        "live_ratings": db_ratings_count,
        "users_count": total_users,
        "movies_count": db_movies_count,
        "svd_components": app.state.col_model.n_factors,
        "metrics": {
            "rmse": float(app.state.cache['metrics']['rmse']),
            "ndcg_10": float(app.state.cache['metrics']['ndcg_10']),
            "map_10": float(app.state.cache['metrics']['map_10'])
        }
    }

@app.get("/api/movies/popular")
def get_popular_movies(limit: int = 10):
    """
    Returns global popular hits (fallback universal shelf).
    """
    popularity = app.state.ratings_df.groupby('movieId').size().reset_index(name='hits')
    merged = popularity.merge(app.state.movies_df, on='movieId')
    
    # Filter active movies only
    active = merged[merged['is_active'] == True]
    popular = active.sort_values(by='hits', ascending=False).head(limit)
    
    return popular.to_dict(orient="records")

@app.get("/api/movies/search")
def search_movies(query: str, limit: int = 10):
    """
    Searches active movies by title.
    """
    if not query:
        return []
    
    active = app.state.movies_df[app.state.movies_df['is_active'] == True]
    matches = active[active['title'].str.contains(query, case=False, na=False)].head(limit)
    return matches.to_dict(orient="records")

@app.post("/api/onboarding")
def user_onboarding(req: OnboardingRequest, db: Session = Depends(get_db)):
    """
    Handles onboarding by matching genres/keywords via TF-IDF, seeding initial
    ratings to bootstrap the SVD profile. If the caller is already a registered
    user (passes req.userId), ratings are seeded under that account so their
    session is never overwritten by a new guest ID.
    """
    # 1. Use caller's existing userId if provided, else create a new guest ID
    effective_user_id = req.userId.strip() if req.userId else f"guest_{uuid.uuid4().hex[:8]}"

    # 2. Match movies based on genres & keywords
    combined_query = " ".join(req.genres) + " " + req.keywords
    combined_query = combined_query.strip().lower()

    if not combined_query:
        raise HTTPException(status_code=400, detail="Must provide at least one genre or keyword")

    # Transform and check similarities
    query_vector = app.state.content_model.vectorizer.transform([combined_query])
    active_movies = app.state.movies_df[app.state.movies_df['is_active'] == True]

    # Cosine similarities
    sims = np.dot(app.state.content_model.tfidf_matrix.toarray(), query_vector.toarray().T).flatten()

    # Map index to movie id and get top matches
    sorted_indices = np.argsort(sims)[::-1]
    top_movie_ids = []

    for idx in sorted_indices:
        mid = app.state.content_model.movie_idx_to_id[idx]
        movie_row = active_movies[active_movies['movieId'] == mid]
        if not movie_row.empty:
            top_movie_ids.append(int(mid))
            if len(top_movie_ids) >= 5:
                break

    # 3. Insert 5.0 seed ratings under effective_user_id to bootstrap SVD profile
    timestamp = int(time.time())
    new_ratings_list = []

    for mid in top_movie_ids:
        rating_obj = DBRating(userId=effective_user_id, movieId=mid, rating=5.0, timestamp=timestamp)
        db.add(rating_obj)

        app.state.col_model.update_rating_online(effective_user_id, mid, 5.0)

        new_ratings_list.append({
            'userId': effective_user_id,
            'movieId': mid,
            'rating': 5.0,
            'timestamp': timestamp
        })

    db.commit()

    new_ratings_df = pd.DataFrame(new_ratings_list)
    app.state.ratings_df = pd.concat([app.state.ratings_df, new_ratings_df], ignore_index=True)

    return {
        "userId": effective_user_id,
        "matched_movies": active_movies[active_movies['movieId'].isin(top_movie_ids)].to_dict(orient="records")
    }

@app.get("/api/recommendations")
def get_recommendations(
    userId: str,
    weight_collaborative: float = 0.5,
    novelty_weight: float = 0.0,
    diversity_weight: float = 0.2,
    top_n: int = 10,
    current_user: Optional[str] = Depends(get_current_user_optional)
):
    """
    Fetches personalized hybrid recommendations with explanation details.
    """
    # Enforce auth verification for non-guest sessions
    if not userId.startswith("guest_"):
        if not current_user or current_user != userId:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing token.")

    recs = app.state.hybrid_recommender.get_recommendations(
        user_id=userId,
        movies_df=app.state.movies_df,
        ratings_df=app.state.ratings_df,
        top_n=top_n,
        weight_collaborative=weight_collaborative,
        diversity_weight=diversity_weight,
        novelty_weight=novelty_weight
    )
    
    if recs.empty:
        return []
        
    # Generate explanation data
    records = recs.to_dict(orient="records")
    response_list = []
    
    for r in records:
        explanation = app.state.hybrid_recommender.explain_recommendation(
            user_id=userId,
            movie_id=r['movieId'],
            ratings_df=app.state.ratings_df
        )
        r['explanation'] = explanation
        response_list.append(r)
        
    return response_list

@app.post("/api/ratings")
def submit_rating(
    rating: RatingCreate, 
    db: Session = Depends(get_db),
    current_user: Optional[str] = Depends(get_current_user_optional)
):
    """
    Saves a rating (like/dislike) and updates the in-memory SVD coordinates immediately.
    """
    # Enforce auth verification for non-guest ratings
    if not rating.userId.startswith("guest_"):
        if not current_user or current_user != rating.userId:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing token.")

    timestamp = int(time.time())
    
    # 1. Insert into SQLite
    db_rating = DBRating(
        userId=rating.userId,
        movieId=rating.movieId,
        rating=rating.rating,
        timestamp=timestamp
    )
    db.add(db_rating)
    db.commit()
    
    # 2. Update SVD model in-memory (SGD Step)
    app.state.col_model.update_rating_online(rating.userId, rating.movieId, rating.rating)
    
    # 3. Update active pandas ratings DataFrame
    new_rating_row = pd.DataFrame([{
        'userId': rating.userId,
        'movieId': rating.movieId,
        'rating': rating.rating,
        'timestamp': timestamp
    }])
    app.state.ratings_df = pd.concat([app.state.ratings_df, new_rating_row], ignore_index=True)
    
    return {"message": "Rating processed successfully and model updated in real-time."}

@app.get("/api/users/{userId}/ratings")
def get_user_ratings(userId: str, db: Session = Depends(get_db)):
    """
    Returns all ratings submitted by a specific user in SQLite.
    """
    ratings = db.query(DBRating).filter(DBRating.userId == userId).all()
    return {r.movieId: r.rating for r in ratings}

@app.get("/api/feed")
def get_global_feed(db: Session = Depends(get_db), limit: int = 10):
    """
    Returns latest rating logs from SQLite (shared live network feed).
    """
    results = db.query(DBRating, DBMovie)\
        .join(DBMovie, DBRating.movieId == DBMovie.movieId)\
        .order_by(DBRating.timestamp.desc())\
        .limit(limit).all()
        
    feed = []
    for r, m in results:
        feed.append({
            "id": r.id,
            "userId": r.userId,
            "movieId": r.movieId,
            "title": m.title,
            "rating": r.rating,
            "timestamp": r.timestamp
        })
    return feed

@app.post("/api/movies")
def add_movie(
    movie: MovieCreate, 
    db: Session = Depends(get_db),
    current_user: Optional[str] = Depends(get_current_user_optional)
):
    """
    Admin Route: Dynamically adds a new movie to catalog and indexes it in SVD and TF-IDF.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized: A valid auth token is required to modify catalog.")

    # Create new ID
    max_id = db.query(DBMovie).order_by(DBMovie.movieId.desc()).first()
    new_movie_id = (max_id.movieId + 1) if max_id else 1
    
    metadata_text = f"{movie.title} {movie.genres.replace('|', ' ')}"
    
    # 1. Insert into SQLite
    db_movie = DBMovie(
        movieId=new_movie_id,
        title=movie.title,
        genres=movie.genres,
        metadata_text=metadata_text,
        tmdbId=None,
        is_active=True
    )
    db.add(db_movie)
    db.commit()
    db.refresh(db_movie)
    
    # 2. Register in RAM Collaborative SVD
    app.state.col_model.register_new_movie(new_movie_id)
    
    # 3. Register in RAM Content TF-IDF Similarity
    app.state.content_model.register_new_movie(new_movie_id, movie.title, movie.genres, metadata_text)
    
    # 4. Rebuild app.state.movies_df
    new_row = pd.DataFrame([{
        'movieId': new_movie_id,
        'title': movie.title,
        'genres': movie.genres,
        'metadata_text': metadata_text,
        'tmdbId': None,
        'is_active': True
    }])
    app.state.movies_df = pd.concat([app.state.movies_df, new_row], ignore_index=True)
    
    return db_movie
 
@app.delete("/api/movies/{movieId}")
def delete_movie(
    movieId: int, 
    db: Session = Depends(get_db),
    current_user: Optional[str] = Depends(get_current_user_optional)
):
    """
    Admin Route: Soft deletes a movie (marks inactive), removing it from recommendations list.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized: A valid auth token is required to modify catalog.")

    db_movie = db.query(DBMovie).filter(DBMovie.movieId == movieId).first()
    if not db_movie:
        raise HTTPException(status_code=404, detail="Movie not found")
        
    db_movie.is_active = False
    db.commit()
    
    # Update in-memory movies_df
    app.state.movies_df.loc[app.state.movies_df['movieId'] == movieId, 'is_active'] = False
    
    return {"message": f"Movie {movieId} archived successfully."}
