export function deriveIncidents(gameState) {
  if (!gameState) return []
  const { nodes = [], flows = [], regulator = {}, company = {} } = gameState
  const incidents = []

  // P0
  nodes.filter(n => n.compromised).forEach(n => incidents.push({
    priority: 0, label: 'P0', labelColor: '#EF4444', wash: '#FEF2F2',
    title: `${n.business_name} Compromised`,
    status: 'Investigating',
    impact: `€${n.revenue_exposure}K/turn at risk`,
    positive: false,
    reporter: '@CISO',
    flowRef: null,
  }))
  nodes.filter(n => n.locked).forEach(n => incidents.push({
    priority: 0, label: 'P0', labelColor: '#EF4444', wash: '#FEF2F2',
    title: `${n.business_name} Locked — Ransom Demand`,
    status: 'Critical',
    impact: `${n.flows_supported?.length || 0} flows blocked`,
    positive: false,
    reporter: '@CISO',
    flowRef: null,
  }))

  // P1
  nodes.filter(n => n.offline).forEach(n => incidents.push({
    priority: 1, label: 'P1', labelColor: '#F59E0B', wash: '#FFFBEB',
    title: `${n.business_name} Offline`,
    status: 'Investigating',
    impact: 'Flows disrupted',
    positive: false,
    reporter: '@SRE-Team',
    flowRef: null,
  }))
  if (regulator.breach_timer != null) incidents.push({
    priority: 1, label: 'P1', labelColor: '#F59E0B', wash: '#FFFBEB',
    title: `Breach Timer: ${regulator.breach_timer} turns to report`,
    status: 'Action Required',
    impact: 'Potential fine incoming',
    positive: false,
    reporter: '@Legal-Compliance',
    flowRef: null,
  })
  if (company.compliance < 0.5) incidents.push({
    priority: 1, label: 'P1', labelColor: '#F59E0B', wash: '#FFFBEB',
    title: 'Compliance Risk — Audit Imminent',
    status: 'Monitoring',
    impact: 'Board Trust dropping',
    positive: false,
    reporter: '@Legal-Compliance',
    flowRef: null,
  })
  flows.filter(f => f.risk_level === 'critical').forEach(f => incidents.push({
    priority: 1, label: 'P1', labelColor: '#F59E0B', wash: '#FFFBEB',
    title: `Revenue Stream '${f.name}' Compromised`,
    status: 'Critical',
    impact: `€${f.current_revenue}K/turn affected`,
    positive: false,
    reporter: '@CISO',
    flowRef: f.node_path,
  }))

  // P2
  nodes.filter(n => n.fogged).forEach(n => incidents.push({
    priority: 2, label: 'P2', labelColor: '#2563EB', wash: '#EFF6FF',
    title: `${n.business_name} — Unknown Status`,
    status: 'Monitoring',
    impact: 'Recommend scan',
    positive: false,
    reporter: '@SRE-Team',
    flowRef: null,
  }))
  nodes.filter(n => !n.fogged && n.defense < 4 && n.business_category !== 'Support').forEach(n => incidents.push({
    priority: 2, label: 'P2', labelColor: '#2563EB', wash: '#EFF6FF',
    title: `${n.business_name} — Weak Defenses`,
    status: 'Monitoring',
    impact: `Defense ${n.defense}/10`,
    positive: false,
    reporter: '@CISO',
    flowRef: null,
  }))
  flows.filter(f => f.risk_level === 'high').forEach(f => incidents.push({
    priority: 2, label: 'P2', labelColor: '#2563EB', wash: '#EFF6FF',
    title: `Revenue Stream '${f.name}' At Risk`,
    status: 'Monitoring',
    impact: `€${f.current_revenue}K/turn`,
    positive: false,
    reporter: '@SRE-Team',
    flowRef: f.node_path,
  }))

  incidents.sort((a, b) => a.priority - b.priority)
  return incidents
}
