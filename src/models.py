import os
import pickle
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

class CollaborativeModel:
    """
    Collaborative Filtering using Matrix Factorization via scikit-learn's TruncatedSVD.
    Includes user-mean centering and temporal decay adjustments.
    """
    def __init__(self, n_factors=50):
        self.n_factors = n_factors
        self.svd = None
        self.user_means = None
        self.reconstructed_matrix = None
        self.user_mapper = {}  # userId -> row_idx
        self.movie_mapper = {}  # movieId -> col_idx
        self.inv_movie_mapper = {}
        self.global_mean = 3.5

    def fit(self, ratings_df: pd.DataFrame, apply_decay: bool = True, decay_lambda: float = 0.05):
        """
        Fits TruncatedSVD on the user-movie rating matrix.
        If apply_decay is True, older ratings decay towards the user mean rating (zero centered).
        """
        # Save global average rating
        self.global_mean = ratings_df['rating'].mean()
        
        # 1. Pivot ratings table (userId x movieId)
        pivot = ratings_df.pivot(index='userId', columns='movieId', values='rating')
        self.user_means = pivot.mean(axis=1)
        
        # 2. Centering: Subtract user mean from their ratings
        pivot_centered = pivot.sub(self.user_means, axis=0)
        
        # 3. Apply Temporal Decay to centered ratings
        if apply_decay and 'timestamp' in ratings_df.columns:
            max_time = ratings_df['timestamp'].max()
            # Calculate time difference in years
            time_diff_years = (max_time - ratings_df['timestamp']) / (60 * 60 * 24 * 365)
            decay_weights = np.exp(-decay_lambda * time_diff_years)
            
            # Map decay weights to the centered pivot matrix
            # Build ratings_df with weights
            ratings_weighted = ratings_df.copy()
            ratings_weighted['weight'] = decay_weights
            ratings_weighted['weighted_centered'] = (ratings_weighted['rating'] - ratings_weighted['userId'].map(self.user_means)) * ratings_weighted['weight']
            
            # Re-pivot the weighted centered ratings
            pivot_imputed = ratings_weighted.pivot(index='userId', columns='movieId', values='weighted_centered')
        else:
            pivot_imputed = pivot_centered
            
        # 4. Fill missing centered values with 0.0 (imputation at user mean)
        pivot_imputed = pivot_imputed.fillna(0.0)
        
        # 5. Fit SVD on centered/imputed matrix
        n_components = min(self.n_factors, pivot_imputed.shape[0] - 1, pivot_imputed.shape[1] - 1)
        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        latent_matrix = self.svd.fit_transform(pivot_imputed.values)
        
        # 6. Reconstruct centered ratings
        reconstructed_centered = np.dot(latent_matrix, self.svd.components_)
        
        # 7. Add user means back (de-centering)
        self.reconstructed_matrix = reconstructed_centered + self.user_means.values[:, np.newaxis]
        
        # Store index mappers
        self.user_ids = pivot.index.tolist()
        self.movie_ids = pivot.columns.tolist()
        self.user_mapper = {uid: idx for idx, uid in enumerate(self.user_ids)}
        self.movie_mapper = {mid: idx for idx, mid in enumerate(self.movie_ids)}
        self.inv_movie_mapper = {idx: mid for idx, mid in enumerate(self.movie_ids)}
        print(f"[CollaborativeModel] Trained SVD with {n_components} factors. Matrix shape: {pivot.shape}")

    def predict_rating(self, user_id: int, movie_id: int) -> float:
        """
        Predicts user rating for a movie. Cliped to standard [0.5, 5.0] range.
        """
        user_known = user_id in self.user_mapper
        movie_known = movie_id in self.movie_mapper
        
        if user_known and movie_known:
            u_idx = self.user_mapper[user_id]
            m_idx = self.movie_mapper[movie_id]
            return np.clip(self.reconstructed_matrix[u_idx, m_idx], 0.5, 5.0)
        elif user_known:
            # User is known, movie is cold start
            return self.user_means[user_id]
        elif movie_known:
            # Movie is known, user is cold start
            return self.global_mean
        else:
            # Both cold start
            return self.global_mean

class ContentModel:
    """
    Content-Based Filtering using TF-IDF on Movie metadata (Title + Genres + Tags).
    """
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', sublinear_tf=True)
        self.tfidf_matrix = None
        self.movies_df = None
        self.movie_id_to_idx = {}
        self.movie_idx_to_id = {}

    def fit(self, movies_df: pd.DataFrame):
        self.movies_df = movies_df.copy()
        # Compute TF-IDF matrix
        self.tfidf_matrix = self.vectorizer.fit_transform(self.movies_df['metadata_text'])
        
        # Store index mappings
        self.movie_id_to_idx = {row['movieId']: idx for idx, row in self.movies_df.iterrows()}
        self.movie_idx_to_id = {idx: row['movieId'] for idx, row in self.movies_df.iterrows()}
        print(f"[ContentModel] Fitted TF-IDF matrix of shape {self.tfidf_matrix.shape}")

