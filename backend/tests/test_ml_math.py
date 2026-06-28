"""
test_ml_math.py — Unit tests for ML recommendation math.
Covers: CollaborativeModel SVD fitting/prediction/online updates, ContentModel TF-IDF vectorization.
"""
import numpy as np
import pandas as pd
import pytest
from backend.src.models import CollaborativeModel, ContentModel

def test_collaborative_model_fit_and_update():
    # 1. Create a dummy ratings dataset
    ratings_data = pd.DataFrame([
        {"userId": "1", "movieId": 101, "rating": 5.0, "timestamp": 1000000},
        {"userId": "1", "movieId": 102, "rating": 3.0, "timestamp": 1000000},
        {"userId": "2", "movieId": 101, "rating": 4.0, "timestamp": 1000000},
        {"userId": "2", "movieId": 103, "rating": 2.0, "timestamp": 1000000},
        {"userId": "3", "movieId": 102, "rating": 4.5, "timestamp": 1000000},
        {"userId": "3", "movieId": 103, "rating": 5.0, "timestamp": 1000000},
    ])

    model = CollaborativeModel(n_factors=2)
    model.fit(ratings_data, apply_decay=False)

    assert model.P is not None
    assert model.Q is not None
    assert model.P.shape[0] == 3  # 3 users
    assert model.Q.shape[0] == 3  # 3 movies

    # 2. Predict rating
    pred = model.predict_rating("1", 101)
    assert 0.5 <= pred <= 5.0

    # 3. Test online SVD update
    u_idx = model.user_mapper["1"]
    m_idx = model.movie_mapper[103]

    p_before = model.P[u_idx].copy()
    q_before = model.Q[m_idx].copy()

    # Perform online SGD update
    model.update_rating_online("1", 103, 5.0)

    p_after = model.P[u_idx]
    q_after = model.Q[m_idx]

    # Latent vectors must shift
    assert not np.array_equal(p_before, p_after)
    assert not np.array_equal(q_before, q_after)

def test_content_model_tfidf():
    # 1. Create dummy movie dataset
    movies_data = pd.DataFrame([
        {"movieId": 101, "title": "Space Battles", "genres": "Sci-Fi|Action", "metadata_text": "Space Battles Sci-Fi Action"},
        {"movieId": 102, "title": "Love Story", "genres": "Romance|Drama", "metadata_text": "Love Story Romance Drama"},
        {"movieId": 103, "title": "Funny Movie", "genres": "Comedy", "metadata_text": "Funny Movie Comedy"},
    ])

    model = ContentModel()
    model.fit(movies_data)

    assert model.tfidf_matrix is not None
    assert model.tfidf_matrix.shape[0] == 3
    # Check vocabulary size is positive
    assert len(model.vectorizer.vocabulary_) > 0

    # 2. Add a new movie dynamically
    new_idx = model.register_new_movie(104, "Dark Space", "Sci-Fi|Horror")
    assert new_idx == 3
    assert model.tfidf_matrix.shape[0] == 4
    assert 104 in model.movie_id_to_idx

def test_hybrid_recommender_onboarding_preferences():
    from backend.src.models import HybridRecommender
    
    # 1. Create a dummy movies dataset
    movies_data = pd.DataFrame([
        {"movieId": 1, "title": "Romance 1", "genres": "Romance|Fantasy", "metadata_text": "romance 1 romance fantasy"},
        {"movieId": 2, "title": "Romance 2", "genres": "Romance|Drama", "metadata_text": "romance 2 romance drama"},
        {"movieId": 3, "title": "Drama 1", "genres": "Drama|Comedy", "metadata_text": "drama 1 drama comedy"},
        {"movieId": 4, "title": "Comedy 1", "genres": "Comedy", "metadata_text": "comedy 1 comedy"},
        {"movieId": 5, "title": "Fantasy 1", "genres": "Fantasy|Romance", "metadata_text": "fantasy 1 fantasy romance"},
    ])
    
    col_model = CollaborativeModel(n_factors=2)
    # Fit SVD on some dummy ratings
    ratings_data = pd.DataFrame([
        {"userId": "1", "movieId": 1, "rating": 4.0, "timestamp": 100000},
        {"userId": "1", "movieId": 3, "rating": 5.0, "timestamp": 100000},
        {"userId": "2", "movieId": 2, "rating": 3.0, "timestamp": 100000},
    ])
    col_model.fit(ratings_data, apply_decay=False)
    
    content_model = ContentModel()
    content_model.fit(movies_data)
    
    recommender = HybridRecommender(col_model, content_model)
    
    # User has rated "Romance 2" (contains Romance/Drama) during onboarding
    user_id = "guest_onboard"
    ratings_df = pd.DataFrame([
        {"userId": user_id, "movieId": 2, "rating": 5.0, "timestamp": 100000}
    ])
    col_model.register_new_user(user_id)
    col_model.update_rating_online(user_id, 2, 5.0)
    
    # Recommendations with preferred genres Romance and Fantasy
    recs = recommender.get_recommendations(
        user_id=user_id,
        movies_df=movies_data,
        ratings_df=ratings_df,
        top_n=3,
        weight_collaborative=0.5,
        diversity_weight=0.2,
        novelty_weight=0.0,
        preferred_genres=["Romance", "Fantasy"],
        seed_movie_ids={2}
    )
    
    assert not recs.empty
    titles = recs["title"].tolist()
    # "Romance 2" is excluded because it's rated.
    # The remaining candidates are Romance 1, Drama 1, Comedy 1, Fantasy 1.
    # Romance 1 (Romance|Fantasy) and Fantasy 1 (Fantasy|Romance) match BOTH preferred genres Romance & Fantasy, and should be ranked at the top!
    # Drama 1 (Drama|Comedy) and Comedy 1 (Comedy) do not match preferred genres, so they should be lower.
    assert "Romance 1" in titles
    assert "Fantasy 1" in titles
    # The top recommended movie should be Romance 1 or Fantasy 1
    assert titles[0] in ["Romance 1", "Fantasy 1"]

