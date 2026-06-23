import os
import zipfile
import urllib.request
import pandas as pd
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
ZIP_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
ZIP_PATH = os.path.join(DATA_DIR, "ml-latest-small.zip")
EXTRACT_DIR = os.path.join(DATA_DIR, "ml-latest-small")

def download_and_extract_data():
    """
    Downloads and extracts the MovieLens-Latest-Small dataset if not already present.
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    # Check if files already exist
    required_files = ['ratings.csv', 'movies.csv', 'tags.csv', 'links.csv']
    all_exist = all(os.path.exists(os.path.join(EXTRACT_DIR, f)) for f in required_files)
    
    if all_exist:
        print("[data_loader] Dataset already exists locally. Skipping download.")
        return

    print(f"[data_loader] Downloading MovieLens dataset from {ZIP_URL}...")
    try:
        # Standard urllib request with a User-Agent header to prevent 403 Forbidden errors
        req = urllib.request.Request(
            ZIP_URL, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response, open(ZIP_PATH, 'wb') as out_file:
            out_file.write(response.read())
            
        print("[data_loader] Extracting zip file...")
        with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
            # The zip file contains a directory 'ml-latest-small/', so extracting to DATA_DIR creates EXTRACT_DIR
            zip_ref.extractall(DATA_DIR)
            
        # Clean up zip file
        os.remove(ZIP_PATH)
        print("[data_loader] Dataset download and extraction completed successfully.")
    except Exception as e:
        print(f"[data_loader] Error downloading/extracting dataset: {e}")
        raise e

def load_recommender_data() -> tuple:
    """
    Downloads data if necessary, loads CSVs, builds movie content text documents.
    Returns:
        ratings_df: DataFrame of columns [userId, movieId, rating, timestamp]
        movies_df: DataFrame of columns [movieId, title, genres, genres_clean, tags_text, metadata_text]
        links_df: DataFrame of columns [movieId, imdbId, tmdbId]
    """
    download_and_extract_data()
    
    ratings_df = pd.read_csv(os.path.join(EXTRACT_DIR, 'ratings.csv'))
    movies_df = pd.read_csv(os.path.join(EXTRACT_DIR, 'movies.csv'))
    tags_df = pd.read_csv(os.path.join(EXTRACT_DIR, 'tags.csv'))
    links_df = pd.read_csv(os.path.join(EXTRACT_DIR, 'links.csv'))
    
    # 1. Clean genres (replace pipe '|' with space for NLP tokenization)
    movies_df['genres_clean'] = movies_df['genres'].str.replace('|', ' ', regex=False)
    # Handle '(no genres listed)' case
    movies_df['genres_clean'] = movies_df['genres_clean'].str.replace('(no genres listed)', '', regex=False)
    
    # 2. Group and aggregate tags per movie
    # Fill NaN tags with empty space
    tags_df['tag'] = tags_df['tag'].fillna('').astype(str)
    # Group tags by movieId and join with spaces
    tags_grouped = tags_df.groupby('movieId')['tag'].apply(lambda x: ' '.join(x)).reset_index()
    tags_grouped.rename(columns={'tag': 'tags_text'}, inplace=True)
    
    # 3. Merge tags into movies
    movies_df = movies_df.merge(tags_grouped, on='movieId', how='left')
    movies_df['tags_text'] = movies_df['tags_text'].fillna('')
    
    # 4. Construct content document corpus column: Title + clean genres + user tags
    movies_df['metadata_text'] = (
        movies_df['title'] + " " + 
        movies_df['genres_clean'] + " " + 
        movies_df['tags_text']
    )
    
    # Simple NLP normalization: lowercase and remove redundant whitespaces
    movies_df['metadata_text'] = movies_df['metadata_text'].str.lower().str.replace(r'\s+', ' ', regex=True).str.strip()
    
    print(f"[data_loader] Loaded {len(ratings_df)} ratings, {len(movies_df)} movies.")
    return ratings_df, movies_df, links_df

if __name__ == "__main__":
    r, m, l = load_recommender_data()
    print("Sample Metadata Text for Movie 1:")
    print(m.iloc[0]['metadata_text'])
