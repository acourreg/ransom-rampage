import asyncio
from uuid import uuid4
from copy import deepcopy

from app.models.schemas import GameResponse, TurnResponse  # Keep schemas for types, but functions take primitives
from app.storage.redis_store import save_game, load_game
from app.core.generation import game_generator

def apply_fog_filter(state: dict) -> dict:
    """
    Apply fog of war filter to game state.
    - Fogged nodes: redact throughput, defense, visibility, cost, compliance_score to "???"
    - Unknown vulnerabilities: hide
    - Byte presence: remove entirely
    """
    filtered = deepcopy(state)
    
    # Redact fogged nodes
    for node in filtered.get("nodes", []):
        if node.get("fogged"):
            node["throughput"] = "???"
            node["defense"] = "???"
            node["visibility"] = "???"
            node["cost"] = "???"
            node["compliance_score"] = "???"
    
    # Hide unknown vulnerabilities
    filtered_vulns = [
        v for v in filtered.get("vulnerabilities", [])
        if v.get("known_by_player", True)
    ]
    filtered["vulnerabilities"] = filtered_vulns
    
    # Remove byte_presence from byte dict
    if "byte" in filtered and "byte_presence" in filtered["byte"]:
        del filtered["byte"]["byte_presence"]
    
    return filtered

async def create_game(user_prompt: str) -> tuple[str, dict]:
    """
    Create a new game via game_generator pipeline.
    Returns (session_id, filtered_state)
    """
    session_id = uuid4().hex[:12]
    
    try:
        # Invoke game_generator (sync → executor)
        loop = asyncio.get_event_loop()
        print(f"📝 Invoking game_generator with prompt: {user_prompt}")
        result = await loop.run_in_executor(
            None, 
            game_generator.invoke, 
            {"user_prompt": user_prompt}
        )
        print(f"📊 game_generator result keys: {result.keys()}")
        state = result.get("final_gamestate", {})
        print(f"🎮 Generated state with {len(state.get('nodes', []))} nodes")
    except Exception as e:
        # Fallback: empty state on error
        print(f"⚠️ game_generator failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        state = {
            "company": {"cash": 5000, "turn": 1, "compliance": 0.7, "reputation": 0.8},
            "nodes": [],
            "edges": [],
            "flows": [],
            "vulnerabilities": [],
            "byte": {"byte_presence": {}, "byte_ap": 2},
            "regulator": {"breach_timer": None, "deletion_requested": False},
            "effects": [],
            "turn_log": [],
        }
    
    # Save to Redis
    try:
        await save_game(session_id, state)
    except Exception:
        pass  # Redis not available
    
    filtered_state = apply_fog_filter(state)
    return session_id, filtered_state

async def get_game(session_id: str) -> dict | None:
    """
    Load game state.
    Returns filtered_state or None
    """
    state = await load_game(session_id)
    if state is None:
        # For dev/placeholder: return a minimal state
        state = {
            "company": {"cash": 5000, "turn": 1, "compliance": 0.7, "reputation": 0.8},
            "nodes": [],
            "edges": [],
            "flows": [],
            "vulnerabilities": [],
            "byte": {"byte_presence": {}, "byte_ap": 2},
            "regulator": {"breach_timer": None, "deletion_requested": False},
            "effects": [],
            "turn_log": [],
        }
    return apply_fog_filter(state)


async def get_suggestions(state: dict) -> dict:
    loop = asyncio.get_event_loop()

    def _invoke_agents():
        from app.core.agents import ciso_graph, sre_graph
        import json

        def build(role):
            return {"messages": [], "game_state": state, "cache_hit": False, "current_cache_key": "",
                    "active_role": role}

        ciso_result = ciso_graph.invoke(build("ciso"))
        sre_result = sre_graph.invoke(build("sre"))

        ciso_rec = json.loads(ciso_result["messages"][-1].content)
        sre_rec = json.loads(sre_result["messages"][-1].content)
        return {"ciso": ciso_rec, "sre": sre_rec}

    return await loop.run_in_executor(None, _invoke_agents)


async def play_turn(session_id: str, action_id: str, target: str | None = None) -> dict:
    """
    Execute turn.
    Simplified: assumes action_id and optional target from player input.
    Returns dict with state, events, etc. (similar to TurnResponse)
    """
    state = await load_game(session_id)
    if state is None:
        # Placeholder: return minimal state if not found (for dev/testing)
        state = {
            "company": {"cash": 5000, "turn": 1, "compliance": 0.7, "reputation": 0.8},
            "nodes": [],
            "edges": [],
            "flows": [],
            "vulnerabilities": [],
            "byte": {"byte_presence": {}, "byte_ap": 2},
            "regulator": {"breach_timer": None, "deletion_requested": False},
            "effects": [],
            "turn_log": [],
        }
    
    if state.get("game_over"):
        raise ValueError("Game is already over")
    
    # Placeholder: just increment turn (will integrate agents later)
    state["company"]["turn"] += 1
    try:
        await save_game(session_id, state)
    except Exception:
        pass  # Redis not available; continue
    
    return {
        "state": apply_fog_filter(state),
        "events": state.get("turn_log", [])[-10:],
        "game_over": False,
        "game_over_reason": None,
        "advisor_recs": {"ciso": {}, "sre": {}}
    }