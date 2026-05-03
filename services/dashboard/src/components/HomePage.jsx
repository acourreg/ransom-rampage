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
      height: '100vh', background: '#1A2332',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      fontFamily: 'Inter'
    }}>
      <div style={{ textAlign: 'center', maxWidth: 480 }}>
        <img
          src="/assets/avatars/ransom-rampage.jpeg"
          width={360}
          style={{
            marginBottom: 24, objectFit: 'contain',
            borderRadius: 12,
            boxShadow: '0 0 40px rgba(37,99,235,0.25), 0 8px 32px rgba(0,0,0,0.5)',
          }}
          onError={e => e.target.style.display = 'none'}
        />
        <div style={{ fontSize: 11, fontWeight: 600, color: '#60A5FA', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 16 }}>
          CTO Crisis Simulator
        </div>
        <p style={{ color: '#94A3B8', fontSize: 15, marginBottom: 40, lineHeight: 1.6 }}>
          Can you keep the lights on?<br />
          A hacker is coming. Your board is watching.
        </p>

        <div style={{ display: 'flex', gap: 8, marginBottom: 28, justifyContent: 'center' }}>
          {[
            { icon: '⚡', label: 'AI generates your company' },
            { icon: '🛡', label: 'Defend against a live hacker' },
            { icon: '🏆', label: 'Survive the simulation' },
          ].map(({ icon, label }) => (
            <div key={label} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: 'rgba(255,255,255,0.08)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 20,
              padding: '6px 14px',
              fontFamily: 'Inter', fontSize: 12, color: '#CBD5E1',
            }}>
              <span>{icon}</span>
              <span>{label}</span>
            </div>
          ))}
        </div>

        <button
          onClick={handlePlay}
          style={{
            width: '100%', padding: '12px 24px', borderRadius: 8, border: 'none',
            background: '#2563EB',
            color: '#FFFFFF', fontFamily: 'Inter', fontWeight: 700,
            fontSize: 14, cursor: 'pointer',
          }}
        >
          {isLocal ? '⚡ Play Now (local mode)' : '🔐 Login to Play'}
        </button>

        <p style={{ fontSize: 11, color: '#64748B', marginTop: 12, textAlign: 'center' }}>
          {isLocal ? 'Running locally — auth bypassed' : 'Sign in with Google to start a simulation'}
        </p>
      </div>

      <footer style={{
        position: 'absolute',
        bottom: 20,
        left: 0,
        right: 0,
        textAlign: 'center',
        padding: '0 24px',
      }}>
        <p style={{
          fontSize: 10,
          color: '#475569',
          lineHeight: 1.6,
          maxWidth: 520,
          margin: '0 auto',
        }}>
          ⚠️ This is a fictional simulation for demonstration purposes only.
          No real companies, infrastructure, or financial data are represented.
          No personal data is stored beyond your Google login session.
          Provided "as is" with no warranty — the author reserves the right
          to modify or discontinue this service at any time.
          <br />
          <span style={{ color: '#64748B' }}>© 2026 Aurélien Courreges-Clercq</span>
        </p>
      </footer>
    </div>
  )
}
