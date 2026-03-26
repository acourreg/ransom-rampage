import { useEffect, useRef } from 'react'
import { formatTurnTimestamp } from '../utils/formatters.js'

const AVATARS = {
  ciso:      { img: '/assets/avatars/ciso.png',   name: '@CISO',             color: '#2563EB' },
  sre:       { img: '/assets/avatars/sre.png',    name: '@SRE-Team',         color: '#10B981' },
  byte:      { img: '/assets/avatars/hacker.png', name: null, color: '#EF4444' },
  hacker:    { img: '/assets/avatars/hacker.png', name: null, color: '#EF4444' },
  regulator: { img: '/assets/avatars/legal.png',  name: '@Legal-Compliance', color: '#F59E0B' },
  cto:       { img: null, emoji: '👔',             name: '@CTO (You)',        color: '#0F172A' },
  system:    { img: null, emoji: '⚙️',             name: 'System',            color: '#94A3B8' },
}

export default function WarRoom({ turnLog = [], turn = 1, loading = false, adversaryName }) {
  const bottomRef = useRef(null)
  const visible = (turnLog || []).filter(e => e.message).slice(-8)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turnLog, loading])

  return (
    <div style={{
      background: '#F1F5F9', borderTop: '1px solid #E2E8F0',
      display: 'flex', flexDirection: 'column', height: 200, flexShrink: 0
    }}>
      {/* Channel header */}
      <div style={{
        padding: '6px 16px', borderBottom: '1px solid #E2E8F0',
        background: '#FFFFFF', display: 'flex', alignItems: 'center', gap: 8
      }}>
        <span style={{ fontFamily: 'Inter', fontWeight: 700, fontSize: 13, color: '#0F172A' }}>
          #incident-response
        </span>
        <span style={{ fontFamily: 'Inter', fontSize: 11, color: '#94A3B8' }}>
          {visible.length} messages
        </span>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
        {visible.length === 0 && (
          <div style={{ padding: '8px 16px', fontFamily: 'JetBrains Mono', fontSize: 11, color: '#94A3B8' }}>
            ⚙️ System  Waiting for game events...
          </div>
        )}

        {visible.map((entry, i) => {
          const av = { ...(AVATARS[entry.source] ?? AVATARS.system) }
          if ((entry.source === 'byte' || entry.source === 'hacker') && av.name === null) {
            av.name = `@${adversaryName || 'Threat-Actor'}`
          }
          const msgTurn = Math.max(1, turn - (visible.length - i - 1))
          const ts = formatTurnTimestamp(msgTurn)
          return (
            <div key={i} style={{
              display: 'flex', gap: 10, padding: '5px 16px',
              borderBottom: '1px solid #E2E8F0', alignItems: 'flex-start'
            }}>
              {/* Avatar */}
              {av.img ? (
                <img
                  src={av.img} width={44} height={44}
                  style={{ borderRadius: '50%', border: '2px solid #E2E8F0', flexShrink: 0, objectFit: 'cover' }}
                  onError={e => { e.target.style.display = 'none' }}
                />
              ) : (
                <div style={{
                  width: 44, height: 44, borderRadius: '50%',
                  background: '#E2E8F0', display: 'flex', alignItems: 'center',
                  justifyContent: 'center', fontSize: 22, flexShrink: 0
                }}>
                  {av.emoji}
                </div>
              )}

              {/* Content */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 2 }}>
                  <span style={{ fontFamily: 'Inter', fontWeight: 700, fontSize: 12, color: av.color }}>
                    {av.name}
                  </span>
                  <span style={{ fontFamily: 'JetBrains Mono', fontSize: 10, color: '#94A3B8' }}>
                    [{ts}]
                  </span>
                </div>
                <div style={{ fontFamily: 'Inter', fontSize: 12, color: '#0F172A', lineHeight: 1.4 }}>
                  {entry.message}
                </div>
              </div>
            </div>
          )
        })}

        {/* Typing indicator */}
        {loading && (
          <div style={{ display: 'flex', gap: 10, padding: '5px 16px', alignItems: 'center' }}>
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#E2E8F0', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14 }}>
              ⚙️
            </div>
            <TypingIndicator />
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span style={{ fontFamily: 'Inter', fontSize: 11, color: '#94A3B8', marginRight: 4 }}>
        Agents deliberating
      </span>
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          width: 6, height: 6, borderRadius: '50%', background: '#94A3B8',
          animation: 'pulse 1.2s ease-in-out infinite',
          animationDelay: `${i * 0.2}s`
        }} />
      ))}
      <style>{`
        @keyframes pulse {
          0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  )
}
