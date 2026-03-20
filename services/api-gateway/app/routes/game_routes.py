from fastapi import APIRouter, HTTPException
from app.models.schemas import CreateGameRequest, GameResponse, TurnRequest, TurnResponse
from app.services.game_service import get_suggestions as svc_get_suggestions


from app.services.game_service import (
    create_game as svc_create_game,
    get_game as svc_get_game,
    play_turn as svc_play_turn,
)

router = APIRouter(prefix="/games", tags=["games"])


@router.post("", response_model=GameResponse)
async def create_game(request: CreateGameRequest):
    session_id, filtered_state = await svc_create_game(request.user_prompt)
    return GameResponse(session_id=session_id, state=filtered_state)


@router.get("/{session_id}", response_model=GameResponse)
async def get_game(session_id: str):
    filtered_state = await svc_get_game(session_id)
    if filtered_state is None:
        raise HTTPException(404, "Game not found")
    return GameResponse(session_id=session_id, state=filtered_state)

@router.get("/{session_id}/suggestions")
async def get_suggestions(session_id: str):
    filtered_state = await svc_get_game(session_id)
    if filtered_state is None:
        raise HTTPException(404, "Game not found")
    suggestions = await svc_get_suggestions(filtered_state)
    return suggestions


@router.post("/{session_id}/turn", response_model=TurnResponse)
async def play_turn(session_id: str, request: TurnRequest):
    if not request.action_id:
        raise HTTPException(400, "action_id required")
    try:
        turn_result = await svc_play_turn(session_id, request.action_id, request.target)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return TurnResponse(
        state=turn_result["state"],
        events=turn_result["events"],
        game_over=turn_result["game_over"],
        game_over_reason=turn_result["game_over_reason"],
        advisor_recs=turn_result["advisor_recs"]
    )