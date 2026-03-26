const BASE = '/api'

async function request(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  return res.json()
}

export const createGame    = (user_prompt, options = {}) => request('POST', '/games', {
  user_prompt,
  shape:              options.shape              ?? null,
  node_count:         options.nodeCount          ?? null,
  threat_agent_name:  options.threatAgent?.name  ?? null,
  threat_agent_desc:  options.threatAgent?.desc  ?? null,
  threat_agent_id:    options.threatAgent?.id    ?? null,
})
export const getGame       = (session_id)           => request('GET',  `/games/${session_id}`)
export const getSuggestions = (session_id)          => request('GET',  `/games/${session_id}/suggestions`)
export const playTurn      = (session_id, action_id, target, cto_actions = []) =>
  request('POST', `/games/${session_id}/turn`, { action_id, target, cto_actions })
