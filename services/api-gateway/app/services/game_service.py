"""
Game service — orchestration layer between routes and core.

Responsibilities:
  - Load / save game state (Redis)
  - Call core (engine, agents, generation) and transition data between them
  - Apply fog-of-war filter before returning state to the route
  - Log meaningful events (player action, engine snapshot, advisor suggestions)
  - Surface exceptions to the route layer

What does NOT belong here:
  - GDD rule resolution  → engine._resolve_player_action
  - Turn phase logic     → engine.execute_turn
  - Agent prompts/graphs → agents module
"""
import asyncio
from uuid import uuid4
from copy import deepcopy

from app.storage.redis_store import save_game, load_game
from app.core.generation import game_generator
from app.core.engine import execute_turn, resolve_player_mutations, _resolve_player_action, apply_mutations
from app.core.logger import (
    log_game_created, log_player_action, log_player_decision,
    log_byte_action, log_state_snapshot, log_advisor_suggestion, log_game_over,
)


# ══════════════════════════════════════════════════════════════
# FOG OF WAR FILTER
# ══════════════════════════════════════════════════════════════

def apply_fog_filter(state: dict) -> dict:
    """
    Redact state before sending to the frontend:
    • Fogged nodes: hide numeric stats, blank category and flows.
    • Vulnerabilities: remove entries not yet known by the player.
    • Byte internals: strip byte_presence.
    """
    filtered = deepcopy(state)

    for node in filtered.get('nodes', []):
        if node.get('fogged'):
            for key in ('throughput', 'defense', 'visibility', 'cost', 'compliance_score'):
                node[key] = '???'
            node['revenue_exposure']   = '???'
            node['business_category']  = 'Unknown'
            node['flows_supported']    = []

    filtered['vulnerabilities'] = [
        v for v in filtered.get('vulnerabilities', [])
        if v.get('known_by_player', True)
    ]

    if 'byte' in filtered and 'byte_presence' in filtered['byte']:
        del filtered['byte']['byte_presence']

    for flow in filtered.get('flows', []):
        if 'current_revenue' not in flow:
            flow['current_revenue'] = 0

    return filtered


# ══════════════════════════════════════════════════════════════
# GAME LIFECYCLE
# ══════════════════════════════════════════════════════════════

async def create_game(
    user_prompt: str,
    shape: str | None = None,
    node_count: int | None = None,
    threat_agent_name: str | None = None,
    threat_agent_desc: str | None = None,
    threat_agent_id:   str | None = None,
) -> tuple[str, dict]:
    """Generate a new game, persist it, return (session_id, filtered_state)."""
    session_id = uuid4().hex[:12]

    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, game_generator.invoke, {
            'user_prompt':       user_prompt,
            'shape':             shape             or 'layered',
            'node_count':        node_count        or 6,
            'threat_agent_name': threat_agent_name or 'Hector the Intern',
            'threat_agent_desc': threat_agent_desc or 'Armed with a YouTube tutorial and too much free time',
            'threat_agent_id':   threat_agent_id   or 'script_kiddie',
        })
        state  = result.get('final_gamestate', {})
        print(f'🎮 Generated state with {len(state.get("nodes", []))} nodes')
    except Exception as e:
        import traceback
        print(f'⚠️ game_generator failed: {type(e).__name__}: {e}')
        traceback.print_exc()
        state = _empty_state()

    try:
        await save_game(session_id, state)
    except Exception:
        pass

    log_game_created(session_id, state)
    return session_id, apply_fog_filter(state)


async def get_game(session_id: str) -> dict | None:
    """Load and return filtered game state, or None if not found."""
    state = await load_game(session_id)
    if state is None:
        state = _empty_state()
    return apply_fog_filter(state)


# ══════════════════════════════════════════════════════════════
# ADVISOR SUGGESTIONS
# ══════════════════════════════════════════════════════════════

async def get_suggestions(state: dict, session_id: str = 'unknown') -> dict:
    """Run CISO, SRE and Byte agents in parallel; return their parsed recommendations."""
    from app.core.agents import ciso_graph, sre_graph, byte_graph
    import json

    def _build(role):
        return {'messages': [], 'game_state': state, 'cache_hit': False,
                'current_cache_key': '', 'active_role': role}

    loop = asyncio.get_event_loop()
    ciso_r, sre_r, byte_r = await asyncio.gather(
        loop.run_in_executor(None, ciso_graph.invoke, _build('ciso')),
        loop.run_in_executor(None, sre_graph.invoke,  _build('sre')),
        loop.run_in_executor(None, byte_graph.invoke, _build('byte')),
    )

    ciso_rec  = json.loads(ciso_r['messages'][-1].content)
    sre_rec   = json.loads(sre_r['messages'][-1].content)
    byte_rec  = json.loads(byte_r['messages'][-1].content)

    print(f"[REC:ciso] action_id={ciso_rec.get('action_id')} target={ciso_rec.get('target')}")
    print(f"[REC:sre]  action_id={sre_rec.get('action_id')}  target={sre_rec.get('target')}")

    turn = state.get('company', {}).get('turn', 0)
    for role, rec in (('ciso', ciso_rec), ('sre', sre_rec), ('byte', byte_rec)):
        log_advisor_suggestion(
            session_id, turn, role,
            rec.get('action_id', '?'), rec.get('target'),
            rec.get('action_label', ''), rec.get('action_description', ''),
            rec.get('cost', 0),
        )

    return {'ciso': ciso_rec, 'sre': sre_rec, 'byte': byte_rec}


