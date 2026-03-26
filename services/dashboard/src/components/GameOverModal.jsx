import { formatCash, formatCompliance } from '../utils/formatters.js'

export default function GameOverModal({ gameState, gameOverReason, onReset }) {
  if (!gameState) return null
  const { company, flows = [], nodes = [] } = gameState
  const DEFEAT_REASONS = ['Faillite', 'Shutdown', 'Exode', 'Breach', 'bankruptcy', 'shutdown', 'reputation', 'compliance', 'breach']
  const isVictory = !gameOverReason || !DEFEAT_REASONS.some(r => gameOverReason.toLowerCase().includes(r.toLowerCase()))
  const activeFlows = flows.filter(f => f.is_active).length
  const lostNodes = nodes.filter(n => n.compromised && n.business_category === 'Revenue Critical')
  const compliance = formatCompliance(company.compliance)

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000, fontFamily: 'Inter'
    }}>
      <div style={{
        background: '#FFFFFF', borderRadius: 12, width: 440,
        boxShadow: '0 20px 60px rgba(0,0,0,0.2)', overflow: 'hidden'
      }}>
        {/* Header bar */}
        <div style={{
          background: isVictory ? '#10B981' : '#EF4444',
          padding: '20px 24px', textAlign: 'center'
        }}>
          <img
            src={isVictory ? '/assets/ui/victory-trophy.png' : '/assets/ui/defeat-servers.png'}
            width={80} height={80}
            style={{ marginBottom: 8, objectFit: 'contain' }}
            onError={e => e.target.style.display = 'none'}
          />
          <div style={{ fontSize: 20, fontWeight: 800, color: '#FFFFFF' }}>
            {isVictory ? '🏆 Strategy Successful' : '💀 Simulation Failed'}
          </div>
          <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.85)', marginTop: 4 }}>
            {isVictory ? `${company.name} survives` : gameOverReason}
          </div>
        </div>

        {/* Stats */}
        <div style={{ padding: '20px 24px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            {isVictory ? (
              <>
                {[
                  ['Final Cash Runway',       formatCash(company.cash)],
                  ['Board Trust',             `${Math.round(company.reputation * 100)}%`],
                  ['Legal Status',            compliance.label],
                  ['Revenue Streams Active',  `${activeFlows} / ${flows.length}`],
                  ['Turns Survived',          `${company.turn} / 10`],
                ].map(([label, val]) => statRow(label, val))}
              </>
            ) : (
              <>
                {[
                  ['Cash at Failure',         formatCash(company.cash)],
                  ['Revenue at Risk',         `€${company.total_revenue_at_risk}K/turn`],
                  ['Turn of Failure',         `Turn ${company.turn}`],
                ].map(([label, val]) => statRow(label, val))}
                {lostNodes.length > 0 && (
                  <tr>
                    <td style={tdLabel}>Critical Dependencies Lost</td>
                    <td style={tdValue}>
                      {lostNodes.map(n => n.business_name).join(', ')}
                    </td>
                  </tr>
                )}
              </>
            )}
          </table>
        </div>

        {/* Reset button */}
        <div style={{ padding: '0 24px 24px' }}>
          <button
            onClick={onReset}
            style={{
              width: '100%', padding: '12px', borderRadius: 8, border: 'none',
              background: '#2563EB', color: '#FFFFFF',
              fontFamily: 'Inter', fontWeight: 700, fontSize: 14,
              cursor: 'pointer'
            }}
          >
            New Simulation
          </button>
        </div>
      </div>
    </div>
  )
}

function statRow(label, val) {
  return (
    <tr key={label}>
      <td style={tdLabel}>{label}</td>
      <td style={tdValue}>{val}</td>
    </tr>
  )
}
const tdLabel = { fontFamily:'Inter', fontSize:12, color:'#64748B', paddingBottom:10, width:'55%' }
const tdValue = { fontFamily:'JetBrains Mono', fontSize:12, color:'#0F172A', paddingBottom:10, fontWeight:600 }
