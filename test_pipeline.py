import sys
import os
import numpy as np
import pandas as pd

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.src.data_loader import load_recommender_data
from backend.src.models import CollaborativeModel, ContentModel, HybridRecommender
from backend.src.evaluation import calculate_accuracy_metrics, calculate_map_k, calculate_ndcg_k

def run_tests():
    print("=== STARTING AUTOMATED PIPELINE TESTS ===")
    
    # 1. Test Ingestion & Data Loader
    print("\n1. Testing Ingestion and Data Loading...")
    ratings, movies, links = load_recommender_data()
    
    assert len(ratings) > 0, "Ratings DataFrame is empty"
    assert len(movies) > 0, "Movies DataFrame is empty"
    assert 'metadata_text' in movies.columns, "Metadata text column not created"
    assert not movies['metadata_text'].isnull().any(), "Metadata text contains NaNs"
    print(f"[OK] Ingestion passed. Loaded {len(ratings)} ratings, {len(movies)} movies.")
    
    # 2. Test Collaborative Filtering (SVD)
    print("\n2. Testing Collaborative Model (SVD)...")
    # Take a small subset of ratings for fast test fitting
    sample_ratings = ratings.sample(n=1000, random_state=42).copy()
    
    col_model = CollaborativeModel(n_factors=10)
    col_model.fit(sample_ratings, apply_decay=False)
    
    assert col_model.P is not None, "User factor matrix P not created"
    assert col_model.Q is not None, "Item factor matrix Q not created"
    
    # Test prediction
    test_user_id = sample_ratings['userId'].iloc[0]
    test_movie_id = sample_ratings['movieId'].iloc[0]
    pred_rating = col_model.predict_rating(test_user_id, test_movie_id)
    
    assert 0.5 <= pred_rating <= 5.0, f"Predicted rating {pred_rating} out of bounds"
    print(f"[OK] SVD collaborative fitting passed. Predict sample rating: {pred_rating:.2f}")
    
    # 3. Test Content-Based Model (TF-IDF)
    print("\n3. Testing Content-Based Model (TF-IDF)...")
    content_model = ContentModel()
    content_model.fit(movies)
    
    assert content_model.tfidf_matrix is not None, "TF-IDF matrix not fitted"
    assert content_model.tfidf_matrix.shape[0] == len(movies), "TF-IDF matrix row count mismatch"
    print(f"[OK] TF-IDF content fitting passed. Vocabulary size: {content_model.tfidf_matrix.shape[1]}")
    
    # 4. Test Evaluation Metrics
    print("\n4. Testing Evaluation Metrics Math...")
    # Mock data for accuracy
    y_true = np.array([4.0, 3.0, 5.0, 2.0])
    y_pred = np.array([3.8, 3.2, 4.7, 2.1])
    acc = calculate_accuracy_metrics(y_true, y_pred)
    assert acc['rmse'] > 0.0, "RMSE calculation error"
    assert acc['mae'] > 0.0, "MAE calculation error"
    
    # Mock data for ranking: {userId: list_of_movie_ids}
    recs = {1: [101, 102, 103, 104]}
    test_ratings = {1: [(101, 5.0), (102, 3.0), (105, 4.0)]}
    
    map_val = calculate_map_k(recs, test_ratings, k=4)
    ndcg_val = calculate_ndcg_k(recs, test_ratings, k=4)
    
    assert np.isclose(map_val, 0.5), f"MAP calculation mismatch: {map_val}"
    assert np.isclose(ndcg_val, 0.613, atol=0.01), f"NDCG calculation mismatch: {ndcg_val}"
    print(f"[OK] Accuracy (RMSE) and Ranking (MAP, NDCG) math checked successfully.")
    
    # 5. Test Hybrid Recommendation Engine
    print("\n5. Testing Hybrid Recommender Assembly...")
    hybrid_rec = HybridRecommender(col_model, content_model)
    
    # Retrieve recommendations for known user
    recs_df = hybrid_rec.get_recommendations(
        user_id=test_user_id,
        movies_df=movies,
        ratings_df=sample_ratings,
        top_n=5,
        weight_collaborative=0.5,
        diversity_weight=0.2,
        novelty_weight=0.1
    )
    
    assert len(recs_df) == 5, "Failed to retrieve top 5 recommendations"
    assert 'final_score' in recs_df.columns, "Score column missing"
    print(f"[OK] Hybrid Recommender recommendations retrieved successfully.")
    
    # 6. Test Online SVD SGD Updates
    print("\n6. Testing Online SVD SGD Updates...")
    # Add a rating and verify matrix changes
    user_row_idx = col_model.user_mapper[test_user_id]
    movie_col_idx = col_model.movie_mapper[test_movie_id]
    
    orig_p = col_model.P[user_row_idx].copy()
    orig_q = col_model.Q[movie_col_idx].copy()
    
    # Perform online rating update
    col_model.update_rating_online(test_user_id, test_movie_id, 5.0)
    
    updated_p = col_model.P[user_row_idx]
    updated_q = col_model.Q[movie_col_idx]
    
    # Ensure vectors have changed
    assert not np.array_equal(orig_p, updated_p), "User latent vector did not update"
    assert not np.array_equal(orig_q, updated_q), "Movie latent vector did not update"
    print(f"[OK] Online SVD SGD rating updates shift latent vectors successfully.")
    
    print("\n=== ALL PIPELINE TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_tests()
