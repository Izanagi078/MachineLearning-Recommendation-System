import React from 'react';

export default function LiveFeed({ feed }) {
  const formatTime = (ts) => {
    const date = new Date(ts * 1000);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', flex: 1, overflowY: 'auto' }}>
      <div>
        <h2 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          📡 Network Stream
        </h2>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Real-time activity logs from all sessions
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto' }}>
        {feed.length === 0 ? (
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textAlign: 'center', marginTop: '20px' }}>
            No recent activity logs yet.
          </p>
        ) : (
          feed.map((item) => {
            const isLike = item.rating >= 4.0;
            return (
              <div
                key={item.id}
                className="glass-card"
                style={{
                  padding: '12px',
                  borderRadius: '8px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                  borderLeft: `3px solid ${isLike ? 'var(--accent-emerald)' : 'var(--accent-rose)'}`
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  <span style={{ fontWeight: '500', color: '#a5b4fc' }}>{item.userId}</span>
                  <span>{formatTime(item.timestamp)}</span>
                </div>
                <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#ffffff', lineBreak: 'anywhere' }}>
                  {item.title}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem' }}>
                  <span style={{ color: isLike ? 'var(--accent-emerald)' : 'var(--accent-rose)', fontWeight: 'bold' }}>
                    {isLike ? 'Liked 👍' : 'Disliked 👎'}
                  </span>
                  <span style={{ color: 'rgba(255, 255, 255, 0.3)' }}>|</span>
                  <span style={{ color: 'var(--text-secondary)' }}>Rating: {item.rating.toFixed(1)}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