# ══════════════════════════════════════════════════════════════
# TURN EXECUTION
# ══════════════════════════════════════════════════════════════

async def play_turn(session_id: str, action_id: str, target: str | None = None, cto_actions: list | None = None) -> dict:
    """
    Execute one game turn:
      1. Load state
      2. Run Byte agent (async) to get next Byte recommendation
      3. Log pre-engine decision snapshot
      4. Delegate full turn resolution to engine.execute_turn
      5. Log post-engine state snapshot
      6. Persist new state
      7. Return filtered state + events
    """
    from app.core.agents import byte_graph
    import json

    state = await load_game(session_id)
    if state is None:
        raise ValueError('Game not found')
    if state.get('game_over'):
        raise ValueError('Game is already over')

    current_turn = state.get('company', {}).get('turn', 0) + 1
    cto_summary = ', '.join(f"{c['action_id']}:{c.get('target')}" for c in (cto_actions or []))
    log_player_action(session_id, current_turn, action_id, target)
    if cto_actions:
        print(f"[PLAYER_ACTION] advisor={action_id} target={target} | cto=[{cto_summary}]")

    loop = asyncio.get_event_loop()

    # ── Byte agent: decide next move (will be queued, resolved next turn) ──
    try:
        byte_result = await loop.run_in_executor(
            None, byte_graph.invoke,
            {'messages': [], 'game_state': state, 'cache_hit': False,
             'current_cache_key': '', 'active_role': 'byte'}
        )
        byte_rec = json.loads(byte_result['messages'][-1].content)
        print(f"[BYTE] action_id={byte_rec.get('action_id')} target={byte_rec.get('target')}")
        log_byte_action(session_id, current_turn,
                        byte_rec.get('action_id', '?'), byte_rec.get('target'), 'queued')
    except Exception as e:
        print(f'[BYTE] agent failed: {e}')
        byte_rec = {'action_id': 'B1', 'target': None, 'mutations': []}

    # ── Pre-engine snapshot: log what the player intends + planned mutations ──
    planned_mutations = resolve_player_mutations(action_id, target, state)
    log_player_decision(
        session_id, current_turn, action_id, target, state,
        planned_mutations,
        byte_rec.get('action_id') if isinstance(byte_rec, dict) else None,
        byte_rec.get('target')    if isinstance(byte_rec, dict) else None,
    )

    # ── CTO actions: resolve before engine (applied to state, engine sees the result) ──
    for cto in (cto_actions or []):
        cto_muts = _resolve_player_action(cto['action_id'], cto.get('target'), state)
        _, cto_applied = apply_mutations(state, cto_muts)
        print(f"[CTO] {cto['action_id']} target={cto.get('target')} → {len(cto_applied)} mutations")
        for a in cto_applied:
            print(f"  → {a['node_id']}.{a['attribute']}: {a.get('old_value')} → {a['new_value']}")

    # ── Engine: full turn resolution (primary action resolved inside) ──
    new_state = await loop.run_in_executor(
        None, execute_turn, state, action_id, target, byte_rec
    )

    resolved_turn = new_state.get('company', {}).get('turn', current_turn)

    # ── Post-engine snapshot ──
    log_state_snapshot(session_id, resolved_turn, new_state)

    if new_state.get('game_over'):
        log_game_over(session_id, resolved_turn, new_state.get('game_over_reason', '?'))

    # ── Persist ──
    try:
        await save_game(session_id, new_state)
    except Exception:
        pass

    return {
        'state':            apply_fog_filter(new_state),
        'events':           new_state.get('turn_log', [])[-10:],
        'game_over':        new_state.get('game_over', False),
        'game_over_reason': new_state.get('game_over_reason', None),
        'advisor_recs':     {'ciso': {}, 'sre': {}},
    }


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _empty_state() -> dict:
    return {
        'company':         {'cash': 5000, 'turn': 1, 'compliance': 0.7, 'reputation': 0.8},
        'nodes':           [],
        'edges':           [],
        'flows':           [],
        'vulnerabilities': [],
        'byte':            {'byte_presence': {}, 'byte_ap': 2},
        'regulator':       {'breach_timer': None, 'deletion_requested': False},
        'effects':         [],
        'turn_log':        [],
    }
