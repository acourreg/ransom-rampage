import { useState, useEffect, useRef } from 'react'

const CTO_ACTIONS = [
  { id:'C0', label:'Scan Node',        cost:50,  targetRequired: true,  desc: 'Reveals vulnerabilities + removes fog on target node. Required before Patch.' },
  { id:'C1', label:'Report Breach',    cost:20,  targetRequired: false, desc: 'Reset breach timer. Avoids regulatory fine. −5% reputation.' },
  { id:'C2', label:'Boost Throughput', cost:25,  targetRequired: true,  desc: 'throughput +2 on target. Immediate revenue lift on bottleneck nodes.' },
  { id:'C3', label:'Patch Vuln',       cost:30,  targetRequired: true,  desc: '⚠ Node goes OFFLINE 1 turn. Removes 1 known vuln. Does NOT increase defense — use Reinforce (C7) for that.' },
  { id:'C4', label:'Cut Costs',        cost:15,  targetRequired: true,  desc: 'cost −1 permanently. Reduces burn rate. Best on high-cost idle nodes.' },
  { id:'C5', label:'Evict Attacker',   cost:30,  targetRequired: true,  desc: 'Clear compromised flag + lateral nodes. Follow up with Reinforce (C7) to block re-entry.' },
  { id:'C6', label:'Pay Ransom',       cost:200, targetRequired: true,  desc: 'Unlock encrypted node instantly. Expensive. −10% reputation.' },
  { id:'C7', label:'Reinforce',        cost:35,  targetRequired: true,  desc: 'Defense +2 on target. Stack to reach defense ≥ 6 to block Byte B1 entry.' },
  { id:'C8', label:'Deploy MFA',       cost:40,  targetRequired: true,  desc: 'has_mfa=true, defense +2. Best on human/entry nodes. One-time only.' },
  { id:'C9', label:'Do Nothing',       cost:0,   targetRequired: false, desc: 'Fog spreads +1 node. Byte acts freely. Only if budget is critical.' },
]

