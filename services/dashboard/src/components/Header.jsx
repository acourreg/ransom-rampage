import { formatCash, formatCompliance, formatReputation } from '../utils/formatters.js'

function TurnRadial({ turn, total = 10 }) {
  const R = 18
  const cx = 24, cy = 24
  const circumference = 2 * Math.PI * R
  const progress = turn / total
  const filled = circumference * progress
  const gap = circumference - filled
  // Rotate so arc starts at the top
  const rotation = -90

  const arcColor = turn <= 3 ? '#48BB78' : turn <= 7 ? '#ECC94B' : '#FC8181'

  return (
    <svg width={48} height={48} viewBox="0 0 48 48" style={{ flexShrink: 0 }}>
      {/* Track */}
      <circle
        cx={cx} cy={cy} r={R}
        fill="none" stroke="#1A1F26" strokeWidth={4}
      />
      {/* Progress arc */}
      <circle
        cx={cx} cy={cy} r={R}
        fill="none"
        stroke={arcColor}
        strokeWidth={4}
        strokeLinecap="round"
        strokeDasharray={`${filled} ${gap}`}
        transform={`rotate(${rotation} ${cx} ${cy})`}
        style={{ transition: 'stroke-dasharray 0.4s ease, stroke 0.4s ease' }}
      />
      {/* Turn number */}
      <text
        x={cx} y={cy - 3}
        textAnchor="middle" dominantBaseline="middle"
        fontFamily="JetBrains Mono" fontWeight={700} fontSize={13}
        fill="#FFFFFF"
      >
        {turn}
      </text>
      {/* /10 label */}
      <text
        x={cx} y={cy + 10}
        textAnchor="middle" dominantBaseline="middle"
        fontFamily="Inter" fontWeight={400} fontSize={7}
        fill="#CBD5E0"
      >
        / {total}
      </text>
    </svg>
  )
}

export default function Header({ company, nodes = [], flows = [] }) {
  if (!company) return null
  const compliance = formatCompliance(company.compliance)
  const reputation = formatReputation(company.reputation)

  const totalCosts = nodes
    .filter(n => typeof n.cost === 'number')
    .reduce((sum, n) => sum + n.cost * 5, 0)
  const totalRevenue = flows.reduce((sum, f) => sum + (f.current_revenue ?? 0), 0)
  const netPerTurn = totalRevenue - totalCosts

  return (
    <div style={{
      background: '#242B35', borderBottom: '1px solid #1A1F26',
      padding: '0 1.5rem', height: 56, flexShrink: 0,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <TurnRadial turn={company.turn} total={company.max_turns ?? 10} />
        <div style={{ fontFamily: 'Inter', fontWeight: 600, fontSize: 15, color: '#FFFFFF' }}>
          {company.name}
          <div style={{ color: '#CBD5E0', fontWeight: 400, fontSize: 10, letterSpacing: 0.5, marginTop: 1 }}>
            TURN {company.turn} OF {company.max_turns ?? 10}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <div style={metricCard}>
          <div style={metricLabel}>CASH RUNWAY</div>
          <div style={{ ...metricValue, color: cashColor(company.cash) }}>
            {formatCash(company.cash)}
          </div>
        </div>
        <div style={metricCard}>
          <div style={metricLabel}>BOARD TRUST</div>
          <div style={{ ...metricValue, color: trustColor(company.reputation) }}>{reputation.label}</div>
        </div>
        <div style={metricCard}>
          <div style={metricLabel}>COMPLIANCE</div>
          <div style={{ ...metricValue, color: complianceColor(company.compliance) }}>{Math.round(company.compliance * 100)}%</div>
        </div>
        <div style={metricCard}>
          <div style={metricLabel}>REVENUE</div>
          <div style={{ ...metricValue, color: '#48BB78' }}>+€{totalRevenue}K</div>
        </div>
        <div style={metricCard}>
          <div style={metricLabel}>COSTS</div>
          <div style={{ ...metricValue, color: '#FC8181' }}>-€{totalCosts}K</div>
        </div>
        <div style={{ ...metricCard, borderLeft: '2px solid #334155' }}>
          <div style={metricLabel}>NET/TURN</div>
          <div style={{ ...metricValue, fontWeight: 800, color: netPerTurn >= 0 ? '#48BB78' : '#FC8181' }}>
            {netPerTurn >= 0 ? '+' : ''}€{netPerTurn}K
          </div>
        </div>
      </div>
    </div>
  )
}

function cashColor(cash) {
  if (cash > 3000) return '#48BB78'
  if (cash > 1000) return '#ECC94B'
  return '#FC8181'
}

function trustColor(reputation) {
  if (reputation > 0.7) return '#4299E1'
  if (reputation > 0.4) return '#ECC94B'
  return '#FC8181'
}

function complianceColor(compliance) {
  if (compliance >= 0.7) return '#10B981'
  if (compliance >= 0.5) return '#F59E0B'
  return '#EF4444'
}

function riskColor(compliance) {
  if (compliance > 0.7) return '#48BB78'
  if (compliance > 0.3) return '#ECC94B'
  return '#FC8181'
}

const metricCard = {
  background: '#1E252E', border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 6, padding: '4px 12px', textAlign: 'center', minWidth: 120
}
const metricLabel = {
  fontFamily: 'Inter', fontSize: 9, color: '#CBD5E0',
  textTransform: 'uppercase', letterSpacing: 1, marginBottom: 2
}
const metricValue = {
  fontFamily: 'JetBrains Mono', fontSize: 12, fontWeight: 700
}
