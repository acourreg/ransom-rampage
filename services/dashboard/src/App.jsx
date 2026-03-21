import { useState, useEffect } from 'react'

export default function App() {
  return (
    <div style={{ padding: '2rem' }}>
      <h1 style={{ fontFamily: 'Inter', fontWeight: 800, fontSize: '2rem', color: '#0F172A' }}>
        RANSOM RAMPAGE
      </h1>
      <p style={{ color: '#64748B', marginTop: '0.5rem' }}>CTO Crisis Simulator — Dashboard loading...</p>
      <div style={{ marginTop: '2rem', padding: '1rem', background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '8px', maxWidth: '400px' }}>
        <p style={{ fontFamily: 'JetBrains Mono', fontSize: '0.85rem', color: '#10B981' }}>
          ✅ Frontend service up
        </p>
        <p style={{ fontFamily: 'JetBrains Mono', fontSize: '0.85rem', color: '#64748B', marginTop: '0.5rem' }}>
          API check: <ApiStatus />
        </p>
      </div>
    </div>
  )
}

function ApiStatus() {
  const [status, setStatus] = useState('checking...')

  useEffect(() => {
    fetch('/health')
      .then(r => r.ok ? setStatus('✅ api-gateway reachable') : setStatus('❌ ' + r.status))
      .catch(() => setStatus('❌ unreachable'))
  }, [])

  return <span>{status}</span>
}