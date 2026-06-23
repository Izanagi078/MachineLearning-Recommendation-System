import os
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.data_loader import load_recommender_data
from src.models import CollaborativeModel, ContentModel, HybridRecommender
from src.evaluation import calculate_accuracy_metrics, calculate_map_k, calculate_ndcg_k, calculate_precision_recall_k

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')

def train_and_save_models():
    """
    Loads MovieLens data, runs train/test split metrics evaluation,
    fits final models on full data, and pickles them.
    """
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)
        
    print("[train] Loading dataset...")
    ratings, movies, links = load_recommender_data()
    
    # --- 1. Model Validation (80/20 Train-Test Split) ---
    print("\n--- Model Validation (80/20 Split) ---")
    train_ratings, test_ratings = train_test_split(ratings, test_size=0.2, random_state=42)
    
    # Fit SVD on train set
    col_val = CollaborativeModel(n_factors=50)
    col_val.fit(train_ratings, apply_decay=True)
    
    # Fit Content model
    content_val = ContentModel()
    content_val.fit(movies)
    
    # A. Accuracy Metrics (RMSE / MAE)
    print("[train] Calculating accuracy error metrics on test set...")
    # Get y_true and y_pred for known test user-movie entries
    test_user_movie_pairs = test_ratings[['userId', 'movieId', 'rating']].values
    y_true = []
    y_pred = []
    
    for uid, mid, rating in test_user_movie_pairs:
        # We only predict if SVD knows the movie, else it defaults safely
        pred = col_val.predict_rating(int(uid), int(mid))
        y_true.append(rating)
        y_pred.append(pred)
        
    accuracy_results = calculate_accuracy_metrics(np.array(y_true), np.array(y_pred))
    print(f"  Collaborative SVD Test RMSE: {accuracy_results['rmse']:.4f}")
    print(f"  Collaborative SVD Test MAE:  {accuracy_results['mae']:.4f}")
    
    # B. Ranking Metrics (MAP@10 / NDCG@10)
    print("[train] Evaluating ranking performance (MAP@10, NDCG@10) on sampled test users...")
    # Build test ratings dict: {userId: [(movieId, rating), ...]}
    test_ratings_dict = {}
    for uid, g in test_ratings.groupby('userId'):
        test_ratings_dict[int(uid)] = list(zip(g['movieId'].astype(int), g['rating'].astype(float)))
        
    # Sample 100 users who have at least one relevant rating (>= 4.0) in the test set
    test_users_with_likes = [
        uid for uid, ratings_list in test_ratings_dict.items()
        if any(r >= 4.0 for _, r in ratings_list)
    ]
    
    # Limit sample size to 100 for speed
    np.random.seed(42)
    sampled_users = np.random.choice(test_users_with_likes, size=min(100, len(test_users_with_likes)), replace=False)
    
    # Generate top-10 hybrid recommendations for each sampled user
    recommender_val = HybridRecommender(col_val, content_val)
    recommendations_dict = {}
    
    for uid in sampled_users:
        recs_df = recommender_val.get_recommendations(
            user_id=int(uid),
            movies_df=movies,
            ratings_df=train_ratings,
            top_n=10,
            weight_collaborative=0.5,
            diversity_weight=0.0,
            novelty_weight=0.0
        )
        recommendations_dict[int(uid)] = recs_df['movieId'].tolist()
        
    # Calculate MAP@10 and NDCG@10
    map_10 = calculate_map_k(recommendations_dict, test_ratings_dict, k=10)
    ndcg_10 = calculate_ndcg_k(recommendations_dict, test_ratings_dict, k=10)
    precision_10, recall_10 = calculate_precision_recall_k(recommendations_dict, test_ratings_dict, k=10)
    
    print(f"  Hybrid System MAP@10:       {map_10 * 100:.2f}%")
    print(f"  Hybrid System NDCG@10:      {ndcg_10 * 100:.2f}%")
    print(f"  Hybrid System Precision@10: {precision_10 * 100:.2f}%")
    print(f"  Hybrid System Recall@10:    {recall_10 * 100:.2f}%")
    
    # --- 2. Fit Final Models on 100% of Data ---
    print("\n--- Training Final Models on Full Dataset ---")
    final_col = CollaborativeModel(n_factors=50)
    final_col.fit(ratings, apply_decay=True)
    
    final_content = ContentModel()
    final_content.fit(movies)
    
    # --- 3. Serialize & Cache Final Models ---
    print("\n--- Serializing Models & Caching Datasets ---")
    
    # Save Collaborative Model
    col_path = os.path.join(MODELS_DIR, 'collaborative_model.pkl')
    with open(col_path, 'wb') as f:
        pickle.dump(final_col, f)
        
    # Save Content Model
    content_path = os.path.join(MODELS_DIR, 'content_model.pkl')
    with open(content_path, 'wb') as f:
        pickle.dump(final_content, f)
        
    # Save Data Cache (to make dashboard load instantly)
    data_cache = {
        'ratings': ratings,
        'movies': movies,
        'links': links,
        'metrics': {
            'rmse': accuracy_results['rmse'],
            'mae': accuracy_results['mae'],
            'map_10': map_10,
            'ndcg_10': ndcg_10
        }
    }
    cache_path = os.path.join(MODELS_DIR, 'data_cache.pkl')
    with open(cache_path, 'wb') as f:
        pickle.dump(data_cache, f)
        
    print(f"[train] Successfully saved SVD model, TF-IDF model, and datasets to {MODELS_DIR}")

if __name__ == "__main__":
    train_and_save_models()
