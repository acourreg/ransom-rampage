import { useState, useMemo } from 'react'
import { computeLayout } from '../utils/layout.js'

const NODE_W = 140, NODE_H = 70
const SVG_W = 800, SVG_H = 420

const TYPE_ICONS = {
  entry: '🌐', database: '🗄️', server: '🖥️',
  middleware: '⚙️', human: '👤', vendor: '🔗'
}

function getNodeStatus(node) {
  if (node.fogged)      return { border: '#CBD5E1', badge: '🔍 Unknown' }
  if (node.compromised) return { border: '#EF4444', badge: '🔴 Anomaly' }
  if (node.locked)      return { border: '#EF4444', badge: '🔒 Locked' }
  if (node.offline)     return { border: '#94A3B8', badge: '⚫ Offline' }
  if (node.isolated)    return { border: '#F59E0B', badge: '🔶 Isolated' }
  return                       { border: '#10B981', badge: '✅ Healthy' }
}

function getNodeDisplayInfo(node) {
  if (node.fogged || node.business_category === 'Unknown') {
    return { subtitle: '🔍 Unknown', detail: null, accent: '#CBD5E1' }
  }
  switch (node.business_category) {
    case 'Revenue Critical':
      return {
        subtitle: `€${node.revenue_exposure}K/turn`,
        detail: node.flows_supported?.join(', '),
        accent: '#10B981',
      }
    case 'Operations':
      return {
        subtitle: `Throughput ${node.throughput}/10 · €${node.cost * 5}K/turn`,
        detail: `Defense ${node.defense}/10`,
        accent: '#2563EB',
      }
    case 'External Dependency':
      return {
        subtitle: `Visibility ${node.visibility}/10`,
        detail: `Defense ${node.defense}/10`,
        accent: '#F59E0B',
      }
    case 'People & Access':
      return {
        subtitle: `Defense ${node.defense}/10 ${node.has_mfa ? '🔐 MFA' : '⚠ No MFA'}`,
        detail: node.compromised ? '🔴 Account compromised' : null,
        accent: '#F59E0B',
      }
    case 'Support':
      return { subtitle: `€${node.cost * 5}K/turn cost`, detail: null, accent: '#94A3B8' }
    default:
      return { subtitle: node.type, detail: null, accent: '#CBD5E1' }
  }
}

export default function InfraGraph({ nodes, edges, selectingTarget, onNodeSelect }) {
  const [selectedNode, setSelectedNode] = useState(null)
  const laidOut = useMemo(() => computeLayout(nodes, SVG_W, SVG_H), [nodes])
  const nodeMap = useMemo(() => Object.fromEntries(laidOut.map(n => [n.id, n])), [laidOut])

  function handleNodeClick(node) {
    setSelectedNode(selectedNode?.id === node.id ? null : node)
    if (selectingTarget) onNodeSelect(node)
  }

  return (
    <div style={{ background: '#FFFFFF', borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.1)', padding: 16, position: 'relative' }}>
      <svg width={SVG_W} height={SVG_H} onClick={e => { if (e.target.tagName === 'svg') setSelectedNode(null) }}>
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#CBD5E1" />
          </marker>
        </defs>

        {/* EDGES */}
        {edges.map((e, i) => {
          const from = nodeMap[e.from], to = nodeMap[e.to]
          if (!from || !to) return null
          return (
            <line key={i}
              x1={from.x + NODE_W} y1={from.y + NODE_H / 2}
              x2={to.x}            y2={to.y + NODE_H / 2}
              stroke="#CBD5E1" strokeWidth={2}
              markerEnd="url(#arrow)"
            />
          )
        })}

        {/* NODES */}
        {laidOut.map(n => {
          const { accent } = getNodeDisplayInfo(n)
          const { subtitle, detail } = getNodeDisplayInfo(n)
          const isSelected = selectedNode?.id === n.id
          const borderColor = (n.compromised || n.locked) ? '#EF4444'
            : n.offline ? '#94A3B8'
            : n.isolated ? '#F59E0B'
            : accent
          return (
            <g key={n.id} onClick={() => handleNodeClick(n)} style={{ cursor: 'pointer' }}>
              <rect
                x={n.x} y={n.y} width={NODE_W} height={NODE_H} rx={8}
                fill="#FFFFFF"
                stroke={selectingTarget ? '#2563EB' : isSelected ? '#2563EB' : borderColor}
                strokeWidth={isSelected || selectingTarget ? 3 : 2}
              />
              <text x={n.x + 12} y={n.y + 28} fontSize={18}>{TYPE_ICONS[n.type] ?? '📦'}</text>
              <text x={n.x + 38} y={n.y + 22} fontSize={11} fontFamily="Inter" fontWeight={600} fill="#0F172A">
                {(n.business_name || n.name).slice(0, 16)}
              </text>
              <text x={n.x + 10} y={n.y + 40} fontSize={9} fontFamily="Inter" fill="#64748B">
                {subtitle}
              </text>
              {detail && (
                <text x={n.x + 10} y={n.y + 54} fontSize={8} fontFamily="Inter" fill="#94A3B8">
                  {detail.slice(0, 22)}
                </text>
              )}
              {(n.compromised || n.locked || n.offline || n.isolated) && (
                <text x={n.x + 105} y={n.y + 14} fontSize={9} fill={borderColor}>
                  {n.compromised ? '🔴' : n.locked ? '🔒' : n.offline ? '⚫' : '🔶'}
                </text>
              )}
            </g>
          )
        })}
      </svg>

      {/* TOOLTIP — positioned absolute over SVG */}
      {selectedNode && !selectingTarget && (() => {
        const n = nodeMap[selectedNode.id]
        if (!n) return null
        const { border, badge } = getNodeStatus(n)
        const tipX = n.x + NODE_W + 8, tipY = n.y
        return (
          <div style={{
            position: 'absolute', left: tipX + 16, top: tipY,
            background: '#FFFFFF', border: '1px solid #E2E8F0',
            borderRadius: 8, padding: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            minWidth: 200, fontFamily: 'Inter', fontSize: 12, zIndex: 10
          }}>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>{n.business_name}</div>
            <div style={{ fontSize: 10, color: '#64748B', marginBottom: 8 }}>
              {n.business_category} · {n.name}
            </div>
            {[['Throughput', n.throughput], ['Defense', n.defense],
              ['Visibility', n.visibility], ['Cost', n.cost], ['Compliance', n.compliance_score]
            ].map(([label, val]) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                <span style={{ color: '#64748B' }}>{label}</span>
                <span style={{ fontFamily: 'JetBrains Mono', color: val === '???' ? '#94A3B8' : '#0F172A' }}>{val}</span>
              </div>
            ))}
            {!n.fogged && <>
              <div style={{ borderTop: '1px solid #E2E8F0', margin: '8px 0' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                <span style={{ color: '#64748B' }}>Revenue exposure</span>
                <span style={{ fontFamily: 'JetBrains Mono', color: '#10B981' }}>€{n.revenue_exposure}K/turn</span>
              </div>
              {n.flows_supported?.length > 0 && (
                <div style={{ fontSize: 10, color: '#94A3B8', marginTop: 4 }}>
                  Flows: {n.flows_supported.join(', ')}
                </div>
              )}
            </>}
          </div>
        )
      })()}
    </div>
  )
}
