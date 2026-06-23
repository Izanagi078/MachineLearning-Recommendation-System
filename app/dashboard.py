import sys
import os
import pickle
import requests
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import CollaborativeModel, ContentModel, HybridRecommender

# Set Page Config
st.set_page_config(
    page_title="🎬 Hybrid Recommendation & Cold-Start Resolution",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Glassmorphism CSS Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .main {
        background-color: #0d0e15;
        color: #e2e8f0;
    }
    
    .stSidebar {
        background-color: #12131e !important;
        border-right: 1px solid #1f2235;
    }
    
    /* Movie Card Wrapper */
    .movie-card {
        background: rgba(18, 19, 30, 0.65);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 12px;
        transition: transform 0.3s ease, border-color 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    .movie-card:hover {
        transform: translateY(-4px);
        border-color: rgba(129, 140, 248, 0.4);
    }
    
    /* Stat Metric Card */
    .stat-card {
        background: linear-gradient(135deg, rgba(20, 21, 38, 0.8) 0%, rgba(13, 14, 25, 0.8) 100%);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        transition: border-color 0.3s;
    }
    .stat-card:hover {
        border-color: rgba(99, 102, 241, 0.3);
    }
    .stat-title {
        font-size: 0.8rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 6px;
    }
    .stat-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #ffffff;
    }
    
    /* Explanations block */
    .explain-block {
        background: rgba(30, 41, 59, 0.4);
        border-left: 3px solid #6366f1;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 0.85rem;
        color: #cbd5e1;
        margin-top: 8px;
    }
    
    /* Button styles overrides */
    div.stButton > button:first-child {
        background-color: #6366f1;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 0.85rem;
    }
    div.stButton > button:first-child:hover {
        background-color: #4f46e5;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- Load Serialized Models & Cache -----------------
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')

@st.cache_resource
def load_models_and_data():
    """
    Loads saved models and cache from models/ directory.
    """
    col_path = os.path.join(MODELS_DIR, 'collaborative_model.pkl')
    content_path = os.path.join(MODELS_DIR, 'content_model.pkl')
    cache_path = os.path.join(MODELS_DIR, 'data_cache.pkl')
    
    try:
        with open(col_path, 'rb') as f:
            col_model = pickle.load(f)
        with open(content_path, 'rb') as f:
            content_model = pickle.load(f)
        with open(cache_path, 'rb') as f:
            cache = pickle.load(f)
        return col_model, content_model, cache
    except Exception as e:
        st.error(f"Failed to load cached models: {e}. Please run 'python -m src.train' first.")
        st.stop()

col_model, content_model, cache = load_models_and_data()
ratings_df = cache['ratings']
movies_df = cache['movies']
links_df = cache['links']
metrics = cache['metrics']

# Initialize Hybrid Recommender
hybrid_recommender = HybridRecommender(col_model, content_model)

# Initialize Session States for Dynamic Queue / Onboarding
if 'session_ratings' not in st.session_state:
    st.session_state.session_ratings = {}  # {movieId: rating}
if 'onboarding_genres' not in st.session_state:
    st.session_state.onboarding_genres = []
if 'last_selected_user' not in st.session_state:
    st.session_state.last_selected_user = None

# Title Section
st.title("🎬 Hybrid Recommendation Engine & Dynamic Onboarding")
st.markdown("An advanced **SVD + TF-IDF** Hybrid Movie Recommender solving **Cold-Start** and optimizing **Diversity vs. Novelty**.")

# ----------------- Sidebar Configurations -----------------
st.sidebar.header("⚙️ User & Profile Config")

# List unique user IDs for selection
unique_users = sorted(ratings_df['userId'].unique().tolist())
user_options = ["New User (Cold-Start)"] + [f"User {uid}" for uid in unique_users[:50]] # Limit to first 50 users for cleaner UI
selected_user_str = st.sidebar.selectbox("Select User Profile", user_options)

# Extract user ID
if selected_user_str == "New User (Cold-Start)":
    user_id = -1
else:
    user_id = int(selected_user_str.split(" ")[1])

# Reset session state if the selected user changes
if user_id != st.session_state.last_selected_user:
    st.session_state.session_ratings = {}
    st.session_state.last_selected_user = user_id

# Model Strategy parameters
st.sidebar.subheader("🎛️ Hybrid Parameters")
col_weight = st.sidebar.slider("Collaborative SVD Weight", min_value=0.0, max_value=1.0, value=0.5, step=0.05,
                               help="Weights Collaborative predictions vs. Content textual similarity scores.")

st.sidebar.subheader("🌟 Discovery Mode")
novelty_weight = st.sidebar.slider("Novelty (Hidden Gems) Bias", min_value=0.0, max_value=1.0, value=0.0, step=0.05,
                                  help="Increases penalty on globally popular movies to highlight hidden gems.")
diversity_weight = st.sidebar.slider("Genre Diversity Bias", min_value=0.0, max_value=1.0, value=0.2, step=0.05,
                                    help="Uses a Greedy Re-ranking penalty to distribute recommendations across different genres.")

# Optional API Key for Real Posters
st.sidebar.subheader("🖼️ Media Poster Lookup")
tmdb_api_key = st.sidebar.text_input("TMDB API Key (Optional)", type="password", 
                                     help="Enter a free TMDB API key to render real movie poster images.")

# Display clear cache button
if st.sidebar.button("Clear Session Queue 🔄"):
    st.session_state.session_ratings = {}
    st.success("Session rating history cleared!")
    st.rerun()

# ----------------- Main Metrics Header -----------------
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-title">SVD Accuracy (RMSE)</div>
        <div class="stat-value">{metrics['rmse']:.4f}</div>
    </div>
    """, unsafe_allow_html=True)
with m2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-title">Hybrid Rank Quality (NDCG@10)</div>
        <div class="stat-value">{metrics['ndcg_10']*100:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)
with m3:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-title">Mean Average Precision (MAP@10)</div>
        <div class="stat-value">{metrics['map_10']*100:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)
with m4:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-title">Dataset Size (Ratings)</div>
        <div class="stat-value">{len(ratings_df):,}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ----------------- TMDB Poster Helper -----------------
def get_movie_poster_url(movie_id: int, api_key: str = None) -> str:
    """
    Fetches the poster URL for a movie from TMDB if an API key is provided.
    Otherwise returns None to fall back to the CSS card.
    """
    if not api_key:
        return None
    try:
        # Get tmdbId from links
        links = links_df[links_df['movieId'] == movie_id]
        if links.empty:
            return None
        tmdb_id = links['tmdbId'].values[0]
        if pd.isna(tmdb_id):
            return None
            
        url = f"https://api.themoviedb.org/3/movie/{int(tmdb_id)}?api_key={api_key}"
        res = requests.get(url, timeout=2.0)
        if res.status_code == 200:
            data = res.json()
            poster_path = data.get('poster_path')
            if poster_path:
                return f"https://image.tmdb.org/t/p/w500{poster_path}"
    except Exception:
        pass
    return None

def render_movie_fallback_card(title: str, genres: str, movie_id: int):
    """
    Generates a beautiful CSS fallback card when TMDB poster is unavailable.
    """
    # Extract year from title if present
    import re
    year_match = re.search(r'\((\d{4})\)', title)
    year = year_match.group(1) if year_match else "N/A"
    clean_title = re.sub(r'\s*\(\d{4}\)', '', title)
    
    genres_list = genres.split('|')
    primary_genre = genres_list[0] if genres_list else "General"
    
    # Select gradient based on movie_id to make cards look diverse
    gradients = [
        "linear-gradient(135deg, #1e1b4b 0%, #311042 100%)",
        "linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%)",
        "linear-gradient(135deg, #311042 0%, #581c87 100%)",
        "linear-gradient(135deg, #022c22 0%, #064e3b 100%)",
        "linear-gradient(135deg, #450a0a 0%, #1e1b4b 100%)"
    ]
    grad = gradients[movie_id % len(gradients)]
    
    card_html = f"""
    <div style="
      background: {grad};
      width: 100%;
      height: 250px;
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 16px;
      color: white;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      border: 1px solid rgba(255, 255, 255, 0.05);
    ">
      <div style="font-size: 11px; text-transform: uppercase; color: #a5b4fc; letter-spacing: 1px; font-weight: 600;">{primary_genre}</div>
      <div style="font-size: 15px; font-weight: bold; line-height: 1.25; max-height: 100px; overflow: hidden; margin-top: 10px;">{clean_title}</div>
      <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; font-size: 11px; color: #cbd5e1; margin-top: auto;">
        <span>ID: {movie_id}</span>
        <span style="background: rgba(255, 255, 255, 0.15); padding: 2px 6px; border-radius: 4px;">{year}</span>
      </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

# ----------------- Streamlit Main Area Tabs -----------------
tab_recs, tab_analysis = st.tabs(["💡 Recommendations Shelf", "📊 Algorithmic Diagnostics"])

with tab_recs:
    # ----------------- COLD-START INTERACTIVE ONBOARDING -----------------
    if user_id == -1 and not st.session_state.session_ratings:
        st.subheader("👋 Welcome, New User!")
        st.write("Since you are a new user, the system is in **Cold-Start mode** (Matrix Factorization SVD has no rating history for you).")
        st.write("To bootstrap your recommendation vector, please share your preferences below:")
        
        # 1. Onboarding Preferences Form
        st.markdown("<div class='movie-card'>", unsafe_allow_html=True)
        col_on1, col_on2 = st.columns(2)
        
        with col_on1:
            # Extract unique genres from movies_df
            all_genres = set()
            for gs in movies_df['genres'].dropna():
                all_genres.update(gs.split('|'))
            all_genres = sorted(list(all_genres))
            if "(no genres listed)" in all_genres:
                all_genres.remove("(no genres listed)")
                
            onboard_genres = st.multiselect("Select genres you enjoy:", all_genres, key="onb_genres_select")
            
        with col_on2:
            onboard_keywords = st.text_input("Or enter plot keywords/topics:", placeholder="e.g., space, time travel, magic, hacking")
            
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Trigger button
        if st.button("Generate Recommendations 🚀"):
            # Construct session ratings mock to kick off the TF-IDF cosine engine
            mock_session = {}
            
            # Combine genres and keywords to search
            search_query = " ".join(onboard_genres) + " " + onboard_keywords
            search_query = search_query.strip().lower()
            
            if search_query:
                # Find matching movies via TF-IDF matrix similarity
                query_vector = content_model.vectorizer.transform([search_query])
                
                # Cosine similarity against all movies
                sims = np.dot(content_model.tfidf_matrix.toarray(), query_vector.toarray().T).flatten()
                top_matching_indices = np.argsort(sims)[::-1][:5]
                
                # Mock rating these top matching movies as 5.0 (liked) in session ratings
                for idx in top_matching_indices:
                    mid = content_model.movie_idx_to_id[idx]
                    mock_session[mid] = 5.0
                    
                st.session_state.session_ratings = mock_session
                st.success("Preferences saved! Fetching recommendations...")
                st.rerun()
            else:
                st.warning("Please select at least one genre or enter keywords.")
                
        # Return popular movies as default fallback before onboarding completes
        st.subheader("🔥 Popular Movies Right Now")
        popular_ids = ratings_df.groupby('movieId').size().sort_values(ascending=False).head(5).index.tolist()
        pop_movies = movies_df[movies_df['movieId'].isin(popular_ids)]
        
        cols = st.columns(5)
        for i, (_, row) in enumerate(pop_movies.iterrows()):
            with cols[i]:
                poster_url = get_movie_poster_url(row['movieId'], tmdb_api_key)
                if poster_url:
                    st.image(poster_url, use_container_width=True)
                else:
                    render_movie_fallback_card(row['title'], row['genres'], row['movieId'])
                    
                st.markdown(f"**{row['title']}**")
                st.write(f"Genres: `{row['genres'].replace('|', ', ')}`")
                if st.button("Like 👍", key=f"pop_like_{row['movieId']}"):
                    st.session_state.session_ratings[row['movieId']] = 5.0
                    st.success(f"Liked {row['title']}!")
                    st.rerun()

    else:
        # User is either established OR has onboarding session ratings
        # 1. Heading details
        if user_id == -1:
            st.subheader("💡 Dynamic Cold-Start Recommendations")
            st.info(f"Active session profile contains `{len(st.session_state.session_ratings)}` rated items.")
        else:
            st.subheader(f"💡 Recommended for User {user_id}")
            
            # Show historical stats for this user
            user_ratings = ratings_df[ratings_df['userId'] == user_id]
            st.write(f"This user has rated `{len(user_ratings)}` movies historically. (Average rating: `{user_ratings['rating'].mean():.2f}` stars)")
            
        # 2. Get recommendations
        with st.spinner("Fetching hybrid recommendations..."):
            recs_df = hybrid_recommender.get_recommendations(
                user_id=user_id,
                movies_df=movies_df,
                ratings_df=ratings_df,
                top_n=10,
                weight_collaborative=col_weight,
                diversity_weight=diversity_weight,
                novelty_weight=novelty_weight,
                session_ratings=st.session_state.session_ratings
            )
            
        if recs_df.empty:
            st.warning("No candidate recommendations found.")
        else:
            # Display recommendations in 2 rows of 5
            row1_cols = st.columns(5)
            row2_cols = st.columns(5)
            
            for i, (_, row) in enumerate(recs_df.iterrows()):
                col = row1_cols[i] if i < 5 else row2_cols[i - 5]
                
                with col:
                    # Poster Image rendering
                    poster_url = get_movie_poster_url(row['movieId'], tmdb_api_key)
                    
                    st.markdown("<div class='movie-card'>", unsafe_allow_html=True)
                    if poster_url:
                        st.image(poster_url, use_container_width=True)
                    else:
                        render_movie_fallback_card(row['title'], row['genres'], row['movieId'])
                        
                    # Title & Score
                    st.markdown(f"##### {row['title']}")
                    st.write(f"Genres: `{row['genres'].replace('|', ', ')}`")
                    
                    # Display metrics
                    score_col, pop_col = st.columns(2)
                    with score_col:
                        st.markdown(f"**Score**: `{row['final_score']:.2f}`")
                    with pop_col:
                        st.markdown(f"**Popularity**: `{int(row['popularity_hits'])}`")
                        
                    # Feedback queue buttons
                    like_col, dislike_col = st.columns(2)
                    with like_col:
                        if st.button("Like 👍", key=f"like_{row['movieId']}"):
                            st.session_state.session_ratings[row['movieId']] = 5.0
                            st.success(f"Added to Queue!")
                            st.rerun()
                    with dislike_col:
                        if st.button("Dislike 👎", key=f"dislike_{row['movieId']}"):
                            st.session_state.session_ratings[row['movieId']] = 1.0
                            st.success(f"Added to Queue!")
                            st.rerun()
                            
                    # XAI Explanation Panel
                    with st.expander("🔎 Why Recommended?"):
                        explanation = hybrid_recommender.explain_recommendation(
                            user_id=user_id,
                            movie_id=row['movieId'],
                            ratings_df=ratings_df,
                            session_ratings=st.session_state.session_ratings
                        )
                        
                        # Render explanation details
                        explained = False
                        if explanation['collaborative']:
                            col_ex = explanation['collaborative']
                            st.markdown(f"""
                            <div class="explain-block">
                                <b>Collaborative Connection</b>:<br>
                                Fits your interest pattern matching <b>{col_ex['liked_movie_title']}</b> 
                                (Latent space similarity: <code>{col_ex['latent_similarity']:.2f}</code>).
                            </div>
                            """, unsafe_allow_html=True)
                            explained = True
                            
                        if explanation['content']:
                            con_ex = explanation['content']
                            words_str = ", ".join([f"'{w}'" for w in con_ex['overlapping_words']])
                            st.markdown(f"""
                            <div class="explain-block">
                                <b>Content Connection</b>:<br>
                                Shares keywords: {words_str}.<br>
                                Matching Genres: <code>{', '.join(con_ex['matching_genres'])}</code>.
                            </div>
                            """, unsafe_allow_html=True)
                            explained = True
                            
                        if not explained:
                            st.write("Recommended as a general matching popular item in your preferred categories.")
                            
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.write("")

        # 3. Display current session queue status in footer
        if st.session_state.session_ratings:
            st.write("---")
            st.subheader("🔄 Active Session Queue Feed")
            
            feed_items = []
            for mid, rating in st.session_state.session_ratings.items():
                m_title = movies_df[movies_df['movieId'] == mid]['title'].values[0]
                status = "Like 👍" if rating == 5.0 else "Dislike 👎"
                feed_items.append(f"**{m_title}** ({status})")
                
            st.write(", ".join(feed_items))

with tab_analysis:
    st.subheader("📊 Algorithmic Diagnostics & Model Latent Space")
    
    # 1. Project genre preferences of selected user (established)
    if user_id != -1:
        st.write(f"Analyzed profile preferences for User {user_id} based on rating history:")
        user_ratings_all = ratings_df[ratings_df['userId'] == user_id].merge(movies_df, on='movieId')
        
        # Count rated genres
        user_genres = []
        for gs in user_ratings_all['genres']:
            user_genres.extend(gs.split('|'))
            
        genre_counts = pd.Series(user_genres).value_counts().reset_index()
        genre_counts.columns = ['Genre', 'Count']
        
        # Plotting genre preference counts
        fig_genres = px.bar(
            genre_counts, 
            x='Genre', 
            y='Count', 
            title=f"User {user_id} Historical Rating Count by Genre",
            color='Count',
            template='plotly_dark'
        )
        fig_genres.update_layout(plot_bgcolor="#12131e", paper_bgcolor="#0d0e15")
        st.plotly_chart(fig_genres, use_container_width=True)
        
    else:
        st.write("Onboarding user profiles have no historical rating distributions yet.")

    # 2. SVD Explained Variance plot
    st.write("---")
    st.subheader("📈 SVD Explained Variance Ratio")
    st.write("Dimensionality reduction performance of TruncatedSVD on the rating pivot table:")
    
    var_exp = col_model.svd.explained_variance_ratio_
    cum_var = np.cumsum(var_exp)
    
    fig_variance = go.Figure()
    fig_variance.add_trace(go.Scatter(y=var_exp, name="Individual Explained Variance", mode="lines+markers", line=dict(color="#6366f1", width=2)))
    fig_variance.add_trace(go.Scatter(y=cum_var, name="Cumulative Explained Variance", mode="lines+markers", line=dict(color="#10b981", width=2)))
    
    fig_variance.update_layout(
        template="plotly_dark",
        plot_bgcolor="#12131e",
        paper_bgcolor="#0d0e15",
        title="SVD Latent Factors Explained Variance Ratio",
        xaxis_title="Latent Component Index",
        yaxis_title="Explained Variance Ratio",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_variance, use_container_width=True)

    # 3. Display general info
    st.write("---")
    st.subheader("💡 System Summary & Hyperparameters")
    st.write(f"**Total Ratings Database Size**: `{ratings_df.shape[0]:,}` transactions")
    st.write(f"**User Count**: `{ratings_df['userId'].nunique()}` unique users")
    st.write(f"**Movie Count**: `{movies_df['movieId'].nunique()}` unique movies")
    st.write(f"**SVD Latent Dimension ($K$)**: `{col_model.n_factors}` components")
    st.write(f"**TF-IDF Feature Count**: `{content_model.tfidf_matrix.shape[1]:,}` words")
