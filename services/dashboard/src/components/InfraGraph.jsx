import { useState, useMemo } from 'react'
import { computeLayout, hexPoints } from '../utils/layout.js'

const TYPE_COL = { entry: 0, human: 1, vendor: 1, middleware: 2, server: 2, database: 3 }

const NODE_ICONS = {
  entry:      '/assets/icons/entry.png',
  database:   '/assets/icons/database.png',
  server:     '/assets/icons/server.png',
  middleware: '/assets/icons/middleware.png',
  human:      '/assets/icons/human.png',
  vendor:     '/assets/icons/vendor.png',
}
const WILDCARD = '/assets/icons/wildcard.png'

const TYPE_EMOJI = {
  entry: '🌐', database: '🗄️', server: '🖥️',
  middleware: '⚙️', human: '👤', vendor: '🔗'
}

function getNodeDisplayInfo(node) {
  if (node.fogged || node.business_category === 'Unknown') {
    return { subtitle: null, accent: '#6B7280' }
  }
  switch (node.business_category) {
    case 'Revenue Critical':
      return { subtitle: `€${node.revenue_exposure}K/turn`, accent: '#10B981' }
    case 'Operations':
      return { subtitle: `Throughput ${node.throughput}/10`, accent: '#38BDF8' }
    case 'People & Access':
      return { subtitle: `Def ${node.defense}/10${node.has_mfa ? ' 🔐' : ' ⚠'}`, accent: '#F59E0B' }
    case 'External Dependency':
      return { subtitle: `Vis ${node.visibility}/10`, accent: '#F59E0B' }
    case 'Support':
      return { subtitle: `€${node.cost * 5}K/turn`, accent: '#9CA3AF' }
    default:
      return { subtitle: node.type, accent: '#9CA3AF' }
  }
}

function scoreToLabel(metric, val) {
  if (val === undefined || val === null || val === '???') return { label: '???', color: '#94A3B8' }
  const n = Number(val)
  if (metric === 'Cost') {
    if (n <= 3) return { label: 'Low',      color: '#10B981' }
    if (n <= 6) return { label: 'Moderate', color: '#F59E0B' }
    return             { label: 'High',     color: '#EF4444' }
  }
  const labels = {
    Throughput:  [,'Minimal','Low','Low','Moderate','Moderate','Moderate','Fast','Fast','High','Max'],
    Defense:     [,'Exposed','Weak','Weak','Minimal','Moderate','Moderate','Strong','Strong','Fortified','Max'],
    Visibility:  [,'Blind','Blind','Low','Low','Partial','Partial','Clear','Clear','Full','Full'],
    Compliance:  [,'None','At Risk','At Risk','Low','Partial','Partial','Good','Good','Compliant','Certified'],
  }
  const label = labels[metric]?.[n] ?? (n <= 3 ? 'Low' : n <= 6 ? 'Moderate' : 'High')
  const color = n <= 3 ? '#EF4444' : n <= 6 ? '#F59E0B' : '#10B981'
  return { label, color }
}

function getStatusRing(node) {
  if (node.compromised) return { stroke: '#EF4444', width: 4, glow: true,  pulse: true  }
  if (node.locked)      return { stroke: '#EF4444', width: 3, glow: false, pulse: false }
  if (node.offline)     return { stroke: '#6B7280', width: 2, glow: false, pulse: false }
  if (node.isolated)    return { stroke: '#F59E0B', width: 2, glow: false, pulse: false }
  return null
}

