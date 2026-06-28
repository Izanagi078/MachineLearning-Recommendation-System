"""Recommendations router — onboarding, recommendations, ratings, user ratings."""
import time
import uuid
from typing import Optional
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models_db import DBRating
from backend.app.schemas import OnboardingRequest, RatingCreate
from backend.app.dependencies import get_current_user_optional
from backend.app.cache import invalidate_all_caches

from backend.app.tmdb import enrich_movie_poster

router = APIRouter(prefix="", tags=["Recommendations"])


@router.post("/onboarding")
def user_onboarding(request: Request, req: OnboardingRequest, db: Session = Depends(get_db)):
    """Bootstrap a user's SVD profile via TF-IDF genre/keyword matching.

    If req.userId is provided (logged-in user), seeds ratings under that account
    instead of generating a new guest ID — session is never overwritten.
    """
    from backend.app.main import app

    effective_user_id = req.userId.strip() if req.userId else f"guest_{uuid.uuid4().hex[:8]}"

    combined_query = " ".join(req.genres) + " " + req.keywords
    combined_query = combined_query.strip().lower()
    if not combined_query:
        raise HTTPException(status_code=400, detail="Must provide at least one genre or keyword.")

    query_vector = app.state.content_model.vectorizer.transform([combined_query])
    active_movies = app.state.movies_df[app.state.movies_df["is_active"] == True]
    sims = np.dot(app.state.content_model.tfidf_matrix.toarray(), query_vector.toarray().T).flatten()

    sorted_indices = np.argsort(sims)[::-1]
    top_movie_ids = []
    for idx in sorted_indices:
        mid = app.state.content_model.movie_idx_to_id[idx]
        if not active_movies[active_movies["movieId"] == mid].empty:
            top_movie_ids.append(int(mid))
            if len(top_movie_ids) >= 5:
                break

    timestamp = int(time.time())
    new_ratings_list = []
    for mid in top_movie_ids:
        db.add(DBRating(userId=effective_user_id, movieId=mid, rating=5.0, timestamp=timestamp))
        app.state.col_model.update_rating_online(effective_user_id, mid, 5.0)
        new_ratings_list.append({"userId": effective_user_id, "movieId": mid, "rating": 5.0, "timestamp": timestamp})

    # Save explicit user preferences to DB for recommendations customization
    from backend.app.models_db import DBUserPreference
    db.query(DBUserPreference).filter(DBUserPreference.userId == effective_user_id).delete()
    for genre in req.genres:
        db.add(DBUserPreference(userId=effective_user_id, preference_type="genre", preference_value=genre))
    if req.keywords.strip():
        db.add(DBUserPreference(userId=effective_user_id, preference_type="keyword", preference_value=req.keywords.strip()))
    for mid in top_movie_ids:
        db.add(DBUserPreference(userId=effective_user_id, preference_type="seed_movie", preference_value=str(mid)))

    db.commit()
    new_ratings_df = pd.DataFrame(new_ratings_list)
    app.state.ratings_df = pd.concat([app.state.ratings_df, new_ratings_df], ignore_index=True)
    
    # Invalidate cache since database ratings count and metrics changed
    invalidate_all_caches()
    
    try:
        from backend.app.routers.feed import trigger_broadcast_update
        trigger_broadcast_update(db)
    except Exception as e:
        print(f"Failed to broadcast onboarding update: {e}")

    matched_records = active_movies[active_movies["movieId"].isin(top_movie_ids)].to_dict(orient="records")
    for r in matched_records:
        enrich_movie_poster(r, db)

    return {
        "userId": effective_user_id,
        "matched_movies": matched_records,
    }


@router.get("/recommendations")
def get_recommendations(
    request: Request,
    userId: str,
    weight_collaborative: float = 0.5,
    novelty_weight: float = 0.0,
    diversity_weight: float = 0.2,
    top_n: int = 10,
    current_user: Optional[str] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Fetch hybrid SVD + TF-IDF personalized recommendations with XAI explanations."""
    from backend.app.main import app

    if not userId.startswith("guest_"):
        if not current_user or current_user != userId:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing token.")

    # Debug logs for troubleshooting recommendation outputs
    user_ratings_in_df = app.state.ratings_df[app.state.ratings_df["userId"] == str(userId)]
    print(f"\n[Debug Recs] userId: {userId}")
    print(f"[Debug Recs] Ratings found in app.state.ratings_df: {len(user_ratings_in_df)}")
    if not user_ratings_in_df.empty:
        print(f"[Debug Recs] Ratings detail: {user_ratings_in_df.to_dict(orient='records')}")

    # Fetch persistent user preferences (genres, keywords, seeds)
    from backend.app.models_db import DBUserPreference
    prefs = db.query(DBUserPreference).filter(DBUserPreference.userId == userId).all()
    preferred_genres = [p.preference_value for p in prefs if p.preference_type == "genre"]
    preferred_keywords = [p.preference_value for p in prefs if p.preference_type == "keyword"]
    seed_movie_ids = {int(p.preference_value) for p in prefs if p.preference_type == "seed_movie"}

    recs = app.state.hybrid_recommender.get_recommendations(
        user_id=userId,
        movies_df=app.state.movies_df,
        ratings_df=app.state.ratings_df,
        top_n=top_n,
        weight_collaborative=weight_collaborative,
        diversity_weight=diversity_weight,
        novelty_weight=novelty_weight,
        preferred_genres=preferred_genres,
        preferred_keywords=preferred_keywords,
        seed_movie_ids=seed_movie_ids,
    )

    if recs.empty:
        return []

    records = recs.to_dict(orient="records")
    for r in records:
        r["explanation"] = app.state.hybrid_recommender.explain_recommendation(
            user_id=userId,
            movie_id=r["movieId"],
            ratings_df=app.state.ratings_df,
        )
        enrich_movie_poster(r, db)
    return records


@router.post("/ratings")
def submit_rating(
    request: Request,
    rating: RatingCreate,
    db: Session = Depends(get_db),
    current_user: Optional[str] = Depends(get_current_user_optional),
):
    """Record a like/dislike and trigger an online SGD update step immediately."""
    from backend.app.main import app

    if not rating.userId.startswith("guest_"):
        if not current_user or current_user != rating.userId:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing token.")

    timestamp = int(time.time())
    db.add(DBRating(userId=rating.userId, movieId=rating.movieId, rating=rating.rating, timestamp=timestamp))
    db.commit()

    app.state.col_model.update_rating_online(rating.userId, rating.movieId, rating.rating)

    new_row = pd.DataFrame([{
        "userId": rating.userId,
        "movieId": rating.movieId,
        "rating": rating.rating,
        "timestamp": timestamp,
    }])
    app.state.ratings_df = pd.concat([app.state.ratings_df, new_row], ignore_index=True)

    # Invalidate cache since database ratings count and metrics changed
    invalidate_all_caches()
    
    try:
        from backend.app.routers.feed import trigger_broadcast_update
        trigger_broadcast_update(db)
    except Exception as e:
        print(f"Failed to broadcast rating update: {e}")

    return {"message": "Rating processed and model updated in real-time."}


@router.get("/users/{userId}/ratings")
def get_user_ratings(request: Request, userId: str, db: Session = Depends(get_db)):
    """Returns all ratings submitted by a specific user."""
    ratings = db.query(DBRating).filter(DBRating.userId == userId).all()
    return {r.movieId: r.rating for r in ratings}
