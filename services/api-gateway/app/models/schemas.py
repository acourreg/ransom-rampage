from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# ============================================================
# Agent & Game Models (from notebook cell 8, adapted)
# ============================================================

class NodeMutation(BaseModel):
    """Mutation applied to a single node attribute."""
    node_id: str
    attribute: str
    value: int | float | bool | str

class AgentRecommendation(BaseModel):
    """Recommendation from an agent (CISO, SRE, BYTE)."""
    action_id: str
    target: Optional[str] = None
    action_label: str
    action_description: str
    cost: int = 0
    mutations: List[Dict[str, Any]] = Field(default_factory=list)
    policy_id:      Optional[str] = None
    scope:          Optional[str] = None
    duration_turns: Optional[int] = None
    cto_pitch:      Optional[str] = None

# ============================================================
# API Request/Response Models
# ============================================================

class CreateGameRequest(BaseModel):
    """Request to create a new game."""
    user_prompt: str = Field(
        default="Generate a highly disruptive Fintech startup that tackles a mundane industry",
        description="Prompt for entity generation"
    )
    shape:             Optional[str] = Field(default=None, description="Infrastructure topology shape")
    node_count:        Optional[int] = Field(default=None, description="Number of nodes to generate")
    threat_agent_name: Optional[str] = Field(default=None, description="Human name of the threat actor")
    threat_agent_desc: Optional[str] = Field(default=None, description="One-liner description of the threat actor")
    threat_agent_id:   Optional[str] = Field(default=None, description="Technical threat category ID")

class CtoAction(BaseModel):
    """A single CTO action in the multi-action payload."""
    action_id: str
    target: Optional[str] = None

class TurnRequest(BaseModel):
    """Request to execute a game turn."""
    action_id: str = Field(description="Primary action (advisor or solo CTO if no cto_actions)")
    target: Optional[str] = Field(default=None, description="Optional target node_id")
    cto_actions: List[CtoAction] = Field(default_factory=list, description="Additional CTO actions executed alongside primary")

class GameResponse(BaseModel):
    """Response with game state (fog-filtered)."""
    session_id: str
    state: Dict[str, Any]

class TurnResponse(BaseModel):
    """Response after turn execution."""
    state: Dict[str, Any]
    events: List[Dict[str, Any]] = Field(default_factory=list)
    game_over: bool = False
    game_over_reason: Optional[str] = None
    advisor_recs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)