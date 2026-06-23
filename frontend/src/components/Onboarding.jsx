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
          userId: currentUserId || null  // pass existing account ID if logged in
        })
      });

      if (response.ok) {
        const data = await response.json();
        // Return matching user data: userId
        onSubmit(data.userId);
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
          type="text"
          placeholder="e.g., time travel, space exploration, superheros, serial killer"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
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
