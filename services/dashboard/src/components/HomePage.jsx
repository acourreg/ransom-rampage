import { useNavigate } from 'react-router-dom';

export default function HomePage() {
  const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

  const handlePlay = () => {
    if (isLocal) {
      // Local dev: skip Cognito, go directly to play
      window.location.href = '/play';
    } else {
      // Prod: /play is protected by ALB Cognito — redirect triggers login
      window.location.href = '/play';
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: '#F8FAFC',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: "'Inter', sans-serif",
      padding: '2rem',
    }}>
      <h1 style={{ fontSize: '2.5rem', color: '#0F172A', marginBottom: '0.5rem' }}>
        Ransom Rampage
      </h1>
      <p style={{ fontSize: '1.2rem', color: '#64748B', marginBottom: '2rem', textAlign: 'center', maxWidth: '600px' }}>
        CTO Crisis Simulator — Defend your AI-generated fintech startup
        from a live ransomware attack. 3 AI advisors. 1 hacker. 15 turns.
        Can you keep the lights on?
      </p>

      <button
        onClick={handlePlay}
        style={{
          padding: '1rem 2.5rem',
          fontSize: '1.1rem',
          fontWeight: 600,
          color: '#FFFFFF',
          backgroundColor: '#2563EB',
          border: 'none',
          borderRadius: '8px',
          cursor: 'pointer',
        }}
      >
        {isLocal ? 'Play Now (local mode)' : 'Login to Play'}
      </button>

      <p style={{ marginTop: '1rem', fontSize: '0.85rem', color: '#94A3B8' }}>
        {isLocal ? 'Running locally — auth bypassed' : 'Sign in with Google to start a simulation'}
      </p>
    </div>
  );
}