// Which targeted actions make sense per node type
const TYPE_ACTIONS = {
  entry:      new Set(['C0', 'C2', 'C3', 'C4', 'C5', 'C7', 'C8']),
  human:      new Set(['C0', 'C2', 'C5', 'C7', 'C8']),
  vendor:     new Set(['C0', 'C3', 'C4', 'C5', 'C7']),
  database:   new Set(['C0', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7']),
  server:     new Set(['C0', 'C2', 'C3', 'C4', 'C5', 'C7']),
  middleware: new Set(['C0', 'C2', 'C3', 'C4', 'C5', 'C7']),
}

function getActionDisabledReason(action, node, vulnerabilities) {
  if (!node) return null
  switch (action.id) {
    case 'C0': {
      if (!node.fogged && !(vulnerabilities ?? []).some(v => v.node_id === node.id && !v.known_by_player))
        return 'Node already scanned — nothing to reveal'
      break
    }
    case 'C2':
      if ((node.throughput ?? 0) >= 10) return 'Throughput already maxed'
      break
    case 'C3': {
      const hasKnownVuln = (vulnerabilities ?? []).some(v => v.node_id === node.id && v.known_by_player)
      if (!hasKnownVuln) return 'No known vulnerability — use Scan first'
      if (node.offline) return 'Node already offline'
      break
    }
    case 'C4': if ((node.cost ?? 0) <= 1) return 'Cost already at minimum'
      break
    case 'C5': if (!node.compromised) return 'Node not compromised'
      break
    case 'C6': if (!node.locked) return 'Node not locked (not ransomed)'
      break
    case 'C7': if ((node.defense ?? 0) >= 9) return 'Defense already maxed'
      break
    case 'C8':
      if (node.has_mfa) return 'MFA already deployed'
      if (typeof node.defense === 'number' && node.defense >= 9) return 'Defense already maxed'
      break
  }
  return null
}

function isBottleneckOnActiveFlow(node, gameState) {
  if (!node || !gameState?.flows || !gameState?.nodes) return false
  return gameState.flows.some(f =>
    f.is_active &&
    f.node_path?.includes(node.id) &&
    f.node_path.every(nid => {
      const n = gameState.nodes.find(x => x.id === nid)
      return !n || (n.throughput ?? 10) >= (node.throughput ?? 10)
    })
  )
}

const PARADIGM_IDS = new Set(['S2', 'S4', 'S5', 'S6', 'E3', 'E4', 'E5', 'E6'])
const AUDIT_EXEMPT_CTO = new Set(['C1', 'C5', 'C7'])

export default function StrategyPanel({
  advisorRecs, gameState, selectedActions, selectedTarget,
  selectingTarget, loading, turn, maxTurns, forceAudit, vulnerabilities,
  onSelectAdvisor, onSelectCto, onCommit, onStartTargetSelect
}) {
  const cash = gameState?.company?.cash ?? 0
  const targetType = selectedTarget?.type

  const currentNodeAction = selectedActions.find(a => a.source === 'cto' && a.resolvedTarget === selectedTarget?.id) ?? null
  const globalAction      = selectedActions.find(a => a.source === 'cto' && !a.resolvedTarget) ?? null
  const hasCtoQueued      = selectedActions.some(a => a.source === 'cto')
  const hasAdvisorQueued  = selectedActions.some(a => a.source === 'ciso' || a.source === 'sre')

  const canCommit = !loading && selectedActions.length > 0

  const [activeTab, setActiveTab] = useState('advisors')
  const [hoveredAction, setHoveredAction] = useState(null)
  const prevTargetRef = useRef(null)

  useEffect(() => {
    if (selectedTarget && !prevTargetRef.current) {
      setActiveTab('actions')
    } else if (!selectedTarget && prevTargetRef.current && !hasCtoQueued) {
      setActiveTab('advisors')
    }
    prevTargetRef.current = selectedTarget
  }, [selectedTarget, hasCtoQueued])

  return (
    <div style={{
      width: 440, flexShrink: 0, background: '#FFFFFF',
      borderLeft: '1px solid #E2E8F0', display: 'flex',
      flexDirection: 'column', overflow: 'hidden'
    }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>

        {/* TAB HEADERS */}
        <div style={{ display: 'flex', borderBottom: '1px solid #E2E8F0', marginBottom: 12 }}>
          {[
            { id: 'advisors', label: '🤖 Advisors' },
            { id: 'actions',  label: '🎮 CTO Actions' },
          ].map(tab => (
            <button key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                flex: 1, padding: '10px 0', border: 'none', background: 'none',
                fontFamily: 'Inter', fontWeight: 600, fontSize: 12,
                color: activeTab === tab.id ? '#2563EB' : '#94A3B8',
                borderBottom: activeTab === tab.id ? '2px solid #2563EB' : '2px solid transparent',
                cursor: 'pointer', transition: 'all 0.15s',
              }}
            >
              {tab.label}
              {tab.id === 'actions' && hasCtoQueued && (
                <span style={{
                  marginLeft: 6, background: '#2563EB', color: '#fff',
                  borderRadius: 10, padding: '1px 6px', fontSize: 9
                }}>{selectedActions.filter(a => a.source === 'cto').length}</span>
              )}
              {tab.id === 'advisors' && hasAdvisorQueued && (
                <span style={{
                  marginLeft: 6, background: '#10B981', color: '#fff',
                  borderRadius: 10, padding: '1px 6px', fontSize: 9
                }}>1</span>
              )}
            </button>
          ))}
        </div>

        {/* TAB CONTENT — ADVISORS */}
        {activeTab === 'advisors' && (
          <div>
            {['ciso', 'sre'].map(role => {
              const rec = advisorRecs?.[role]
              const accentColor = role === 'ciso' ? '#2563EB' : '#10B981'
              const icon = role === 'ciso' ? '🛡' : '⚙️'
              if (!rec) return (
                <div key={role} style={{ ...advisorCard, borderLeft: `20px solid ${accentColor}`, padding: '14px 14px 14px 16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                    <img
                      src={role === 'ciso' ? '/assets/avatars/ciso.png' : '/assets/avatars/sre.png'}
                      width={48} height={48}
                      style={{ borderRadius: '50%', border: `2px solid ${accentColor}`, objectFit: 'cover', flexShrink: 0 }}
                      onError={e => { e.target.style.display = 'none' }}
                    />
                    <div>
                      <div style={{ fontFamily: 'Inter', fontSize: 10, fontWeight: 600, color: accentColor, textTransform: 'uppercase', letterSpacing: 1 }}>
                        {role === 'ciso' ? 'CISO' : 'SRE'}
                      </div>
                      <div style={{ fontFamily: 'Inter', fontSize: 12, color: '#94A3B8' }}>Deliberating...</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center', paddingLeft: 4 }}>
                    {[0, 1, 2].map(i => (
                      <div key={i} style={{
                        width: 8, height: 8, borderRadius: '50%', background: accentColor,
                        animation: 'dotPulse 1.2s ease-in-out infinite',
                        animationDelay: `${i * 0.2}s`
                      }} />
                    ))}
                  </div>
                  <style>{`@keyframes dotPulse {
                    0%,80%,100% { opacity:0.3; transform:scale(0.8); }
                    40% { opacity:1; transform:scale(1.2); }
                  }`}</style>
                </div>
              )
              const isSelected = selectedActions.some(a => a.source === role && a.id === rec.action_id)
              const isPolicy = !!rec.policy_id
              const policyBg = isSelected ? '#EFF6FF' : isPolicy
                ? (role === 'ciso' ? '#F5F3FF' : '#F0FDF4')
                : '#FFFFFF'
              const barWidth = isPolicy ? 24 : 20
              const barStyle = isPolicy
                ? { borderLeft: 'none', borderImage: role === 'ciso'
                    ? 'linear-gradient(180deg, #7C3AED, #2563EB) 1'
                    : 'linear-gradient(180deg, #10B981, #059669) 1',
                  borderImageSlice: 1, borderLeftWidth: barWidth, borderLeftStyle: 'solid' }
                : { borderLeft: `${barWidth}px solid ${accentColor}` }
              return (
                <div key={role} style={{
                  ...advisorCard,
                  ...barStyle,
                  padding: '14px 14px 14px 16px',
                  background: policyBg,
                  outline: isSelected ? `2px solid ${accentColor}` : 'none'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                    <img
                      src={role === 'ciso' ? '/assets/avatars/ciso.png' : '/assets/avatars/sre.png'}
                      width={48} height={48}
                      style={{ borderRadius: '50%', border: `2px solid ${accentColor}`, objectFit: 'cover', flexShrink: 0 }}
                      onError={e => { e.target.style.display = 'none' }}
                    />
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontFamily: 'Inter', fontSize: 10, fontWeight: 600, color: accentColor, textTransform: 'uppercase', letterSpacing: 1 }}>
                          {role === 'ciso' ? 'CISO' : 'SRE'}
                        </span>
                        {isPolicy && (
                          <span style={{
                            background: '#7C3AED', color: '#FFFFFF',
                            borderRadius: 10, padding: '2px 7px',
                            fontSize: 9, fontWeight: 700, letterSpacing: 0.5,
                            whiteSpace: 'nowrap',
                          }}>⚡ POLICY</span>
                        )}
                      </div>
                      <span style={{ fontFamily: 'Inter', fontWeight: 700, fontSize: 13, color: '#0F172A', lineHeight: 1.2 }}>
                        {rec.action_label}
                      </span>
                    </div>
                  </div>
                  {isPolicy && rec.cto_pitch && (
                    <div style={{
                      fontFamily: 'Inter', fontSize: 11, color: '#334155',
                      fontStyle: 'italic', marginBottom: 8,
                      borderLeft: '3px solid #E2E8F0', paddingLeft: 10, lineHeight: 1.5,
                    }}>
                      "{rec.cto_pitch}"
                    </div>
                  )}
                  <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 8 }}>
                    <tbody>
                    {[
                      ['Cost',     `€${rec.cost}K`],
                      ['Duration', isPolicy && rec.duration_turns ? `${rec.duration_turns} turns` : '1 Turn'],
                      ['Benefit',  rec.cto_pitch && isPolicy ? null : rec.action_description],
                      ['Risk',     rec.revenue_impact],
                    ].filter(([, val]) => val != null).map(([label, val]) => (
                      <tr key={label}>
                        <td style={{ fontFamily: 'Inter', fontSize: 10, color: '#94A3B8', paddingBottom: 3, width: 55 }}>{label}</td>
                        <td style={{ fontFamily: label === 'Cost' ? 'JetBrains Mono' : 'Inter', fontSize: 10, color: '#0F172A', paddingBottom: 3 }}>{val}</td>
                      </tr>
                    ))}
                    </tbody>
                  </table>
                  <button
                    onClick={() => isSelected
                      ? onSelectAdvisor(null)
                      : onSelectAdvisor({ id: rec.action_id, label: rec.action_label, cost: rec.cost, target: rec.target, source: role, targetNode: gameState?.nodes?.find(n => n.id === rec.target) })
                    }
                    style={{
                      width: '100%', padding: '6px', borderRadius: 6, border: `1px solid ${accentColor}`,
                      background: isSelected ? accentColor : '#FFFFFF',
                      color: isSelected ? '#FFFFFF' : accentColor,
                      fontFamily: 'Inter', fontWeight: 600, fontSize: 12, cursor: 'pointer'
                    }}
                  >
                    {isSelected ? '✓ Selected' : 'Accept'}
                  </button>
                </div>
              )
            })}
          </div>
        )}

        {/* TAB CONTENT — CTO ACTIONS */}
        {activeTab === 'actions' && (
          <div>
            {/* Target selection feedback */}
            {selectingTarget && (
              <div style={{
                marginBottom: 12, padding: '8px 12px', background: '#EFF6FF',
                border: '1px solid #2563EB', borderRadius: 6,
                fontFamily: 'Inter', fontSize: 11, color: '#2563EB'
              }}>
                🎯 Click a node on the map to select target...
              </div>
            )}
            {selectedTarget && !selectingTarget && (
              <div style={{
                marginBottom: 12, padding: '8px 12px',
                background: currentNodeAction ? '#F0FDF4' : '#F8FAFC',
                border: `1px solid ${currentNodeAction ? '#10B981' : '#E2E8F0'}`,
                borderRadius: 6, fontFamily: 'Inter', fontSize: 11,
                color: currentNodeAction ? '#10B981' : '#94A3B8'
              }}>
                {currentNodeAction
                  ? `✓ ${selectedTarget.business_name} → ${currentNodeAction.label} (queued)`
                  : `Target: ${selectedTarget.business_name} — pick an action below`}
              </div>
            )}

            {/* Node-specific actions */}
            {targetType ? (
              <>
                <div style={{ fontFamily: 'Inter', fontSize: 10, color: '#64748B', marginBottom: 6, fontWeight: 600 }}>
                  🎯 On {selectedTarget.business_name}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, marginBottom: 8 }}>
                  {CTO_ACTIONS.filter(a => a.targetRequired && TYPE_ACTIONS[targetType]?.has(a.id)).map(action => {
                    const isSelected = selectedActions.some(a => a.id === action.id && a.resolvedTarget === selectedTarget.id)
                    const disabledReason = getActionDisabledReason(action, selectedTarget, vulnerabilities)
                    const isDisabled = loading || action.cost > cash || !!disabledReason
                    return (
                      <button key={action.id} disabled={isDisabled}
                        title={disabledReason ?? action.desc}
                        onMouseEnter={() => setHoveredAction(action)}
                        onMouseLeave={() => setHoveredAction(null)}
                        onClick={() => onSelectCto(
                          isSelected ? null : { id: action.id, label: action.label, cost: action.cost, source: 'cto', targetRequired: true },
                          selectedTarget.id
                        )}
                        style={{ ...actionBtn(isSelected, isDisabled), opacity: disabledReason ? 0.35 : 1 }}
                      >
                        <div>{action.label}</div>
                        <div style={{ fontFamily: 'JetBrains Mono', fontSize: 9, marginTop: 2, color: isSelected ? '#FFFFFF' : '#F59E0B' }}>
                          €{action.cost}K
                        </div>
                      </button>
                    )
                  })}
                </div>
                {hoveredAction && hoveredAction.id === 'C2' && !getActionDisabledReason(hoveredAction, selectedTarget, vulnerabilities) && (
                  <div style={{
                    marginBottom: 8, padding: '6px 10px',
                    background: isBottleneckOnActiveFlow(selectedTarget, gameState) ? '#F0FDF4' : '#FFFBEB',
                    border: `1px solid ${isBottleneckOnActiveFlow(selectedTarget, gameState) ? '#10B981' : '#F59E0B'}`,
                    borderRadius: 6, fontFamily: 'Inter', fontSize: 11,
                    color: isBottleneckOnActiveFlow(selectedTarget, gameState) ? '#059669' : '#92400E',
                  }}>
                    {isBottleneckOnActiveFlow(selectedTarget, gameState)
                      ? `⚡ Bottleneck on active flow — throughput +2 will increase revenue directly.`
                      : `⚠ Not the current bottleneck — revenue won't increase until slower nodes are boosted.`}
                  </div>
                )}
                {hoveredAction && getActionDisabledReason(hoveredAction, selectedTarget, vulnerabilities) && (
                  <div style={{
                    marginBottom: 8, padding: '6px 10px',
                    background: '#FEF2F2', border: '1px solid #EF4444',
                    borderRadius: 6, fontFamily: 'Inter', fontSize: 11, color: '#DC2626',
                  }}>
                    ⛔ {getActionDisabledReason(hoveredAction, selectedTarget, vulnerabilities)}
                  </div>
                )}
              </>
            ) : (
              <div style={{ fontFamily: 'Inter', fontSize: 11, color: '#94A3B8', marginBottom: 10 }}>
                Click a node on the map to see targeted actions
              </div>
            )}

            {/* General actions — always visible */}
            <div style={{ fontFamily: 'Inter', fontSize: 10, color: '#64748B', marginBottom: 6, fontWeight: 600 }}>
              ⚡ General
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
              {CTO_ACTIONS.filter(a => !a.targetRequired).map(action => {
                const isSelected = selectedActions.some(a => a.id === action.id && !a.resolvedTarget)
                const isDisabled = action.cost > cash
                return (
                  <button key={action.id} disabled={isDisabled}
                    onClick={() => onSelectCto(
                      isSelected ? null : { id: action.id, label: action.label, cost: action.cost, source: 'cto', targetRequired: false },
                      '_global'
                    )}
                    style={actionBtn(isSelected, isDisabled)}
                  >
                    <div>{action.label}</div>
                    <div style={{ fontFamily: 'JetBrains Mono', fontSize: 9, marginTop: 2, color: isSelected ? '#FFFFFF' : '#F59E0B' }}>
                      €{action.cost}K
                    </div>
                  </button>
                )
              })}
            </div>

            {/* Selected action description — always shows the latest queued CTO action */}
            {(() => {
              const latestCto = selectedActions.filter(a => a.source === 'cto').at(-1)
              const selectedId = latestCto?.id ?? globalAction?.id
              const action = CTO_ACTIONS.find(a => a.id === selectedId)
              if (!action) return null
              return (
                <div style={{
                  marginTop: 12, padding: '8px 10px',
                  background: '#F8FAFC', border: '1px solid #E2E8F0',
                  borderRadius: 6, borderLeft: '3px solid #2563EB',
                }}>
                  <div style={{ fontFamily: 'Inter', fontSize: 10, fontWeight: 600, color: '#2563EB', marginBottom: 3 }}>
                    {action.label}
                  </div>
                  <div style={{ fontFamily: 'Inter', fontSize: 11, color: '#475569', lineHeight: 1.5 }}>
                    {action.desc}
                  </div>
                </div>
              )
            })()}
          </div>
        )}
      </div>

      {/* COMMIT AREA — queued actions + button */}
      <div style={{ padding: '1rem', borderTop: '1px solid #E2E8F0' }}>
        {selectedActions.length > 0 && (
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 10, color: '#94A3B8', fontFamily: 'Inter', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              Queued ({selectedActions.length})
            </div>
            {selectedActions.map((action, i) => {
              const isAdvisor = action.source === 'ciso' || action.source === 'sre'
              const isBlocked = forceAudit && !isAdvisor && !AUDIT_EXEMPT_CTO.has(action.id)
              const borderColor = isBlocked ? '#EF4444' : action.source === 'sre' ? '#10B981' : '#2563EB'
              const textColor   = isBlocked ? '#EF4444' : action.source === 'sre' ? '#10B981' : '#2563EB'
              const bgColor     = isBlocked ? '#FEF2F2' : action.source === 'sre' ? '#F0FDF4' : '#EFF6FF'
              return (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  background: bgColor, border: `1px solid ${borderColor}`,
                  borderRadius: 6, padding: '6px 10px', marginBottom: 4,
                  fontFamily: 'Inter', fontSize: 11,
                }}>
                  <span style={{ color: textColor, fontWeight: 600 }}>
                    {isBlocked ? '⛔ ' : '▶ '}
                    {action.label}
                    {action.targetNode && (
                      <span style={{ color: '#64748B', fontWeight: 400 }}> → {action.targetNode.business_name}</span>
                    )}
                  </span>
                  <button
                    onClick={() => isAdvisor
                      ? onSelectAdvisor(null)
                      : onSelectCto(null, action.resolvedTarget || '_global')
                    }
                    style={{ background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer', fontSize: 14, lineHeight: 1, padding: '0 2px' }}
                  >×</button>
                </div>
              )
            })}
          </div>
        )}
        <button
          disabled={!canCommit}
          onClick={onCommit}
          style={{
            width: '100%', padding: '12px',
            background: loading ? '#94A3B8' : !canCommit ? '#E2E8F0' : '#2563EB',
            color: !canCommit ? '#94A3B8' : '#FFFFFF',
            border: 'none', borderRadius: 8,
            fontFamily: 'Inter', fontWeight: 700, fontSize: 13,
            cursor: !canCommit ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? '⏳ Agents deliberating...'
            : canCommit ? `COMMIT (Turn ${turn}/${maxTurns ?? 10})`
            : 'Select an action first'}
        </button>
      </div>
    </div>
  )
}

function actionBtn(isSelected, isDisabled) {
  return {
    padding: '8px 4px', borderRadius: 6, border: '1px solid',
    borderColor: isSelected ? '#2563EB' : '#E2E8F0',
    background: isSelected ? '#2563EB' : isDisabled ? '#F8FAFC' : '#FFFFFF',
    color: isSelected ? '#FFFFFF' : isDisabled ? '#94A3B8' : '#0F172A',
    fontFamily: 'Inter', fontSize: 10, fontWeight: 600,
    cursor: isDisabled ? 'not-allowed' : 'pointer',
    textAlign: 'center', lineHeight: 1.3
  }
}

const advisorCard = {
  borderRadius: 8, border: '1px solid #E2E8F0',
  padding: '12px', marginBottom: 10
}
