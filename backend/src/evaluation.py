import numpy as np
import pandas as pd

def calculate_accuracy_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Computes regression error metrics: RMSE and MAE.
    """
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    mae = np.mean(np.abs(y_true - y_pred))
    return {
        'rmse': rmse,
        'mae': mae
    }

def calculate_map_k(recommendations_dict: dict, test_ratings_dict: dict, k: int = 10, rel_threshold: float = 4.0) -> float:
    """
    Computes Mean Average Precision at K (MAP@K).
    Args:
        recommendations_dict: dict of {userId: list_of_recommended_movie_ids}
        test_ratings_dict: dict of {userId: list_of_tuples_(movie_id, rating)_in_test_set}
        k: the cut-off rank
        rel_threshold: minimum rating to consider an item relevant (default: 4.0)
    """
    aps = []
    
    for uid, recs in recommendations_dict.items():
        if uid not in test_ratings_dict:
            continue
            
        # Extract list of relevant movie IDs in the test set for this user
        test_movies = test_ratings_dict[uid]
        relevant_movies = set([mid for mid, rating in test_movies if rating >= rel_threshold])
        
        if not relevant_movies:
            # Skip users with no relevant items in test set (cannot compute precision)
            continue
            
        # Take top K recommendations
        top_recs = recs[:k]
        
        hits = 0
        sum_precisions = 0.0
        
        for i, rec_id in enumerate(top_recs):
            if rec_id in relevant_movies:
                hits += 1
                precision_at_i = hits / (i + 1)
                sum_precisions += precision_at_i
                
        ap = sum_precisions / min(len(relevant_movies), k)
        aps.append(ap)
        
    return float(np.mean(aps)) if aps else 0.0

def calculate_ndcg_k(recommendations_dict: dict, test_ratings_dict: dict, k: int = 10, rel_threshold: float = 4.0) -> float:
    """
    Computes Normalized Discounted Cumulative Gain at K (NDCG@K) using binary relevance.
    """
    ndcgs = []
    
    for uid, recs in recommendations_dict.items():
        if uid not in test_ratings_dict:
            continue
            
        test_movies = test_ratings_dict[uid]
        relevant_movies = set([mid for mid, rating in test_movies if rating >= rel_threshold])
        
        if not relevant_movies:
            continue
            
        top_recs = recs[:k]
        
        # Calculate DCG@K
        dcg = 0.0
        for i, rec_id in enumerate(top_recs):
            if rec_id in relevant_movies:
                # Rank i is 0-indexed, so rank index for formula is i + 1
                dcg += 1.0 / np.log2(i + 2)
                
        # Calculate IDCG@K (Ideal DCG where all hit recommendations rank first)
        idcg = 0.0
        n_ideal = min(len(relevant_movies), k)
        for i in range(n_ideal):
            idcg += 1.0 / np.log2(i + 2)
            
        ndcg = dcg / idcg if idcg > 0.0 else 0.0
        ndcgs.append(ndcg)
        
    return float(np.mean(ndcgs)) if ndcgs else 0.0

def calculate_precision_recall_k(recommendations_dict: dict, test_ratings_dict: dict, k: int = 10, rel_threshold: float = 4.0) -> tuple:
    """
    Computes average Precision@K and Recall@K.
    """
    precisions = []
    recalls = []
    
    for uid, recs in recommendations_dict.items():
        if uid not in test_ratings_dict:
            continue
            
        test_movies = test_ratings_dict[uid]
        relevant_movies = set([mid for mid, rating in test_movies if rating >= rel_threshold])
        
        if not relevant_movies:
            continue
            
        top_recs = recs[:k]
        
        # Calculate hits
        hits = len(set(top_recs).intersection(relevant_movies))
        
        precision = hits / k
        recall = hits / len(relevant_movies)
        
        precisions.append(precision)
        recalls.append(recall)
        
    avg_precision = float(np.mean(precisions)) if precisions else 0.0
    avg_recall = float(np.mean(recalls)) if recalls else 0.0
    return avg_precision, avg_recall
