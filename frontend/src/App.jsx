import React, { useState, useEffect } from 'react';
import SidebarSettings from './components/SidebarSettings';
import LiveFeed from './components/LiveFeed';
import Onboarding from './components/Onboarding';
import MovieShelf from './components/MovieShelf';
import VisualCharts from './components/VisualCharts';
import LoginModal from './components/LoginModal';

export default function App() {
  const [userId, setUserId] = useState(() => localStorage.getItem('userId') || '');
  const [sessionRatings, setSessionRatings] = useState({});
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  
  // Recommendations and Shelves
  const [recommendations, setRecommendations] = useState([]);
  const [popularMovies, setPopularMovies] = useState([]);
  const [feed, setFeed] = useState([]);
  const [stats, setStats] = useState(null);

  // Filter params
  const [weightCol, setWeightCol] = useState(0.5);
  const [novelty, setNovelty] = useState(0.0);
  const [diversity, setDiversity] = useState(0.2);

  // Search
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);

  // States
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // 1. Initial page load data
  useEffect(() => {
    fetchStats();
    fetchPopular();
    fetchFeed();
    
    // Poll the feed and stats every 5 seconds for real-time multiplayer updates
    const interval = setInterval(() => {
      fetchFeed();
      fetchStats();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // 2. Fetch recommendations whenever userId or parameters adjust
  useEffect(() => {
    if (userId) {
      fetchRecommendations();
    }
  }, [userId, weightCol, novelty, diversity]);

  // 3. Search query lookup
  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      handleSearch();
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery]);

  // API Call Helpers
  const fetchStats = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error('Failed to load stats', e);
    }
  };

  const fetchPopular = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/movies/popular?limit=5');
      if (res.ok) {
        const data = await res.json();
        setPopularMovies(data);
      }
    } catch (e) {
      console.error('Failed to load popular movies', e);
    }
  };

  const fetchFeed = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/feed?limit=8');
      if (res.ok) {
        const data = await res.json();
        setFeed(data);
      }
    } catch (e) {
      console.error('Failed to load activity feed', e);
    }
  };

  const fetchRecommendations = async () => {
    setIsLoading(true);
    setErrorMsg('');
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/api/recommendations?userId=${userId}&weight_collaborative=${weightCol}&novelty_weight=${novelty}&diversity_weight=${diversity}&top_n=10`
      );
      if (res.ok) {
        const data = await res.json();
        setRecommendations(data);
      } else {
        setErrorMsg('Failed to load personalized recommendations.');
      }
    } catch (e) {
      setErrorMsg('Cannot connect to API server.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/movies/search?query=${encodeURIComponent(searchQuery)}&limit=5`);
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data);
      }
    } catch (e) {
      console.error('Search failed', e);
    }
  };

  // Interactions
  const handleRateMovie = async (movieId, rating) => {
    if (!userId) return;

    try {
      const res = await fetch('http://127.0.0.1:8000/api/ratings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId, movieId, rating })
      });

      if (res.ok) {
        // Record rating locally
        setSessionRatings((prev) => ({
          ...prev,
          [movieId]: rating
        }));

        // Refresh recommendations, stats, and feed
        fetchRecommendations();
        fetchStats();
        fetchFeed();
      }
    } catch (e) {
      console.error('Rating submission failed', e);
    }
  };

  const handleDeleteMovie = async (movieId) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/movies/${movieId}`, {
        method: 'DELETE'
      });

      if (res.ok) {
        // Clear search or reset shelves
        setSearchResults((prev) => prev.filter((m) => m.movieId !== movieId));
        setPopularMovies((prev) => prev.filter((m) => m.movieId !== movieId));
        setRecommendations((prev) => prev.filter((m) => m.movieId !== movieId));
        fetchStats();
        if (userId) fetchRecommendations();
      }
    } catch (e) {
      console.error('Archiving movie failed', e);
    }
  };

  const handleResetSession = () => {
    localStorage.removeItem('userId');
    setUserId('');
    setSessionRatings({});
    setRecommendations([]);
    setSearchResults([]);
    setSearchQuery('');
  };

  const handleOnboardingSubmit = (newUserId) => {
    localStorage.setItem('userId', newUserId);
    setUserId(newUserId);
    setSessionRatings({}); // reset rating indicators for new guest session
  };

  // Refresh catalogs
  const refreshCatalog = () => {
    fetchPopular();
    fetchStats();
    if (userId) fetchRecommendations();
  };

  const handleLogin = async (username) => {
    localStorage.setItem('userId', username);
    setUserId(username);
    setSessionRatings({});
    
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/users/${username}/ratings`);
      if (res.ok) {
        const data = await res.json();
        setSessionRatings(data);
      }
    } catch (e) {
      console.error("Failed to load user ratings", e);
    }
  };

  return (
    <div className="app-container">
      {/* Heavenly background glowing blobs */}
      <div className="glow-orb glow-orb-1"></div>
      <div className="glow-orb glow-orb-2"></div>
      
      {/* Sidebar 1: Sliders, Session details, and Admin Add Movie */}
      <SidebarSettings
        weightCol={weightCol}
        setWeightCol={setWeightCol}
        novelty={novelty}
        setNovelty={setNovelty}
        diversity={diversity}
        setDiversity={setDiversity}
        userId={userId}
        onReset={handleResetSession}
        onAddMovieSuccess={refreshCatalog}
      />

      {/* Sidebar 2: Live Multiplayer Ratings Log Stream */}
      <LiveFeed feed={feed} />

      {/* Main recommendation shelf space */}
      <main className="main-content">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px' }}>
          <div>
            <h1>🎬 Personal Recommendations Portal</h1>
            <p style={{ color: 'var(--text-secondary)' }}>
              Real-time SVD matrix factorizer & content keyword TF-IDF ensembled engine.
            </p>
          </div>
          <button 
            className="btn-primary" 
            style={{ 
              background: userId ? '#25283c' : 'linear-gradient(135deg, var(--accent-indigo) 0%, #4338ca 100%)', 
              fontSize: '0.85rem', 
              padding: '10px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
            onClick={() => userId ? handleResetSession() : setIsLoginModalOpen(true)}
          >
            {userId ? `Sign Out (${userId}) 🚪` : 'Sign In / Register 🔑'}
          </button>
        </div>

        {/* Determine if onboarding is required for cold start */}
        {!userId || (!userId.startsWith('User ') && Object.keys(sessionRatings).length === 0) ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', marginTop: '20px' }}>
            {!userId && (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', maxWidth: '500px', fontSize: '0.85rem' }}>
                Browse as a guest by filling out preferences below, or click <strong>Sign In</strong> in the top corner to load a demo or custom user profile.
              </p>
            )}
            {userId && (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', maxWidth: '500px', fontSize: '0.85rem' }}>
                Welcome, <strong>{userId}</strong>! Since you are a new user, please choose your interests to bootstrap your SVD latent vector.
              </p>
            )}
            <Onboarding onSubmit={handleOnboardingSubmit} />
          </div>
        ) : (
          <>
            {/* Header statistics banner */}
            {stats && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px' }}>
                <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '14px' }}>
                  <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>RMSE (Accuracy)</span>
                  <span style={{ fontSize: '1.4rem', fontWeight: 'bold', color: 'var(--accent-emerald)', marginTop: '4px' }}>
                    {stats.metrics.rmse.toFixed(4)}
                  </span>
                </div>
                <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '14px' }}>
                  <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>NDCG@10 Rank</span>
                  <span style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#ffffff', marginTop: '4px' }}>
                    {(stats.metrics.ndcg_10 * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '14px' }}>
                  <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>MAP@10 Precision</span>
                  <span style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#ffffff', marginTop: '4px' }}>
                    {(stats.metrics.map_10 * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '14px' }}>
                  <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Model Users (SVD)</span>
                  <span style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#ffffff', marginTop: '4px' }}>
                    {stats.users_count}
                  </span>
                </div>
              </div>
            )}

            {/* Movie Catalog Search Panel */}
            <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <h3 style={{ fontSize: '0.85rem' }}>🔍 Search Catalog & Rate</h3>
              <input
                type="text"
                placeholder="Search movies to rate and instantly influence SVD vectors..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  background: 'rgba(0,0,0,0.2)',
                  color: 'white',
                  outline: 'none',
                  fontFamily: 'var(--font-family)'
                }}
              />
              {searchResults.length > 0 && (
                <div style={{ marginTop: '10px' }}>
                  <MovieShelf
                    title="Search Results"
                    movies={searchResults}
                    onRate={handleRateMovie}
                    onDelete={handleDeleteMovie}
                    sessionRatings={sessionRatings}
                  />
                </div>
              )}
            </div>

            {/* Recommendations Shelf */}
            {isLoading ? (
              <div className="glass-card" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                Re-indexing user latent matrix coordinates...
              </div>
            ) : errorMsg ? (
              <div className="glass-card" style={{ padding: '24px', textAlign: 'center', color: 'var(--accent-rose)' }}>
                {errorMsg}
              </div>
            ) : (
              <MovieShelf
                title="💡 Recommended For You"
                movies={recommendations}
                onRate={handleRateMovie}
                onDelete={handleDeleteMovie}
                sessionRatings={sessionRatings}
              />
            )}

            {/* General Popular Shelf */}
            <MovieShelf
              title="🔥 Popular Right Now"
              movies={popularMovies}
              onRate={handleRateMovie}
              onDelete={handleDeleteMovie}
              sessionRatings={sessionRatings}
            />

            {/* SVD explained variance and coordinates diagnostics */}
            {stats && <VisualCharts stats={stats} />}
          </>
        )}
      </main>

      {/* Glassmorphic Auth Portal Modal Overlay */}
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onLogin={handleLogin}
      />
    </div>
  );
}
