import React, { useState } from 'react';

export default function SidebarSettings({
  weightCol,
  setWeightCol,
  novelty,
  setNovelty,
  diversity,
  setDiversity,
  userId,
  onReset,
  onAddMovieSuccess
}) {
  const [title, setTitle] = useState('');
  const [genres, setGenres] = useState('');
  const [isAdminOpen, setIsAdminOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  const handleAddMovie = async (e) => {
    e.preventDefault();
    if (!title.trim() || !genres.trim()) {
      setStatusMsg('Please enter both title and genres.');
      return;
    }

    setIsSubmitting(true);
    setStatusMsg('');

    try {
      const response = await fetch('http://127.0.0.1:8000/api/movies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, genres })
      });

      if (response.ok) {
        const data = await response.json();
        setStatusMsg(`Successfully added "${data.title}" (ID: ${data.movieId})!`);
        setTitle('');
        setGenres('');
        if (onAddMovieSuccess) onAddMovieSuccess();
      } else {
        const errData = await response.json();
        setStatusMsg(`Error: ${errData.detail || 'Failed to add movie'}`);
      }
    } catch (err) {
      setStatusMsg('Server connection failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <aside className="settings-sidebar">
      <div>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          ⚙️ Control Center
        </h2>
      </div>

      <div className="slider-group">
        <div className="slider-header">
          <span>Collaborative SVD Weight</span>
          <span style={{ color: '#818cf8', fontWeight: 'bold' }}>{weightCol.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min="0.0"
          max="1.0"
          step="0.05"
          value={weightCol}
          onChange={(e) => setWeightCol(parseFloat(e.target.value))}
        />
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          Balances latents-based collaborative filtering vs. content description vectors.
        </p>
      </div>

      <div className="slider-group">
        <div className="slider-header">
          <span>Novelty (Hidden Gems) Bias</span>
          <span style={{ color: '#818cf8', fontWeight: 'bold' }}>{novelty.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min="0.0"
          max="1.0"
          step="0.05"
          value={novelty}
          onChange={(e) => setNovelty(parseFloat(e.target.value))}
        />
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          Penalizes globally popular hits to surface obscure, highly-rated treasures.
        </p>
      </div>

      <div className="slider-group">
        <div className="slider-header">
          <span>Genre Diversity Bias</span>
          <span style={{ color: '#818cf8', fontWeight: 'bold' }}>{diversity.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min="0.0"
          max="1.0"
          step="0.05"
          value={diversity}
          onChange={(e) => setDiversity(parseFloat(e.target.value))}
        />
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          Greedy re-ranking filter to prevent multiple recommendations of overlapping genres.
        </p>
      </div>

      <div className="glass-card" style={{ padding: '14px', marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>👤 Session Profile</h4>
        <p style={{ fontSize: '0.8rem', wordBreak: 'break-all' }}>
          ID: <code style={{ color: '#f43f5e' }}>{userId || 'None'}</code>
        </p>
        <button className="btn-primary" style={{ padding: '6px', fontSize: '0.8rem', background: '#25283c' }} onClick={onReset}>
          Reset Session 🔄
        </button>
      </div>

      {/* Admin catalog panel */}
      <div className="glass-card" style={{ padding: '14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <h4 
          style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', justifyContent: 'between', alignItems: 'center' }}
          onClick={() => setIsAdminOpen(!isAdminOpen)}
        >
          🔐 Catalog Manager {isAdminOpen ? '▲' : '▼'}
        </h4>

        {isAdminOpen && (
          <form onSubmit={handleAddMovie} style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '6px' }}>
            <input
              type="text"
              placeholder="Movie Title (e.g. Dune: Part Two)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              style={{ padding: '6px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'rgba(0,0,0,0.2)', color: 'white', fontSize: '0.8rem' }}
            />
            <input
              type="text"
              placeholder="Genres (e.g. Sci-Fi|Adventure)"
              value={genres}
              onChange={(e) => setGenres(e.target.value)}
              style={{ padding: '6px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'rgba(0,0,0,0.2)', color: 'white', fontSize: '0.8rem' }}
            />
            <button className="btn-primary" style={{ padding: '6px', fontSize: '0.8rem' }} type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Adding...' : 'Add Dynamic Movie 🚀'}
            </button>
            {statusMsg && (
              <p style={{ fontSize: '0.75rem', color: '#10b981', marginTop: '4px', wordBreak: 'break-word' }}>{statusMsg}</p>
            )}
          </form>
        )}
      </div>
    </aside>
  );
}
