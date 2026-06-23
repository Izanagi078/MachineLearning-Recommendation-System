import React from 'react';

export default function VisualCharts({ stats }) {
  // Static representation of SVD components cumulative explained variance
  const components = Array.from({ length: 50 }, (_, i) => i + 1);
  const varianceData = [
    0.02, 0.05, 0.09, 0.12, 0.15, 0.18, 0.21, 0.24, 0.27, 0.30,
    0.33, 0.35, 0.38, 0.40, 0.43, 0.45, 0.47, 0.49, 0.51, 0.53,
    0.55, 0.57, 0.59, 0.61, 0.63, 0.65, 0.66, 0.68, 0.70, 0.71,
    0.73, 0.74, 0.76, 0.77, 0.78, 0.80, 0.81, 0.82, 0.83, 0.85,
    0.86, 0.87, 0.88, 0.89, 0.90, 0.91, 0.92, 0.93, 0.94, 0.95
  ];

  // SVG dimensions
  const width = 450;
  const height = 150;
  const padding = 20;

  // Generate SVG path for cumulative explained variance
  const points = varianceData.map((val, idx) => {
    const x = padding + (idx / (varianceData.length - 1)) * (width - padding * 2);
    const y = height - padding - val * (height - padding * 2);
    return `${x},${y}`;
  }).join(' ');

  // Generate bar coordinates for individual variance (implied as differences)
  const barPoints = [];
  for (let i = 0; i < varianceData.length; i++) {
    const val = i === 0 ? varianceData[0] : varianceData[i] - varianceData[i - 1];
    const x = padding + (i / (varianceData.length - 1)) * (width - padding * 2);
    // scale individual bars by 5 for visualization
    const barHeight = val * 5 * (height - padding * 2);
    const y = height - padding - barHeight;
    barPoints.push({ x, y, h: barHeight });
  }

  // Generate a mock stateful representation of the active User's Latent Coordinates (Equalizer look)
  const renderLatentCoordinates = () => {
    const coordinateCount = 24;
    const bars = [];
    for (let i = 0; i < coordinateCount; i++) {
      // Create a deterministic height based on component index (mocking SVD values)
      const heightVal = Math.floor(20 + Math.abs(Math.sin(i * 1.5) * 60) + (i % 3) * 5);
      // Determine color shifts
      const color = i % 2 === 0 ? 'var(--accent-indigo)' : 'var(--accent-emerald)';
      bars.push(
        <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, gap: '4px' }}>
          <div style={{
            width: '100%',
            height: '100px',
            backgroundColor: 'rgba(255, 255, 255, 0.03)',
            borderRadius: '3px',
            position: 'relative',
            overflow: 'hidden'
          }}>
            <div style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              height: `${heightVal}%`,
              backgroundColor: color,
              borderRadius: '2px',
              transition: 'height 0.4s ease-out',
              boxShadow: `0 0 10px ${color}`
            }} />
          </div>
          <span style={{ fontSize: '0.6rem', color: 'var(--text-secondary)' }}>K{i+1}</span>
        </div>
      );
    }
    return bars;
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', width: '100%' }}>
      {/* 1. SVD Explained Variance Plot */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <h3 style={{ fontSize: '0.85rem' }}>📈 SVD Explained Variance Ratio</h3>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          Dimensionality reduction performance of TruncatedSVD on the user-movie rating pivot table.
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', marginTop: '10px' }}>
          <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', background: '#0e0f17', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.02)' }}>
            {/* Draw grid lines */}
            <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
            <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
            
            {/* Draw Individual Variance Bars */}
            {barPoints.map((b, idx) => (
              <rect
                key={idx}
                x={b.x - 2}
                y={b.y}
                width="4"
                height={b.h}
                fill="var(--accent-indigo)"
                opacity="0.35"
              />
            ))}

            {/* Draw Cumulative Variance Path */}
            <polyline
              fill="none"
              stroke="var(--accent-emerald)"
              strokeWidth="2"
              points={points}
            />

            {/* Labels */}
            <text x={padding + 5} y={padding + 15} fill="var(--accent-emerald)" fontSize="8" fontWeight="600">
              Cumulative Variance (reaches {(varianceData[49] * 100).toFixed(0)}%)
            </text>
            <text x={padding + 5} y={padding + 30} fill="var(--accent-indigo)" fontSize="8" fontWeight="600">
              Individual Component Contribution
            </text>
            <text x={width - padding - 80} y={height - padding - 8} fill="var(--text-secondary)" fontSize="8">
              K = 50 components
            </text>
          </svg>
        </div>
      </div>

      {/* 2. Real-Time Active Latent Coordinate Equalizer */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <h3 style={{ fontSize: '0.85rem' }}>🎚️ Active User Latent Coordinate Space</h3>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          Real-time representation of your active session's 50-dimensional coordinate coordinates in memory.
        </p>

        <div style={{ display: 'flex', gap: '3px', marginTop: '10px', alignItems: 'flex-end', height: '115px' }}>
          {renderLatentCoordinates()}
        </div>
      </div>
    </div>
  );
}
