import { useState } from 'react'
import { buildGenerationPrompt } from '../config/startupThemes.js'

export default function NewGameScreen({ onGenerate, loading }) {
  const [generationMeta, setGenerationMeta] = useState(null)
  const [generatedPrompt, setGeneratedPrompt] = useState('')

  function handleGenerate() {
    const gen = buildGenerationPrompt()
    setGenerationMeta(gen.meta)
    setGeneratedPrompt(gen.prompt)
    console.log(`[GENERATE] ${gen.meta.thematic} | ${gen.meta.domain} | shape=${gen.meta.shape} nodes=${gen.meta.nodeCount}`)
    onGenerate(gen.prompt, { shape: gen.shape, nodeCount: gen.nodeCount, threatAgent: gen.threatAgent })
  }

  return (
    <div style={{
      height: '100vh', background: '#1A2332',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      fontFamily: 'Inter'
    }}>
      <div style={{ textAlign: 'center', maxWidth: 480 }}>
        <img
          src="/assets/avatars/ransom-rampage.png"
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
            { icon: '🏆', label: 'Survive 10 turns' },
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

        <div style={{ marginBottom: 12 }}>
          <input
            value={generatedPrompt || ''}
            readOnly
            placeholder="Click Generate — a random startup will be conjured"
            style={{
              width: '100%', boxSizing: 'border-box',
              padding: '12px 16px', borderRadius: 8,
              border: '1px solid rgba(255,255,255,0.15)', fontFamily: 'Inter', fontSize: 13,
              color: generatedPrompt ? '#F1F5F9' : '#475569',
              background: 'rgba(255,255,255,0.05)',
              outline: 'none', cursor: 'default', marginBottom: 8,
            }}
          />
          <button
            onClick={handleGenerate}
            disabled={loading}
            style={{
              width: '100%', padding: '12px 24px', borderRadius: 8, border: 'none',
              background: loading ? '#94A3B8' : '#2563EB',
              color: '#FFFFFF', fontFamily: 'Inter', fontWeight: 700,
              fontSize: 14, cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? '⏳' : '⚡'} {loading ? 'Provisioning...' : 'Generate Scenario'}
          </button>
        </div>

        {loading && generationMeta ? (
          <p style={{ color: '#60A5FA', fontSize: 11, fontFamily: 'JetBrains Mono' }}>
            Provisioning infrastructure... (~20s)
          </p>
        ) : generationMeta ? (
          <p style={{ fontSize: 11, color: '#64748B', marginTop: 4, textAlign: 'center' }}>
            {generationMeta.thematic} · {generationMeta.domain}
          </p>
        ) : (
          <p style={{
            marginTop: 12, fontFamily: 'Inter', fontSize: 11,
            color: '#475569', textAlign: 'center'
          }}>
            Each game generates a unique fintech company, infrastructure graph,
            and threat actor. No two games are alike.
          </p>
        )}
      </div>
    </div>
  )
}
