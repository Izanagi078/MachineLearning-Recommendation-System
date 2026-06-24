import React, { useState } from 'react';
import api from '../api';

const DEMO_USERS = ['User 10', 'User 50', 'User 100', 'User 200', 'User 300'];

export default function LoginModal({ isOpen, onClose, onLogin }) {
  const [mode, setMode] = useState('login'); // 'login' or 'register'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [selectedDemo, setSelectedDemo] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (selectedDemo) {
        const data = await api.loginDemo(selectedDemo);
        onLogin(data.username, data.token);
        setSelectedDemo('');
        onClose();
      } else {
        if (!username.trim() || !password) {
          setError('Please fill in both username and password.');
          setLoading(false);
          return;
        }
        const data = mode === 'login'
          ? await api.login(username.trim(), password)
          : await api.register(username.trim(), password);
        onLogin(data.username, data.token);
        setUsername('');
        setPassword('');
        onClose();
      }
    } catch (err) {
      setError(err.body?.detail || 'Cannot connect to authorization server.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      backdropFilter: 'blur(16px)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div className="glass-card" style={{
        width: '100%',
        maxWidth: '420px',
        border: '1px solid rgba(99, 102, 241, 0.25)',
        boxShadow: '0 30px 60px rgba(0,0,0,0.8), 0 0 40px rgba(99, 102, 241, 0.12)',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        position: 'relative',
        padding: '30px'
      }}>
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '14px',
            right: '16px',
            background: 'transparent',
            color: 'var(--text-secondary)',
            fontSize: '1.2rem',
            boxShadow: 'none'
          }}
        >
          ✕
        </button>

        <div style={{ textAlign: 'center', marginBottom: '4px' }}>
          <h2 style={{ fontSize: '1.4rem', marginBottom: '6px' }}>🔑 Recommender Auth Portal</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Authenticate to sync offline latent updates and store preferences
          </p>
        </div>

        {/* Tab Selection */}
        {!selectedDemo && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', padding: '2px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
            <button
              onClick={() => { setMode('login'); setError(''); }}
              style={{
                padding: '8px',
                fontSize: '0.85rem',
                borderRadius: '6px',
                background: mode === 'login' ? 'var(--accent-indigo)' : 'transparent',
                color: 'white',
                boxShadow: 'none'
              }}
            >
              Sign In
            </button>
            <button
              onClick={() => { setMode('register'); setError(''); }}
              style={{
                padding: '8px',
                fontSize: '0.85rem',
                borderRadius: '6px',
                background: mode === 'register' ? 'var(--accent-indigo)' : 'transparent',
                color: 'white',
                boxShadow: 'none'
              }}
            >
              Register
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Option 1: Demo dropdown */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: '600' }}>
              Select Pre-Trained Demo Profile:
            </label>
            <select
              id="demo-profile-select"
              name="demoProfile"
              value={selectedDemo}
              onChange={(e) => {
                setSelectedDemo(e.target.value);
                if (e.target.value) {
                  setUsername('');
                  setPassword('');
                }
              }}
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                background: '#151624',
                color: 'white',
                fontFamily: 'var(--font-family)',
                fontSize: '0.85rem',
                outline: 'none'
              }}
            >
              <option value="">-- Choose Profile (Passwordless) --</option>
              {DEMO_USERS.map((u) => (
                <option key={u} value={u}>{u}</option>
              ))}
            </select>
          </div>

          {!selectedDemo && (
            <>
              <div style={{ textAlign: 'center', fontSize: '0.75rem', color: 'rgba(255,255,255,0.15)', fontWeight: 'bold' }}>
                — OR CUSTOM ACCOUNT —
              </div>

              {/* Username Input */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: '600' }}>
                  Username:
                </label>
                <input
                  id="auth-username"
                  name="username"
                  type="text"
                  placeholder="e.g. movie_fan"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    background: 'rgba(0,0,0,0.3)',
                    color: 'white',
                    fontFamily: 'var(--font-family)',
                    fontSize: '0.85rem',
                    outline: 'none'
                  }}
                />
              </div>

              {/* Password Input */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: '600' }}>
                  Password:
                </label>
                <input
                  id="auth-password"
                  name="password"
                  type="password"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    background: 'rgba(0,0,0,0.3)',
                    color: 'white',
                    fontFamily: 'var(--font-family)',
                    fontSize: '0.85rem',
                    outline: 'none'
                  }}
                />
              </div>
            </>
          )}

          {error && (
            <p style={{ color: 'var(--accent-rose)', fontSize: '0.75rem', textAlign: 'center', wordBreak: 'break-word' }}>{error}</p>
          )}

          <button
            type="submit"
            className="btn-primary"
            disabled={loading}
            style={{ width: '100%', padding: '12px', fontSize: '0.9rem', marginTop: '6px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}
          >
            {loading ? 'Processing...' : selectedDemo ? 'Load Demo Profile 🔓' : mode === 'login' ? 'Sign In 🔑' : 'Create Account 🚀'}
          </button>
        </form>
      </div>
    </div>
  );
}
