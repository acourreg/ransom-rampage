import time

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.schemas import CreateGameRequest, GameResponse, TurnRequest, TurnResponse
from app.services.game_service import (
    create_game as svc_create_game,
    get_game as svc_get_game,
    get_suggestions as svc_get_suggestions,
    play_turn as svc_play_turn,
)

router = APIRouter(prefix="/games", tags=["games"])
limiter = Limiter(key_func=get_remote_address)


@router.post("", response_model=GameResponse)
@limiter.limit("1/2minutes")
async def create_game(request: Request, body: CreateGameRequest):
    session_id, filtered_state = await svc_create_game(
        body.user_prompt,
        shape=body.shape,
        node_count=body.node_count,
        threat_agent_name=body.threat_agent_name,
        threat_agent_desc=body.threat_agent_desc,
        threat_agent_id=body.threat_agent_id,
    )
    return GameResponse(session_id=session_id, state=filtered_state)


@router.get("/{session_id}", response_model=GameResponse)
@limiter.limit("10/minute")
async def get_game(request: Request, session_id: str):
    filtered_state = await svc_get_game(session_id)
    if filtered_state is None:
        raise HTTPException(404, "Game not found")
    return GameResponse(session_id=session_id, state=filtered_state)

@router.get("/{session_id}/suggestions")
@limiter.limit("3/minute")
async def get_suggestions(request: Request, session_id: str):
    from app.storage.redis_store import load_game
    raw_state = await load_game(session_id)
    if raw_state is None:
        raise HTTPException(404, "Game not found")
    t0 = time.time()
    print(f"[SUGGESTIONS] Start — session {session_id} | turn {raw_state.get('company', {}).get('turn', '?')}")
    suggestions = await svc_get_suggestions(raw_state, session_id=session_id)
    print(f"[SUGGESTIONS] Total — {time.time() - t0:.2f}s")
    return suggestions


@router.post("/{session_id}/turn", response_model=TurnResponse)
@limiter.limit("1/20seconds")
async def play_turn(request: Request, session_id: str, body: TurnRequest):
    cto_list = [a.model_dump() for a in body.cto_actions]
    print(f"[TURN] session={session_id} action_id={body.action_id} target={body.target} cto_actions={cto_list}")
    if not body.action_id:
        raise HTTPException(400, "action_id required")
    try:
        turn_result = await svc_play_turn(session_id, body.action_id, body.target, cto_actions=cto_list)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return TurnResponse(
        state=turn_result["state"],
        events=turn_result["events"],
        game_over=turn_result["game_over"],
        game_over_reason=turn_result["game_over_reason"],
        advisor_recs=turn_result["advisor_recs"]
    )