import React, { useState } from 'react';

const DEMO_USERS = ['User 10', 'User 50', 'User 100', 'User 200', 'User 300'];

export default function LoginModal({ isOpen, onClose, onLogin }) {
  const [username, setUsername] = useState('');
  const [selectedDemo, setSelectedDemo] = useState('');
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    let finalUser = '';
    if (selectedDemo) {
      finalUser = selectedDemo;
    } else if (username.trim()) {
      // Clean custom username
      finalUser = username.trim();
    } else {
      setError('Please select a demo user or enter a custom username.');
      return;
    }

    onLogin(finalUser);
    setUsername('');
    setSelectedDemo('');
    onClose();
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(12px)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div className="glass-card" style={{
        width: '100%',
        maxWidth: '400px',
        border: '1px solid rgba(99, 102, 241, 0.2)',
        boxShadow: '0 30px 60px rgba(0,0,0,0.8), 0 0 30px rgba(99, 102, 241, 0.1)',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        position: 'relative'
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
          <h2 style={{ fontSize: '1.4rem', marginBottom: '6px' }}>🔑 Portal Authentication</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Log in to retrieve history or test pre-trained profiles
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Option 1: Demo dropdown */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: '600' }}>
              Select Pre-Trained Demo User:
            </label>
            <select
              value={selectedDemo}
              onChange={(e) => {
                setSelectedDemo(e.target.value);
                if (e.target.value) setUsername(''); // clear custom
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
              <option value="">-- Choose Profile --</option>
              {DEMO_USERS.map((u) => (
                <option key={u} value={u}>{u}</option>
              ))}
            </select>
          </div>

          <div style={{ textAlign: 'center', fontSize: '0.75rem', color: 'rgba(255,255,255,0.15)', fontWeight: 'bold' }}>
            — OR —
          </div>

          {/* Option 2: Custom Text Input */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: '600' }}>
              Enter Custom Username:
            </label>
            <input
              type="text"
              placeholder="e.g. john_doe"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (e.target.value) setSelectedDemo(''); // clear dropdown
              }}
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

          {error && (
            <p style={{ color: 'var(--accent-rose)', fontSize: '0.75rem', textAlign: 'center' }}>{error}</p>
          )}

          <button
            type="submit"
            className="btn-primary"
            style={{ width: '100%', padding: '12px', fontSize: '0.9rem', marginTop: '6px' }}
          >
            Confirm & Load Profile 🔓
          </button>
        </form>
      </div>
    </div>
  );
}