export default function InfraGraph({
  nodes, edges, vulnerabilities, selectingTarget, highlightedFlow, onNodeSelect, onDeselect
}) {
  const [selectedNode, setSelectedNode] = useState(null)

  const knownVulnNodeIds = useMemo(() => new Set(
    (vulnerabilities ?? []).filter(v => v.known_by_player).map(v => v.node_id)
  ), [vulnerabilities])

  const colGroups = nodes.reduce((acc, n) => {
    const col = TYPE_COL[n.type] ?? 2
    acc[col] = (acc[col] ?? 0) + 1
    return acc
  }, {})
  const maxNodesInCol = Math.max(1, ...Object.values(colGroups))
  const colCount = Object.keys(colGroups).length
  const SVG_W = Math.max(480, colCount * 140 + 80)
  const SVG_H = Math.max(320, maxNodesInCol * 130 + 80)

  const statusKey = nodes.map(n =>
    `${n.id}:${n.compromised}:${n.locked}:${n.offline}:${n.fogged}:${n.isolated}:${n.defense}:${n.throughput}`
  ).join('|')

  const laidOut = useMemo(
    () => computeLayout(nodes, SVG_W, SVG_H),
    [statusKey, nodes.length, SVG_W, SVG_H]
  )
  const nodeMap = useMemo(() => Object.fromEntries(laidOut.map(n => [n.id, n])), [laidOut])

  const highlightSet = new Set(highlightedFlow ?? [])

  function handleNodeClick(e, node) {
    e.stopPropagation()
    const next = selectedNode?.id === node.id ? null : node
    setSelectedNode(next)
    onNodeSelect(next ?? node)
  }

  function handleBgClick() {
    setSelectedNode(null)
    onDeselect?.()
  }

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <style>{`
        @keyframes pulse-ring {
          0%,100% { opacity:1; transform-origin:center; transform:scale(1); }
          50%      { opacity:0.5; transform:scale(1.04); }
        }
        @keyframes hex-select {
          0%,100% { opacity:0.5; } 50% { opacity:1; }
        }
      `}</style>

      <svg
        key={statusKey}
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        style={{ width: '100%', height: 'auto', display: 'block', cursor: 'default' }}
        onClick={handleBgClick}
      >
        <defs>
          <marker id="arr" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">
            <polygon points="0 0, 10 4, 0 8" fill="#94A3B8" />
          </marker>
          <marker id="arr-hl" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">
            <polygon points="0 0, 10 4, 0 8" fill="#10B981" />
          </marker>
          <filter id="glow-red" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="4" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
          <filter id="glow-select" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>

        {/* EDGES */}
        {edges.map((e, i) => {
          const f = nodeMap[e.from], t = nodeMap[e.to]
          if (!f || !t) return null
          const hl = highlightSet.has(e.from) && highlightSet.has(e.to)
          return (
            <line key={i}
              x1={f.cx} y1={f.cy} x2={t.cx} y2={t.cy}
              stroke={hl ? '#10B981' : '#94A3B8'}
              strokeWidth={hl ? 3 : 2.5}
              opacity={hl ? 1 : 0.8}
              markerEnd={hl ? 'url(#arr-hl)' : 'url(#arr)'}
            />
          )
        })}

        {/* NODES */}
        {laidOut.map(n => {
          const { subtitle, accent } = getNodeDisplayInfo(n)
          const status = getStatusRing(n)
          const isSelected = selectedNode?.id === n.id
          const R = n.r
          const pts = hexPoints(n.cx, n.cy, R)
          const imgSize = R * 1.65
          const imgOffset = imgSize / 2
          const icon = NODE_ICONS[n.type] ?? WILDCARD
          const emoji = TYPE_EMOJI[n.type]

          return (
            <g key={n.id}
              onClick={e => handleNodeClick(e, n)}
              style={{ cursor: selectingTarget ? 'crosshair' : 'pointer' }}
            >
              {/* selectingTarget hover ring */}
              {selectingTarget && (
                <polygon
                  points={pts}
                  fill="rgba(37,99,235,0.08)"
                  stroke="#2563EB" strokeWidth={1.5}
                  strokeDasharray="4 3"
                />
              )}

              {/* Clip path for image */}
              <clipPath id={`clip-${n.id}`}>
                <polygon points={pts} />
              </clipPath>

              {/* Node image */}
              <image
                href={icon}
                x={n.cx - imgOffset} y={n.cy - imgOffset}
                width={imgSize} height={imgSize}
                clipPath={`url(#clip-${n.id})`}
                opacity={n.offline ? 0.25 : n.fogged ? 0.35 : 1}
                style={{ pointerEvents: 'none' }}
              />

              {/* Bad state tint overlay — over image, clipped to hex */}
              {!n.fogged && (n.compromised || n.locked) && (
                <polygon points={pts} fill="#EF4444" opacity={0.18} style={{ pointerEvents: 'none' }} />
              )}
              {!n.fogged && n.isolated && (
                <polygon points={pts} fill="#F59E0B" opacity={0.15} style={{ pointerEvents: 'none' }} />
              )}
              {!n.fogged && n.offline && (
                <polygon points={pts} fill="#64748B" opacity={0.35} style={{ pointerEvents: 'none' }} />
              )}

              {/* Status ring — small inset indicator for node health */}
              {status && (
                <polygon
                  points={hexPoints(n.cx, n.cy, R - 15)}
                  fill="none"
                  stroke={status.stroke}
                  strokeWidth={status.width}
                  filter={status.glow ? 'url(#glow-red)' : 'none'}
                  style={status.pulse ? { animation: 'pulse-ring 1.1s ease-in-out infinite' } : {}}
                />
              )}

              {/* Selected glow ring — outer ring around hex */}
              {isSelected && (
                <polygon
                  points={hexPoints(n.cx, n.cy, R - 13)}
                  fill="none" stroke="#2563EB" strokeWidth={1.5}
                  opacity={0.7}
                  filter="url(#glow-select)"
                  style={{ animation: 'hex-select 1.5s ease-in-out infinite' }}
                />
              )}

              {/* Fogged overlay */}
              {n.fogged && <>
                <polygon points={hexPoints(n.cx, n.cy, R - 15)} fill="#9CA3AF" opacity={0.5} style={{ pointerEvents: 'none' }} />
                <image
                  href={WILDCARD}
                  x={n.cx - imgOffset} y={n.cy - imgOffset}
                  width={imgSize} height={imgSize}
                  clipPath={`url(#clip-${n.id})`}
                  opacity={0.3}
                  style={{ pointerEvents: 'none' }}
                />
                {/* Known type → "?" (not yet scanned). Wildcard type → emoji */}
                {NODE_ICONS[n.type] ? (
                  <text x={n.cx} y={n.cy}
                    textAnchor="middle" dominantBaseline="middle"
                    fontSize={32} fill="#F9FAFB" fontWeight={700}
                    style={{ pointerEvents: 'none' }}>
                    ?
                  </text>
                ) : (emoji && (
                  <text x={n.cx} y={n.cy - 5}
                    textAnchor="middle" dominantBaseline="middle"
                    fontSize={32}
                    style={{ pointerEvents: 'none' }}>
                    {emoji}
                  </text>
                ))}
              </>}

              {/* Status badges */}
              {n.compromised && !n.fogged && (
                <text x={n.cx + R * 0.5} y={n.cy - R * 0.75}
                  fontSize={8} fontFamily="Inter" fontWeight={700}
                  fill="#EF4444" textAnchor="middle"
                  style={{ pointerEvents: 'none' }}>
                  AT RISK
                </text>
              )}
              {n.locked && (
                <text x={n.cx + R * 0.55} y={n.cy - R * 0.6}
                  fontSize={14} textAnchor="middle"
                  style={{ pointerEvents: 'none' }}>🔒</text>
              )}
              {!n.fogged && !n.compromised && !n.offline && (n.defense ?? 0) >= 8 && (
                <text x={n.cx} y={n.cy - R * 0.72}
                  fontSize={8} fontFamily="Inter" fontWeight={700}
                  fill="#10B981" textAnchor="middle"
                  style={{ pointerEvents: 'none' }}>
                  FORTIFIED
                </text>
              )}
              {knownVulnNodeIds.has(n.id) && !n.fogged && (
                <text
                  x={n.cx + R * 0.55} y={n.cy - R * 0.7}
                  fontSize={13} textAnchor="middle"
                  style={{ pointerEvents: 'none' }}>
                  ⚠️
                </text>
              )}

              {/* Label pill background */}
              <rect
                x={n.cx - 58} y={n.cy + R - 12}
                width={116} height={25} rx={3}
                fill="rgba(15,23,42,0.55)"
                style={{ pointerEvents: 'none' }}
              />
              <text x={n.cx} y={n.cy + R - 1}
                fontSize={7} fontFamily="Inter" fontWeight={600}
                fill="#F1F5F9" textAnchor="middle"
                style={{ pointerEvents: 'none' }}>
                {(n.business_name || n.name).slice(0, 22)}
              </text>
              {subtitle && (
                <text x={n.cx} y={n.cy + R + 9}
                  fontSize={7.5} fontFamily="Inter"
                  fill={accent} textAnchor="middle"
                  style={{ pointerEvents: 'none' }}>
                  {subtitle}
                </text>
              )}

              {/* Category border when healthy */}
              {!status && (
                <polygon points={hexPoints(n.cx, n.cy, R - 15)}
                  fill="none"
                  stroke={accent}
                  strokeWidth={2}
                  opacity={0.6}
                  style={{ pointerEvents: 'none' }}
                />
              )}

              {/* Transparent click catcher — must be last */}
              <polygon
                points={pts}
                fill="transparent"
                stroke="none"
                style={{ cursor: selectingTarget ? 'crosshair' : 'pointer' }}
              />
            </g>
          )
        })}
      </svg>

      {/* TOOLTIP */}
      {selectedNode && (() => {
        const n = nodeMap[selectedNode.id]
        if (!n) return null
        const leftPct = Math.min(72, (n.cx / SVG_W) * 100 + 2)
        const topPct = Math.max(2, (n.cy / SVG_H) * 100 - 8)
        return (
          <div style={{
            position: 'absolute',
            left: `${leftPct}%`,
            top: `${topPct}%`,
            background: '#FFFFFF',
            border: '1px solid #E2E8F0',
            borderRadius: 8, padding: '12px 14px',
            boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
            minWidth: 210, maxWidth: 260,
            fontFamily: 'Inter', fontSize: 12,
            color: '#0F172A', zIndex: 20,
          }}>
            <div style={{ fontWeight: 700, marginBottom: 3 }}>{n.business_name}</div>
            <div style={{ fontSize: 10, color: '#64748B', marginBottom: 8 }}>
              {n.business_category} · {n.name}
            </div>
            {[
              ['Throughput',  n.throughput],
              ['Defense',     n.defense],
              ['Visibility',  n.visibility],
              ['Cost',        n.cost],
              ['Compliance',  n.compliance_score],
            ].map(([label, val]) => {
              const { label: qlabel, color } = scoreToLabel(label, val)
              return (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                  <span style={{ color: '#64748B' }}>{label}</span>
                  <span style={{ fontFamily: 'JetBrains Mono', fontSize: 11, color }}>{qlabel}</span>
                </div>
              )
            })}
            {!n.fogged && <>
              <div style={{ borderTop: '1px solid #E2E8F0', margin: '8px 0' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                <span style={{ color: '#64748B' }}>Revenue exposure</span>
                <span style={{ fontFamily: 'JetBrains Mono', color: '#10B981' }}>€{n.revenue_exposure}K/turn</span>
              </div>
              {n.flows_supported?.length > 0 && (
                <div style={{ fontSize: 10, color: '#94A3B8', marginTop: 4 }}>
                  {n.flows_supported.join(', ')}
                </div>
              )}
              {(vulnerabilities ?? []).filter(v => v.node_id === n.id && v.known_by_player).map((v, i) => (
                <div key={i} style={{
                  marginTop: 6, padding: '4px 8px',
                  background: '#FEF9C3', borderRadius: 4,
                  fontSize: 10, color: '#92400E',
                }}>
                  ⚠️ Known vuln (sev {v.severity}/3): {v.description}
                </div>
              ))}
            </>}
          </div>
        )
      })()}
    </div>
  )
}
