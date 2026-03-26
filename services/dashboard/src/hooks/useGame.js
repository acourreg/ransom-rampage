import { useState, useCallback } from 'react'
import { createGame, getGame, playTurn, getSuggestions } from '../api.js'

export default function useGame() {
  const [sessionId, setSessionId]     = useState(null)
  const [gameState, setGameState]     = useState(null)
  const [advisorRecs, setAdvisorRecs] = useState(null)
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState(null)
  const [gameOver, setGameOver]       = useState(false)
  const [gameOverReason, setGameOverReason] = useState(null)
  const [showIntro, setShowIntro]     = useState(false)

  const startGame = useCallback(async (prompt, options = {}) => {
    setLoading(true)
    setError(null)
    try {
      const res = await createGame(prompt, options)
      setSessionId(res.session_id)
      setGameState(res.state)
      setShowIntro(true)
      const recs = await getSuggestions(res.session_id)
      setAdvisorRecs(recs)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const commitTurn = useCallback(async (actionId, target, ctoActions = []) => {
    if (!sessionId) return
    setLoading(true)
    setAdvisorRecs(null)
    try {
      const res = await playTurn(sessionId, actionId, target, ctoActions)
      setGameState(res.state)
      if (res.game_over) {
        setGameOver(true)
        setGameOverReason(res.game_over_reason)
      } else {
        const recs = await getSuggestions(sessionId)
        setAdvisorRecs(recs)
        console.log('[RECS] turn', res.state?.company?.turn, JSON.stringify(recs, null, 2))
      }
    } catch (e) {
      setError(e.message)
      console.error('[commitTurn] error:', e)
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  const dismissIntro = useCallback(() => setShowIntro(false), [])

  const resetGame = useCallback(() => {
    setSessionId(null)
    setGameState(null)
    setAdvisorRecs(null)
    setGameOver(false)
    setGameOverReason(null)
    setError(null)
    setShowIntro(false)
  }, [])

  return {
    sessionId, gameState, advisorRecs,
    loading, error, gameOver, gameOverReason,
    showIntro, dismissIntro,
    startGame, commitTurn, resetGame
  }
}
