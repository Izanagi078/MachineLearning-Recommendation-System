import React, { useState } from 'react';

const AVAILABLE_GENRES = [
  'Action', 'Adventure', 'Animation', 'Children', 'Comedy', 'Crime',
  'Documentary', 'Drama', 'Fantasy', 'Horror', 'Mystery', 'Romance',
  'Sci-Fi', 'Thriller', 'Western'
];

export default function Onboarding({ onSubmit, currentUserId }) {
  const [selectedGenres, setSelectedGenres] = useState([]);
  const [keywords, setKeywords] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [matchedMovies, setMatchedMovies] = useState(null); // confirmation step

  const toggleGenre = (genre) => {
    if (selectedGenres.includes(genre)) {
      setSelectedGenres(selectedGenres.filter((g) => g !== genre));
    } else {
      setSelectedGenres([...selectedGenres, genre]);
    }
  };

  const handleGenerate = async () => {
    if (selectedGenres.length === 0 && !keywords.trim()) {
      setErrorMsg('Please select at least one genre or enter search keywords.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg('');

    try {
      const response = await fetch('http://127.0.0.1:8000/api/onboarding', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          genres: selectedGenres,
          keywords: keywords.trim(),
          userId: currentUserId || null
        })
      });

      if (response.ok) {
        const data = await response.json();
        // Show confirmation screen with matched movies before transitioning
        setMatchedMovies({ userId: data.userId, movies: data.matched_movies || [] });
      } else {
        const errData = await response.json();
        setErrorMsg(`Failed: ${errData.detail || 'Network error'}`);
      }
    } catch (err) {
      setErrorMsg('Failed to connect to recommendation backend.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // ── Confirmation screen ─────────────────────────────────────────────────
  if (matchedMovies) {
    return (
      <div className="glass-card" style={{ padding: '24px 28px', maxWidth: '600px', width: '100%' }}>
        {/* Compact header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
          <span style={{ fontSize: '1.8rem' }}>✅</span>
          <div>
            <h2 style={{ fontSize: '1.1rem', marginBottom: '2px' }}>Profile Bootstrapped!</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', margin: 0 }}>
              Genres: <strong style={{ color: 'var(--accent-indigo)' }}>{selectedGenres.join(', ') || '—'}</strong>
              {keywords && <> · <em>"{keywords}"</em></>}
            </p>
          </div>
        </div>

        {/* Seeded movies — compact rows */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '7px', marginBottom: '16px' }}>
          {matchedMovies.movies.length === 0 && (
            <p style={{ color: 'var(--text-secondary)', textAlign: 'center', fontSize: '0.82rem' }}>
              No exact matches — SVD will still personalize from the model.
            </p>
          )}
          {matchedMovies.movies.map((m) => (
            <div key={m.movieId} style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '8px 12px',
              borderRadius: '7px',
              background: 'rgba(99,102,241,0.08)',
              border: '1px solid rgba(99,102,241,0.18)'
            }}>
              <div style={{ minWidth: 0 }}>
                <span style={{ fontWeight: '600', fontSize: '0.85rem' }}>{m.title}</span>
                {m.genres && (
                  <span style={{ marginLeft: '8px', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                    {m.genres}
                  </span>
                )}
              </div>
              <span style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)', fontWeight: 'bold', whiteSpace: 'nowrap', marginLeft: '8px' }}>
                ⭐ Seeded
              </span>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            Session: <code style={{ color: 'var(--accent-indigo)' }}>{matchedMovies.userId}</code>
          </span>
          <button
            className="btn-primary"
            style={{ padding: '10px 20px', fontSize: '0.9rem', whiteSpace: 'nowrap' }}
            onClick={() => onSubmit(matchedMovies.userId)}
          >
            View My Recommendations →
          </button>
        </div>
      </div>
    );
  }

  // ── Selection screen ────────────────────────────────────────────────────
  return (
    <div className="onboarding-container glass-card" style={{ padding: '36px', maxWidth: '550px' }}>
      <div style={{ textAlign: 'center', marginBottom: '12px' }}>
        <h1 style={{ fontSize: '1.8rem', marginBottom: '8px' }}>👋 Dynamic Cold-Start Bootstrap</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Matrix Factorization needs a few ratings to build your collaborative profile. Let's seed it instantly using content similarities:
        </p>
      </div>

      <div style={{ width: '100%' }}>
        <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '10px' }}>
          Select Genres you enjoy:
        </h4>
        <div className="genre-grid">
          {AVAILABLE_GENRES.map((g) => {
            const isActive = selectedGenres.includes(g);
            return (
              <div
                key={g}
                className={`genre-chip ${isActive ? 'active' : ''}`}
                onClick={() => toggleGenre(g)}
              >
                {g}
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
          Plot Keywords or Themes (Optional):
        </h4>
        <input
          id="onboarding-keywords"
          name="keywords"
          type="text"
          placeholder="e.g., time travel, space exploration, superheros, serial killer"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
          style={{
            width: '100%',
            padding: '12px',
            borderRadius: '8px',
            border: '1px solid var(--border-color)',
            background: 'rgba(0,0,0,0.3)',
            color: 'white',
            fontFamily: 'var(--font-family)',
            outline: 'none',
            fontSize: '0.9rem'
          }}
        />
      </div>

      {/* Selected genre summary */}
      {selectedGenres.length > 0 && (
        <div style={{ fontSize: '0.8rem', color: 'var(--accent-indigo)', textAlign: 'center' }}>
          Selected: {selectedGenres.join(' · ')}
        </div>
      )}

      {errorMsg && (
        <p style={{ color: 'var(--accent-rose)', fontSize: '0.8rem', textAlign: 'center' }}>{errorMsg}</p>
      )}

      <button
        className="btn-primary"
        style={{ width: '100%', padding: '14px', fontSize: '1rem' }}
        onClick={handleGenerate}
        disabled={isSubmitting}
      >
        {isSubmitting ? 'Personalizing Catalog...' : 'Build SVD Latent Profile 🚀'}
      </button>
    </div>
  );
}