class HybridRecommender:
    """
    Hybrid Recommender System coordinating SVD and Content models.
    Supports user vector space profiling, dynamic novelty scaling, and greedy genre diversification.
    """
    def __init__(self, col_model: CollaborativeModel, content_model: ContentModel):
        self.col_model = col_model
        self.content_model = content_model

    def get_recommendations(self, 
                            user_id: int, 
                            movies_df: pd.DataFrame, 
                            ratings_df: pd.DataFrame, 
                            top_n: int = 10, 
                            weight_collaborative: float = 0.5, 
                            diversity_weight: float = 0.0, 
                            novelty_weight: float = 0.0, 
                            session_ratings: dict = None) -> pd.DataFrame:
        """
        Generates personalized, hybrid recommendations.
        """
        session_ratings = session_ratings or {}
        
        # 1. Identify candidate movies to recommend (exclude movies rated historically or in the active session)
        rated_movie_ids = set()
        if user_id in self.col_model.user_mapper:
            rated_movie_ids = set(ratings_df[ratings_df['userId'] == user_id]['movieId'].tolist())
        
        # Add session ratings to excluded set
        session_rated_ids = set(session_ratings.keys())
        excluded_ids = rated_movie_ids.union(session_rated_ids)
        
        # Filter candidate movies
        candidates_df = movies_df[~movies_df['movieId'].isin(excluded_ids)].copy()
        if len(candidates_df) == 0:
            return pd.DataFrame()
            
        # 2. Construct User Text Profile Vector in TF-IDF space
        n_features = self.content_model.tfidf_matrix.shape[1]
        u_text_vector = np.zeros((1, n_features))
        has_text_profile = False
        
        # Add historical ratings to text vector (only positive ratings, e.g. >= 3.0)
        if user_id in self.col_model.user_mapper:
            user_ratings = ratings_df[ratings_df['userId'] == user_id]
            for _, row in user_ratings.iterrows():
                mid = row['movieId']
                if mid in self.content_model.movie_id_to_idx:
                    m_idx = self.content_model.movie_id_to_idx[mid]
                    weight = row['rating'] - 3.0  # center around 3.0
                    if weight > 0:
                        u_text_vector += weight * self.content_model.tfidf_matrix[m_idx].toarray()
                        has_text_profile = True
                        
        # Add session ratings to text vector
        for mid, rating in session_ratings.items():
            if mid in self.content_model.movie_id_to_idx:
                m_idx = self.content_model.movie_id_to_idx[mid]
                weight = rating - 3.0
                if weight > 0:
                    u_text_vector += weight * self.content_model.tfidf_matrix[m_idx].toarray()
                    has_text_profile = True
                    
        # 3. Calculate Scores for Candidates
        candidate_ids = candidates_df['movieId'].values
        candidate_indices = [self.content_model.movie_id_to_idx[mid] for mid in candidate_ids]
        
        # Collaborative SVD Predictions (scaled to [0, 1] range)
        col_predictions = np.array([self.col_model.predict_rating(user_id, mid) for mid in candidate_ids])
        col_predictions_norm = (col_predictions - 0.5) / 4.5
        
        # Content NLP Similarity Scores
        if has_text_profile:
            u_vec_norm = np.linalg.norm(u_text_vector)
            if u_vec_norm > 0:
                u_text_vector = u_text_vector / u_vec_norm
            # Dot product with candidate rows
            candidate_tfidf = self.content_model.tfidf_matrix[candidate_indices].toarray()
            content_scores = np.dot(candidate_tfidf, u_text_vector.T).flatten()
        else:
            # True Cold-start with no preferences: default content similarity is zero
            content_scores = np.zeros(len(candidate_ids))
            
        # 4. Ensembled Hybrid Score
        # If user is completely new and has no session ratings, force Content-based (which will be 0)
        # to fall back to global popularity, meaning SVD weight is effectively ignored.
        is_new_user = user_id not in self.col_model.user_mapper
        active_weight = 0.0 if (is_new_user and not session_ratings) else weight_collaborative
        
        hybrid_scores = active_weight * col_predictions_norm + (1.0 - active_weight) * content_scores
        
        # 5. Apply Novelty Adjustments (penalize globally popular blockbusters)
        popularity = ratings_df.groupby('movieId').size()
        pop_min = popularity.min() if not popularity.empty else 1
        pop_max = popularity.max() if not popularity.empty else 100
        
        # Map popularity to candidates
        candidate_popularity = np.array([popularity.get(mid, 0) for mid in candidate_ids])
        candidate_popularity_norm = (candidate_popularity - pop_min) / (pop_max - pop_min + 1e-8)
        
        # Adjust hybrid scores based on novelty weight (scale down popular items)
        adjusted_scores = hybrid_scores * (1.0 - novelty_weight * candidate_popularity_norm)
        
        candidates_df['base_score'] = hybrid_scores
        candidates_df['col_prediction'] = col_predictions
        candidates_df['content_similarity'] = content_scores
        candidates_df['final_score'] = adjusted_scores
        candidates_df['popularity_hits'] = candidate_popularity
        
        # 6. Apply Greedy Genre Diversification Re-ranking
        if diversity_weight > 0.0:
            candidates_df = candidates_df.sort_values(by='final_score', ascending=False).reset_index(drop=True)
            selected_indices = []
            selected_genres = set()
            
            # Greedy selection loop
            while len(selected_indices) < min(top_n * 2, len(candidates_df)):
                best_idx = None
                best_score = -999.0
                
                # Check top remaining candidates (search window of 50 candidates)
                search_limit = min(50, len(candidates_df))
                for idx in range(search_limit):
                    if idx in selected_indices:
                        continue
                    
                    row = candidates_df.iloc[idx]
                    movie_genres = set(row['genres'].split('|'))
                    
                    # Calculate genre overlap with currently selected set
                    if selected_genres:
                        overlap = len(selected_genres.intersection(movie_genres))
                        # Penalty is proportional to overlap size
                        penalty = (overlap / len(movie_genres)) * diversity_weight
                    else:
                        penalty = 0.0
                        
                    score = row['final_score'] * (1.0 - penalty)
                    if score > best_score:
                        best_score = score
                        best_idx = idx
                        
                if best_idx is None:
                    break
                    
                selected_indices.append(best_idx)
                row_selected = candidates_df.iloc[best_idx]
                selected_genres.update(row_selected['genres'].split('|'))
                
            reordered_df = candidates_df.iloc[selected_indices].copy()
            # Append remaining candidates in original sorted order just in case
            remaining_indices = [i for i in range(len(candidates_df)) if i not in selected_indices]
            reordered_df = pd.concat([reordered_df, candidates_df.iloc[remaining_indices]])
            final_recs_df = reordered_df.head(top_n)
        else:
            final_recs_df = candidates_df.sort_values(by='final_score', ascending=False).head(top_n)
            
        return final_recs_df.reset_index(drop=True)

    def explain_recommendation(self, user_id: int, movie_id: int, ratings_df: pd.DataFrame, session_ratings: dict = None) -> dict:
        """
        Generates Explainable AI (XAI) insights explaining the recommendation.
        """
        session_ratings = session_ratings or {}
        movie_idx = self.content_model.movie_id_to_idx[movie_id]
        movie_row = self.content_model.movies_df.iloc[movie_idx]
        movie_genres = set(movie_row['genres'].split('|'))
        
        # 1. Collaborative Explanation (Latent Factor Proximity)
        col_explanation = None
        user_known = user_id in self.col_model.user_mapper
        
        # Retrieve movies this user has highly-rated (either historically or in session)
        user_likes = []
        if user_known:
            hist_likes = ratings_df[(ratings_df['userId'] == user_id) & (ratings_df['rating'] >= 4.0)]['movieId'].tolist()
            user_likes.extend(hist_likes)
        for mid, rating in session_ratings.items():
            if rating >= 4.0:
                user_likes.append(mid)
                
        user_likes = list(set(user_likes))
        
        if user_likes and movie_id in self.col_model.movie_mapper:
            # Find the movie vector in the SVD latent space (V^T matrix)
            m_svd_idx = self.col_model.movie_mapper[movie_id]
            m_latent = self.col_model.svd.components_[:, m_svd_idx]
            
            # Find the closest liked movie in the latent SVD space
            best_similarity = -1.0
            best_movie_id = None
            
            for liked_id in user_likes:
                if liked_id in self.col_model.movie_mapper:
                    liked_svd_idx = self.col_model.movie_mapper[liked_id]
                    liked_latent = self.col_model.svd.components_[:, liked_svd_idx]
                    
                    # Cosine similarity in latent space
                    denom = (np.linalg.norm(m_latent) * np.linalg.norm(liked_latent)) + 1e-8
                    sim = np.dot(m_latent, liked_latent) / denom
                    if sim > best_similarity:
                        best_similarity = sim
                        best_movie_id = liked_id
                        
            if best_movie_id:
                liked_title = self.content_model.movies_df[self.content_model.movies_df['movieId'] == best_movie_id]['title'].values[0]
                col_explanation = {
                    'liked_movie_title': liked_title,
                    'latent_similarity': best_similarity
                }
                
        # 2. Content Explanation (TF-IDF Vector Word Overlap)
        content_explanation = None
        
        # Aggregate user's liked text documents
        liked_indices = [self.content_model.movie_id_to_idx[mid] for mid in user_likes if mid in self.content_model.movie_id_to_idx]
        if liked_indices:
            # Aggregate TF-IDF vectors of liked movies
            user_tfidf = self.content_model.tfidf_matrix[liked_indices].mean(axis=0)
            movie_tfidf = self.content_model.tfidf_matrix[movie_idx].toarray().flatten()
            
            # Element-wise product shows which words contributed to similarity
            overlap = np.multiply(user_tfidf.A1, movie_tfidf)
            top_term_indices = np.argsort(overlap)[::-1][:3]
            
            feature_names = self.content_model.vectorizer.get_feature_names_out()
            overlapping_words = [feature_names[i] for i in top_term_indices if overlap[i] > 0]
            
            if overlapping_words:
                content_explanation = {
                    'overlapping_words': overlapping_words,
                    'matching_genres': list(movie_genres)
                }
                
        return {
            'collaborative': col_explanation,
            'content': content_explanation
        }
