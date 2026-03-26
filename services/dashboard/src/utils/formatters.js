export function formatCash(cash) {
  return cash >= 1000 ? `€${(cash / 1000).toFixed(1)}M` : `€${cash}K`
}

export function formatCashColor(cash) {
  if (cash > 3000) return '#10B981'
  if (cash > 1000) return '#F59E0B'
  return '#EF4444'
}

export function formatReputation(reputation) {
  const pct = Math.round(reputation * 100)
  if (reputation > 0.7) return { label: `${pct}% (High)`, color: '#10B981' }
  if (reputation > 0.4) return { label: `${pct}% (Med)`,  color: '#F59E0B' }
  return                       { label: `${pct}% (Low)`,  color: '#EF4444' }
}

export function formatCompliance(compliance) {
  if (compliance > 0.7) return { label: 'SOC2 COMPLIANT ✅', color: '#10B981' }
  if (compliance > 0.3) return { label: '⚠ AT RISK',         color: '#F59E0B' }
  return                       { label: '🔴 NON-COMPLIANT',   color: '#EF4444' }
}

export function formatTurnTimestamp(turn) {
  const safeTurn = Math.max(1, turn || 1)
  const totalMins = safeTurn * 5
  const h = String(15 + Math.floor(totalMins / 60)).padStart(2, '0')
  const m = String(totalMins % 60).padStart(2, '0')
  return `${h}:${m}`
}
