import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState } from 'react'
import HomePage from './components/HomePage.jsx'
import useGame from './hooks/useGame.js'
import NewGameScreen from './components/NewGameScreen.jsx'
import GameOverModal from './components/GameOverModal.jsx'
import Header from './components/Header.jsx'
import InfraGraph from './components/InfraGraph.jsx'
import TriageBoard from './components/TriageBoard.jsx'
import StrategyPanel from './components/StrategyPanel.jsx'
import WarRoom from './components/WarRoom.jsx'

function GameApp() {
  const {
    sessionId, gameState, advisorRecs,
    loading, error, gameOver, gameOverReason,
    showIntro, dismissIntro,
    startGame, commitTurn, resetGame
  } = useGame()

  // selectedActions: queued actions (max 2 CTO, or 1 advisor that replaces all)
  const [selectedActions, setSelectedActions] = useState([])
  const [selectedTarget, setSelectedTarget]   = useState(null)
  const [selectingTarget, setSelectingTarget] = useState(false)
  const [pendingAction, setPendingAction]     = useState(null)

  function handleNodeSelect(node) {
    if (selectingTarget && pendingAction) {
      // Action-first flow: associate clicked node with the pending queued action
      setSelectedActions(prev => prev.map(a =>
        a.id === pendingAction.id && a.source === 'cto'
          ? { ...a, resolvedTarget: node.id, targetNode: node }
          : a
      ))
      setPendingAction(null)
      setSelectingTarget(false)
    } else if (selectingTarget) {
      setSelectedTarget(node)
      setSelectingTarget(false)
    } else if (node === null) {
      setSelectedTarget(null)
    } else {
      setSelectedTarget(node)
    }
  }

  function handleSelectAdvisor(rec) {
    if (rec === null) {
      setSelectedActions(prev => prev.filter(a => a.source !== 'ciso' && a.source !== 'sre'))
    } else {
      // Keep queued CTO actions — advisor + CTOs coexist and all execute on commit
      setSelectedActions(prev => [...prev.filter(a => a.source === 'cto'), rec])
      setSelectedTarget(null)
      console.log('[ADVISOR ACCEPT]', rec.id, '→', rec.target)
    }
  }

  function handleSelectCto(action, nodeId) {
    if (action === null) {
      setSelectedActions(prev => prev.filter(a => {
        if (a.source !== 'cto') return true
        return nodeId === '_global' ? !!a.resolvedTarget : a.resolvedTarget !== nodeId
      }))
      return
    }
    const withTarget = nodeId === '_global'
      ? action
      : { ...action, resolvedTarget: nodeId, targetNode: gameState?.nodes?.find(n => n.id === nodeId) }

    setSelectedActions(prev => {
      const alreadySelected = prev.some(a =>
        a.id === action.id &&
        (nodeId === '_global' ? !a.resolvedTarget : a.resolvedTarget === nodeId)
      )
      if (alreadySelected) {
        return prev.filter(a => !(a.id === action.id &&
          (nodeId === '_global' ? !a.resolvedTarget : a.resolvedTarget === nodeId)))
      }
      const advisors = prev.filter(a => a.source !== 'cto')
      const ctos = prev.filter(a => a.source === 'cto')
      return [...advisors, ...ctos, withTarget]
    })
  }

  async function handleCommit() {
    if (selectedActions.length === 0) return

    const advisorAction = selectedActions.find(a => a.source === 'ciso' || a.source === 'sre')
    const ctoActions    = selectedActions.filter(a => a.source === 'cto')

    // Advisor present → advisor = primary, CTOs sent as cto_actions
    // No advisor → first CTO = primary, rest sent as cto_actions
    let primaryId, primaryTarget, ctoPayload

    if (advisorAction) {
      primaryId     = advisorAction.id
      primaryTarget = advisorAction.target ?? null
      ctoPayload    = ctoActions.map(a => ({
        action_id: a.id,
        target:    a.resolvedTarget ?? a.target ?? null,
      }))
    } else if (ctoActions.length > 0) {
      const [first, ...rest] = ctoActions
      primaryId     = first.id
      primaryTarget = first.resolvedTarget ?? first.target ?? null
      ctoPayload    = rest.map(a => ({
        action_id: a.id,
        target:    a.resolvedTarget ?? a.target ?? null,
      }))
    } else {
      return
    }

    // Validate all CTO targets
    const unresolved = ctoPayload.find(c => {
      const def = selectedActions.find(a => a.id === c.action_id && a.source === 'cto')
      return def?.targetRequired && !c.target
    })
    if (unresolved) {
      console.warn('[COMMIT] CTO action requires target — not resolved:', unresolved.action_id)
      return
    }

    console.log('[COMMIT] primary:', primaryId, primaryTarget, '| cto:', ctoPayload)
    await commitTurn(primaryId, primaryTarget, ctoPayload)
    setSelectedActions([])
    setPendingAction(null)
    setSelectedTarget(null)
    setSelectingTarget(false)
  }

  function handleReset() {
    resetGame()
    setSelectedActions([])
    setPendingAction(null)
    setSelectedTarget(null)
    setSelectingTarget(false)
  }

  // Pre-game
  if (!sessionId) {
    return <NewGameScreen onGenerate={startGame} loading={loading} />
  }

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100vh', background:'#F8FAFC', overflow:'hidden' }}>
      <Header company={gameState?.company} nodes={gameState?.nodes ?? []} flows={gameState?.flows ?? []} />

      {/* Ticker bar */}
      <TriageBoard gameState={gameState} />

      {error && (
        <div style={{ background:'#FEF2F2', borderBottom:'1px solid #EF4444', padding:'6px 1.5rem', fontFamily:'JetBrains Mono', fontSize:11, color:'#EF4444', flexShrink:0 }}>
          ⚠ Error: {error}
        </div>
      )}

      {/* 2 colonnes : [Graph + WarRoom] + StrategyPanel */}
      <div style={{ display:'flex', flex:1, overflow:'hidden' }}>

        {/* Colonne gauche : graph + incident response empilés */}
        <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
          <div style={{
            flex: 1, padding: '0.25rem 1rem 1rem', overflowY: 'auto', overflowX: 'hidden',
            background: '#F2EDE4',
            backgroundImage: 'linear-gradient(30deg, rgba(160,145,125,0.45) 1px, transparent 1px), linear-gradient(150deg, rgba(160,145,125,0.45) 1px, transparent 1px), linear-gradient(30deg, rgba(160,145,125,0.18) 1px, transparent 1px), linear-gradient(150deg, rgba(160,145,125,0.18) 1px, transparent 1px)',
            backgroundSize: '80px 46px, 80px 46px, 20px 12px, 20px 12px',
          }}>
            <InfraGraph
              nodes={gameState?.nodes ?? []}
              edges={gameState?.edges ?? []}
              vulnerabilities={gameState?.vulnerabilities ?? []}
              selectingTarget={selectingTarget}
              onNodeSelect={handleNodeSelect}
              onDeselect={() => setSelectedTarget(null)}
            />
          </div>

          <WarRoom
            turnLog={gameState?.turn_log ?? []}
            turn={gameState?.company?.turn ?? 1}
            loading={loading}
            adversaryName={gameState?.company?.adversary}
          />
        </div>

        {/* Colonne droite : StrategyPanel seul */}
        <StrategyPanel
          advisorRecs={advisorRecs}
          gameState={gameState}
          selectedActions={selectedActions}
          selectedTarget={selectedTarget}
          selectingTarget={selectingTarget}
          loading={loading}
          turn={gameState?.company?.turn ?? 1}
          maxTurns={gameState?.company?.max_turns ?? 10}
          forceAudit={(gameState?.company?.compliance ?? 1) < 0.5}
          vulnerabilities={gameState?.vulnerabilities ?? []}
          onSelectAdvisor={handleSelectAdvisor}
          onSelectCto={handleSelectCto}
          onStartTargetSelect={() => setSelectingTarget(true)}
          onCommit={handleCommit}
        />
      </div>

      {gameOver && (
        <GameOverModal
          gameState={gameState}
          gameOverReason={gameOverReason}
          onReset={handleReset}
        />
      )}

      {sessionId && showIntro && gameState && (
        <div style={{
          position: 'fixed', inset: 0,
          background: 'rgba(15,23,42,0.85)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 500, fontFamily: 'Inter',
        }}>
          <div style={{
            background: '#FFFFFF', borderRadius: 12,
            maxWidth: 520, width: '90%',
            boxShadow: '0 24px 64px rgba(0,0,0,0.4)',
            overflow: 'hidden',
          }}>
            {/* Header */}
            <div style={{
              background: 'linear-gradient(135deg, #1E3A5F 0%, #1E293B 60%, #0F172A 100%)',
              borderBottom: '1px solid #2563EB',
              padding: '24px 28px',
              display: 'flex', alignItems: 'center', gap: 16,
            }}>
              <div style={{
                width: 48, height: 48, borderRadius: 8,
                background: 'rgba(37,99,235,0.25)',
                border: '1px solid rgba(37,99,235,0.4)',
                display: 'flex',
                alignItems: 'center', justifyContent: 'center',
                fontSize: 24,
              }}>
                🏦
              </div>
              <div>
                <div style={{ fontWeight: 800, fontSize: 20, color: '#F1F5F9', letterSpacing: -0.5 }}>
                  {gameState.company.name}
                </div>
                <div style={{ fontSize: 12, color: '#64748B', marginTop: 2, textTransform: 'uppercase', letterSpacing: 1 }}>
                  {gameState.company.sector}
                </div>
                <div style={{ fontSize: 11, color: '#EF4444', marginTop: 4 }}>
                  ⚠ Threat detected: <strong>{gameState.company.adversary}</strong>
                </div>
                {gameState.company.adversary_desc && (
                  <div style={{ fontSize: 10, color: '#94A3B8', marginTop: 2, fontStyle: 'italic' }}>
                    "{gameState.company.adversary_desc}"
                  </div>
                )}
              </div>
            </div>

            {/* Body */}
            <div style={{ padding: '24px 28px' }}>
              <p style={{
                fontSize: 15, lineHeight: 1.7, color: '#334155',
                fontStyle: 'italic', marginBottom: 20,
                borderLeft: '3px solid #E2E8F0', paddingLeft: 16,
              }}>
                "{gameState.company.intro ?? `${gameState.company.name} — good luck with that.`}"
              </p>

              {/* Quick stats */}
              <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
                {[
                  { label: 'Cash Runway',    value: `€${(gameState.company.cash / 1000).toFixed(1)}M` },
                  { label: 'Sector',          value: gameState.company.sector ?? 'Fintech' },
                  { label: 'Compliance',      value: `${Math.round((gameState.company.compliance ?? 0.7) * 100)}%` },
                ].map(({ label, value }) => (
                  <div key={label} style={{
                    flex: 1, background: '#F8FAFC', borderRadius: 8,
                    padding: '10px 12px', textAlign: 'center',
                    border: '1px solid #E2E8F0',
                  }}>
                    <div style={{ fontSize: 9, color: '#94A3B8', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>
                      {label}
                    </div>
                    <div style={{ fontFamily: 'JetBrains Mono', fontSize: 13, fontWeight: 700, color: '#0F172A' }}>
                      {value}
                    </div>
                  </div>
                ))}
              </div>

              {/* CTA */}
              <button
                onClick={dismissIntro}
                style={{
                  width: '100%', padding: '14px',
                  background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
                  boxShadow: '0 4px 16px rgba(37,99,235,0.35)',
                  color: '#FFFFFF',
                  border: 'none', borderRadius: 8,
                  fontFamily: 'Inter', fontWeight: 700, fontSize: 14,
                  cursor: 'pointer', letterSpacing: 0.3,
                }}
              >
                ⚡ Start Simulation — Turn 1 / {gameState?.company?.max_turns ?? 10}
              </button>
              <p style={{ textAlign: 'center', fontSize: 11, color: '#94A3B8', marginTop: 10, marginBottom: 0 }}>
                A hacker is already scanning your perimeter.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/play" element={<GameApp />} />
        <Route path="/play/:sessionId" element={<GameApp />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
