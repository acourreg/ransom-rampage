import { useMemo } from 'react'
import { deriveIncidents } from '../utils/incidents.js'

const PRIORITY_STYLE = {
  0: { icon: '🔴', label: 'P0', color: '#EF4444', bg: 'rgba(239,68,68,0.15)' },
  1: { icon: '⚠️', label: 'P1', color: '#F59E0B', bg: 'rgba(245,158,11,0.15)' },
  2: { icon: '📋', label: 'P2', color: '#60A5FA', bg: 'rgba(96,165,250,0.15)' },
}

export default function TriageBoard({ gameState }) {
  const incidents = useMemo(() => deriveIncidents(gameState), [gameState])

  const items = incidents.length > 0 ? incidents : [{
    priority: -1, title: 'ALL SYSTEMS OPERATIONAL', impact: '', reporter: ''
  }]

  const loopItems = [...items, ...items, ...items]
  const isHealthy = incidents.length === 0
  const speed = Math.max(40, 90 - incidents.length * 3)

  return (
    <div style={{
      height: 36, background: '#0F172A',
      display: 'flex', alignItems: 'center',
      borderBottom: '1px solid #1E293B',
      overflow: 'hidden', flexShrink: 0,
      position: 'relative',
    }}>
      {/* Label fixe gauche */}
      <div style={{
        flexShrink: 0, padding: '0 12px',
        borderRight: '1px solid #1E293B',
        fontFamily: 'JetBrains Mono', fontSize: 10,
        fontWeight: 700, color: '#EF4444',
        letterSpacing: 1, whiteSpace: 'nowrap',
        background: '#0F172A', zIndex: 2,
        height: '100%', display: 'flex', alignItems: 'center',
      }}>
        🚨 LIVE
      </div>

      {/* Ticker scroll area */}
      <div className="ticker-wrap" style={{
        flex: 1, overflow: 'hidden', height: '100%',
        display: 'flex', alignItems: 'center',
        maskImage: 'linear-gradient(to right, transparent 0%, black 3%, black 97%, transparent 100%)',
      }}>
        {isHealthy ? (
          <div style={{
            fontFamily: 'JetBrains Mono', fontSize: 11,
            color: '#10B981', padding: '0 16px', whiteSpace: 'nowrap'
          }}>
            ✅ ALL SYSTEMS OPERATIONAL — No active incidents
          </div>
        ) : (
          <div style={{
            display: 'flex', alignItems: 'center',
            animation: `ticker-scroll ${speed}s linear infinite`,
            whiteSpace: 'nowrap',
          }}>
            <style>{`
              @keyframes ticker-scroll {
                0%   { transform: translateX(0); }
                100% { transform: translateX(-33.333%); }
              }
              .ticker-wrap:hover div {
                animation-play-state: paused !important;
              }
            `}</style>

            {loopItems.map((inc, i) => {
              const ps = PRIORITY_STYLE[inc.priority] ?? PRIORITY_STYLE[2]
              return (
                <span key={i} style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  padding: '0 20px',
                  fontFamily: 'JetBrains Mono', fontSize: 11,
                  color: '#E2E8F0',
                }}>
                  <span style={{
                    background: ps.bg, color: ps.color,
                    padding: '1px 6px', borderRadius: 3,
                    fontSize: 9, fontWeight: 700, letterSpacing: 0.5,
                  }}>
                    {ps.icon} {ps.label}
                  </span>
                  <span style={{ color: '#F1F5F9', fontSize: 12 }}>{inc.title}</span>
                  {inc.impact && (
                    <span style={{ color: ps.color, fontSize: 11 }}>· {inc.impact}</span>
                  )}
                  {inc.reporter && (
                    <span style={{ color: '#94A3B8', fontSize: 11 }}>· {inc.reporter}</span>
                  )}
                  <span style={{ color: '#1E3A5F', marginLeft: 8 }}>────</span>
                </span>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
