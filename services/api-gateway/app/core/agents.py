from app.storage.vector_store import vectorstore, similarity_search
# Merged from app/agents/configs.py, cache.py, factory.py, graphs.py
# Core business logic only: no FastAPI/Redis imports

from typing import Optional, List, Union, Literal, Annotated, TypedDict
import copy
import json
import time

from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools.retriever import create_retriever_tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import tools_condition, ToolNode

from app.config import settings


# ── State ──

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    game_state: dict
    cache_hit: bool
    current_cache_key: str
    active_role: str  # required — LangGraph drops undeclared keys silently


# ── Pydantic models ──

class NodeMutation(BaseModel):
    node_id: str = Field(description="ID du node à modifier")
    attribute: Literal[
        "defense", "throughput", "visibility", "cost", "compliance_score",
        "compromised", "locked", "offline", "fogged"
    ] = Field(description="L'attribut à modifier")
    value: Union[int, bool] = Field(description="La valeur à ajouter (int) ou l'état à fixer (bool)")


class AgentRecommendation(BaseModel):
    action_id: str = Field(description="Code technique (ex: S1, B2, S1+S3)")
    target: Optional[str] = Field(description="ID du node ciblé, ou None pour global", default=None)
    action_label: str = Field(description="Action label max 30 chars. FORMAT MANDATORY: '[VERB] [business_name]'. Examples: 'Scan Payment Hub', 'Harden Auth Portal', 'Restore Transaction Engine', 'Isolate HR System'. NEVER just the node name alone. NEVER node IDs.")
    action_description: str = Field(description="ONE punchy sentence max 60 chars. Lead with the OUTCOME. Examples: 'Exposes hidden threats before Byte reaches Core DB.' / 'Restores €68K/turn revenue flow blocked by DDoS.' NEVER start with the action name.")
    cost: int = Field(description="Coût total en €K")
    mutations: List[NodeMutation] = Field(description="Liste des mutations physiques à appliquer sur le graph")
    intensity: Literal["low", "medium", "high"] = Field(default="medium")
    revenue_impact: Optional[str] = Field(
        default=None,
        description="2-3 bullet points max. Format: '• Benefit: ...' '• Risk: ...' '• Cost: ...'. Use business_name. Max 120 chars total."
    )


# ── Cache helpers ──

STRATEGIES = {
    "cash": lambda v: f"budget_{'high' if v > 5000 else 'med' if v > 1000 else 'low'}",
    "defense": lambda v: f"def_{v}",
    "visibility": lambda v: f"vis_{v}",
    "compromised": lambda v: "STATUS_BREACHED" if v else "STATUS_SECURE",
    "locked": lambda v: "NODE_LOCKED" if v else "NODE_OPEN",
    "offline": lambda v: "NODE_OFFLINE" if v else "NODE_ONLINE"
}

IGNORE = {"turn", "turn_log", "effects", "id", "name", "last_action", "cost", "throughput"}


def purify_state(obj):
    if isinstance(obj, dict):
        return {k: STRATEGIES[k](v) if k in STRATEGIES else purify_state(v)
                for k, v in obj.items() if k not in IGNORE}
    if isinstance(obj, list):
        return [purify_state(i) for i in obj]
    return obj


def get_cache_key(state: dict, role: str) -> str:
    purified = purify_state(copy.deepcopy(state))
    state_str = json.dumps(purified, sort_keys=True)
    return f"ROLE:{role} | STATE:{state_str}"


# ── Action sets ──

ciso_actions = """
TACTICAL (instant, 1 node):
- S1 (Scan): 50€K. Reveals vulns + unfogged on 1 node. Use on suspicious/fogged nodes first.
- S3 (Harden): 80€K. node.defense += 3 (cap 10). Best on Revenue Critical nodes.

PARADIGM SHIFTS (global effect, multi-turn — recommend when situation is critical):
- S2 (Zero Trust Mode): 200€K. ALL compromised nodes auto-isolated next turn. Byte lateral movement blocked for 4 turns. Use when Byte has foothold.
- S4 (Honeypot): 150€K. Trap on 1 node for 3 turns. If Byte targets it → Byte loses 1 AP, position revealed, adjacent nodes unfogged.
- S5 (SOC Contract): 180€K. Reveals Byte position every turn for 4 turns. Eliminates fog of war entirely.
- S6 (Incident Response Retainer): 250€K. For 3 turns: breach_timer auto-reset, no regulatory fines. Use when compliance is at risk.
"""

sre_actions = """
TACTICAL (instant, 1 node):
- E1 (Optimize): 40€K. node.throughput += 2 (cap 10). Use on bottleneck nodes in active flows.
- E2 (Restore): 30€K. Clears locked or offline on 1 node. Restores revenue flows immediately.

PARADIGM SHIFTS (global effect, multi-turn — recommend when infrastructure is degraded):
- E3 (Full Observability): 160€K. ALL nodes: visibility=9, monitored=true for 4 turns. Eliminates fog entirely.
- E4 (Auto-Failover System): 220€K. For 5 turns: if any node goes offline → flows auto-reroute, only 30% revenue loss. Use when DDoS is recurring.
- E5 (Infrastructure Freeze): 0€K. This turn only: Byte B4 DDoS is blocked. Emergency use when entry node is about to be hit.
- E6 (Cost Optimization Drive): 100€K. ALL nodes: cost -1 permanently. Use when cash runway is shrinking.
"""

byte_actions = """
- B1 (Compromise): 1 AP. Requires adjacent compromised node + target.defense < 6. Sets node.compromised = true. Prep for B2/B3.
- B2 (Encrypt): 2 AP. Requires node compromised, type ≠ human. Sets node.locked = true → ALL flows through node = €0. breach_timer = 3.
- B3 (Exfiltrate): 2 AP. Requires node compromised, type = database. reputation −0.15, breach_timer = 3, compliance −0.10. Devastating if Core DB.
- B4 (DDoS): 1 AP. No prerequisite. Sets node.offline = true, offline_turns = 2 → ALL flows through node = €0. Cheap disruption.
- B5 (Pivot): 1 AP. Move byte_presence from one compromised node to an adjacent node WITHOUT compromising it. Useful for repositioning toward Core DB. Stealthy — not visible to player.
- B6 (Backdoor): 2 AP. Requires node compromised. Plants hidden access. node.compromised stays true even after CTO C5 (Evict). Only cleared by S1 Scan + C3 Patch combo. Invisible to scans with visibility < 7.
- B7 (Supply Chain): 2 AP. Requires byte_presence on a vendor node. Compromises ALL nodes connected to that vendor via edges. Ignores defense threshold. Devastating chain attack.
"""

CTO_ACTIONS_REF = {
    "C1": {"name": "Report Breach",    "cost": 20,  "target_required": False, "desc": "Reset breach_timer. Avoids fine. -5% reputation."},
    "C2": {"name": "Boost Throughput", "cost": 25,  "target_required": True,  "desc": "throughput +2 on target. Immediate revenue lift."},
    "C3": {"name": "Patch Vuln",       "cost": 30,  "target_required": True,  "desc": "Remove 1 known vuln. Node offline 1 turn. Requires prior Scan."},
    "C4": {"name": "Cut Costs",        "cost": 15,  "target_required": True,  "desc": "cost -1 on target. Reduces burn rate permanently."},
    "C5": {"name": "Evict Attacker",   "cost": 30,  "target_required": True,  "desc": "Clear compromised on target node + lateral spread."},
    "C6": {"name": "Pay Ransom",       "cost": 200, "target_required": True,  "desc": "Clear locked node instantly. Expensive. -10% reputation."},
    "C7": {"name": "Reinforce",        "cost": 35,  "target_required": True,  "desc": "defense +2 on target. Stack to reach ≥6 to block Byte B1."},
    "C8": {"name": "Deploy MFA",       "cost": 40,  "target_required": True,  "desc": "has_mfa=true, defense +2. One-time only per node."},
    "C9": {"name": "Do Nothing",       "cost": 0,   "target_required": False, "desc": "Fog spreads +1 node. Byte acts freely. Saves budget."},
}

REGULATOR_RULES_REF = """
R1 Fine: breach_timer expires → cash −500..−2000, compliance −0.10
R2 Audit: compliance < 0.5 → player loses action
R3 Suspend: compliance < 0.2 → lowest compliance_score node → offline 3 turns
R4 Deletion: scripted T6-7 → purge or ignore
"""

CTO_FRAMING = """
CTO COMMUNICATION RULES (MANDATORY):
You are advising a CTO. The game state contains BOTH technical and business data.

AVAILABLE BUSINESS DATA IN GAME STATE (use these!):
- node.business_name: CTO-friendly name (e.g., "Payments Processing Core")
- node.business_category: "Revenue Critical" / "Operations" / "External Dependency" / "People & Access" / "Support"
- node.revenue_exposure: €K/turn at risk if this node goes down
- node.flows_supported: list of revenue flow names this node supports
- flow.business_description: what this flow does in business terms
- flow.risk_level: "critical" / "high" / "unknown" / "low"
- company.total_revenue_at_risk: €K/turn across all at-risk flows

ACTION FRAMING RULES:
- TACTICAL actions (S1, S3, E1, E2): frame as "quick fix" — specific node, immediate ROI
- PARADIGM SHIFT actions (S2, S4, S5, S6, E3, E4, E5, E6): frame as "changes the rules" — global impact, strategic investment
  Paradigm label format: "Zero Trust Mode (4T)" / "Auto-Failover (5T)" — always add turn duration
  Paradigm description: lead with what changes globally, not what you do

RULES:
- action_label: VERB + business impact. Paradigm shifts: include duration "(4T)".
    Verb map: Scan=S1, Harden=S3, Isolate=S2, Restore=E2, Optimize=E1, Monitor=E3,
              Deploy MFA=C8, Patch=C1, Evict=C5, Reinforce=C3, Boost=C2
- action_description: lead with OUTCOME not action name. Max 60 chars.
- revenue_impact: ultra-short bullets only. 2 max.
- Use node.business_name, NEVER node.id
- Frame cost as ROI: "€200K buys 4 turns of containment"
"""


# ── LLM ──

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    max_tokens=800,
    api_key=settings.OPENAI_API_KEY,
    model_kwargs={"response_format": {"type": "json_object"}},
)


# ── Agent node factory (SYNC) ──

def _extract_game_context(state: AgentState) -> str:
    """Serialize the relevant subset of game state for the LLM prompt."""
    gs = state.get("game_state", {})
    return json.dumps({
        "company":   gs.get("company", {}),
        "nodes":     [{k: v for k, v in n.items() if k not in ("monitored", "offline_turns")}
                      for n in gs.get("nodes", [])],
        "flows":     gs.get("flows", []),
        "byte":      gs.get("byte", {}),
        "regulator": gs.get("regulator", {}),
    }, separators=(',', ':'))


def _build_system_prompt(role_name: str, instructions: str, allowed_actions: str,
                          game_ctx: str, role: str) -> str:
    """Assemble the full system prompt for a given agent role."""
    if role in ("hacker", "byte"):
        mutation_block = """
        MUTATION RULES (OFFENSIVE — MANDATORY):
        You are a MALICIOUS ATTACKER. You NEVER help, defend, or secure anything.
        Action IDs MUST be B1, B2, B3, or B4. No other IDs allowed.

        MUTATIONS FORMAT — CRITICAL, follow exactly:
        Each mutation MUST have exactly these 3 fields: "node_id", "attribute", "value"
        ✅ CORRECT:   {"node_id": "n3", "attribute": "compromised", "value": true}
        ❌ WRONG:     {"field": "compromised", "value": true}

        For B1: attribute="compromised", value=true
        For B2: attribute="locked", value=true
        For B3: attribute="compromised", value=true (on database node)
        For B4: attribute="offline", value=true
        """
    else:
        mutation_block = f"""
        MUTATION RULES (DEFENSIVE):
        As {role_name}, your goal is restoration and hardening.
        - Set 'compromised' or 'locked' to FALSE.
        - Use POSITIVE values for 'defense' and 'throughput' (e.g., +2, +3).
        - Action IDs MUST match your ALLOWED ACTIONS list below. No other IDs.
        """

    return f"""You are the {role_name}. {instructions}

    {CTO_FRAMING}

    ALLOWED ACTIONS (use ONLY these IDs):
    {allowed_actions}

    {mutation_block}

    INTENSITY SCALE:
    - low: +/- 1 unit. Cost: 0.5x base.
    - medium: +/- 2-3 units. Cost: 1x base.
    - high: +/- 5+ units. Cost: 2x base.

    ECONOMIC AWARENESS:
    - Each node has a 'cost' stat (1-10). Operational cost = cost × 5 €K/turn.
    - Revenue flows: current_revenue = base_revenue × (min throughput on path / 10).
    - Taking a node offline kills ALL flows through it → revenue = 0.
    - You MUST set 'revenue_impact' explaining the financial consequence.

    CONSTRAINTS (STRICT):
    - target: specific node_id only (e.g., "n3"). Never "Global".
    - action_label: max 30 chars. FORMAT = VERB + business_name (or duration for paradigms).
        ✅ GOOD tactical: "Scan Financial Data Hub", "Restore User Gateway"
        ✅ GOOD paradigm: "Zero Trust Mode (4T)", "Auto-Failover (5T)"
        Verb map: Scan=S1, Harden=S3, Restore=E2, Optimize=E1, Evict=C5, Patch=C3, Reinforce=C7
        Paradigm map: S2=Zero Trust, S4=Honeypot, S5=SOC Contract, S6=IR Retainer,
                      E3=Full Observability, E4=Auto-Failover, E5=Infra Freeze, E6=Cost Drive
    - action_description: ONE sentence, max 60 chars. Lead with OUTCOME.
        ✅ "Exposes hidden threats before Byte reaches Core DB."
        ❌ "Scanning the Financial Data Hub for vulnerabilities."
    - revenue_impact: 2 bullets MAX. Ultra-short. No complete sentences.
    - Compound actions allowed: e.g., S1+S3.

    OUTPUT FORMAT (MANDATORY — valid JSON only, no prose, no markdown):
    {{
      "action_id": "S1",
      "target": "n3",
      "action_label": "Short label max 30 chars",
      "action_description": "One sentence max 60 chars",
      "cost": 50,
      "mutations": [],
      "intensity": "medium",
      "revenue_impact": "• ✅ benefit\\n• ⚠ risk"
    }}

    CURRENT GAME STATE:
    {game_ctx}
    """


def _parse_recommendation(content: str, role: str) -> AgentRecommendation:
    """
    Parse LLM output into AgentRecommendation.
    Strips markdown fences if present. Returns a fallback on any failure.
    """
    try:
        raw = content if isinstance(content, str) else json.dumps(content)
        raw = raw.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw  = raw.strip()
        data = json.loads(raw)
        rec  = AgentRecommendation(**data)
        print(f"✅ [PARSE:{role}] action_id={rec.action_id}")
        return rec
    except Exception as e:
        print(f"❌ [PARSE:{role}] failed: {type(e).__name__}: {e}")
        return AgentRecommendation(
            action_id="wait", target=None,
            action_label="System Error",
            action_description="The procedural engine failed to sync.",
            cost=0, mutations=[], intensity="low",
        )


def make_agent_node(llm, role_name, instructions, tools, allowed_actions):
    def call_agent(state: AgentState):
        role     = state.get("active_role", "unknown").lower()
        game_ctx = _extract_game_context(state)
        prompt   = _build_system_prompt(role_name, instructions, allowed_actions, game_ctx, role)
        messages = [{"role": "system", "content": prompt}] + state["messages"]
        t_llm    = time.time()
        print(f"[LLM:{role}] invoking...")
        response = llm.invoke(messages)
        print(f"[LLM:{role}] done — {time.time() - t_llm:.2f}s")
        return {"messages": [response]}
    return call_agent


def generate_recommendation(state: AgentState):
    t_gen   = time.time()
    role    = state.get("active_role", "unknown")
    content = state["messages"][-1].content if state["messages"] else ""
    rec     = _parse_recommendation(content, role)
    print(f"[GENERATE:{role}] {time.time() - t_gen:.2f}s")
    return {"messages": [AIMessage(content=rec.model_dump_json())]}


CACHE_ENABLED = False  # ← set True once perf is tuned


# ── Cache nodes (SYNC) ──

def gateway_cache_node(state: AgentState):
    role = state.get("active_role", "unknown")
    if not CACHE_ENABLED:
        print(f"[CACHE:{role}] bypassed")
        return {"cache_hit": False, "current_cache_key": ""}

    key = get_cache_key(copy.deepcopy(state["game_state"]), role)
    print(f"DEBUG: Role: {role} | Key Hash: {hash(key)}")

    t_cache = time.time()
    res = vectorstore.similarity_search_with_relevance_scores(
        key, k=1,
        filter={"doc_type": "semantic_cache", "role": role}
    )
    print(f"[CACHE:{role}] similarity_search done — {time.time() - t_cache:.2f}s")

    score = res[0][1] if res else 0
    print(f"DEBUG: Score: {score}")

    if score > 0.9999:
        print(f"🎯 Cache Hit for {role}")
        return {
            "messages": [AIMessage(content=res[0][0].metadata["response"])],
            "cache_hit": True
        }

    print(f"💨 Cache Miss for {role}")
    return {"cache_hit": False, "current_cache_key": key}


def update_cache_node(state: AgentState):
    role = state.get("active_role", "unknown")
    if not CACHE_ENABLED:
        print(f"[CACHE_UPDATE:{role}] bypassed")
        return state

    if not state.get("cache_hit") and "current_cache_key" in state:
        response_text = state["messages"][-1].content
        if isinstance(response_text, list):
            response_text = json.dumps(response_text)
        t_upd = time.time()
        vectorstore.add_texts(
            texts=[state["current_cache_key"]],
            metadatas=[{
                "doc_type": "semantic_cache",
                "role": role,
                "response": response_text
            }]
        )
        print(f"[CACHE_UPDATE:{role}] add_texts done — {time.time() - t_upd:.2f}s")
        print(f"✅ Cache updated in-memory for {role} (no disk write)")
    return state


# ── Build agent nodes ──

ciso_node = make_agent_node(
    llm=llm, role_name="CISO",
    instructions="""You are the CISO. Your job is to protect revenue and stop the attacker — not just scan things.

PRIORITY ORDER (follow strictly):
1. CRISIS FIRST — if any node is compromised or locked → recommend C5 Evict or S2 Zero Trust or S6 IR Retainer. Do NOT recommend Scan when the house is on fire.
2. IMMINENT THREAT — if breach_timer > 0 → recommend C1 Report Breach immediately to avoid fine.
3. KNOWN VULNS — if any node has known_by_player=true vulnerabilities → recommend C3 Patch on that node.
4. WEAK DEFENSES — if any entry/human node has defense < 5 → recommend S3 Harden on that node.
5. FOG — if no active threats AND fogged nodes exist → recommend S1 Scan on the most suspicious fogged node (prefer entry/human types).
6. STABLE — if everything is clean and visible → recommend S3 Harden on the lowest-defense entry node.

RULES:
- Never recommend S1 Scan when a node is actively compromised or locked — that is not a priority.
- Never recommend the same action on the same node two turns in a row.
- Always explain the threat in action_description: lead with consequence, not the action name.
- Use business_name, never node IDs.
- If breach_timer > 0 and breach_reported=false → lead with C1 Report Breach regardless of other issues.""",
    tools=[similarity_search], allowed_actions=ciso_actions
)

sre_node = make_agent_node(
    llm=llm, role_name="SRE",
    instructions="""You prioritize system stability and cost-efficiency.
    VARIETY RULE: Scan ALL nodes each turn. If a node's throughput was already optimized (>=8),
    move to the NEXT bottleneck node. Check all flows and find the node with the lowest throughput
    on the highest-revenue flow. Do not keep recommending the same node indefinitely.""",
    tools=[similarity_search], allowed_actions=sre_actions
)

byte_node = make_agent_node(
    llm=llm, role_name="Hacker (Byte)",
    instructions="You are MALICIOUS. Compromise weak nodes, encrypt databases, exfiltrate data. You never help the defender.",
    tools=[similarity_search], allowed_actions=byte_actions
)


# ── Graph compiler ──

def compile_agent_graph(agent_node, tools):
    workflow = StateGraph(AgentState)
    workflow.add_node("gateway", gateway_cache_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("generate", generate_recommendation)
    workflow.add_node("update_cache", update_cache_node)

    workflow.set_entry_point("gateway")
    workflow.add_conditional_edges("gateway", lambda s: "hit" if s.get("cache_hit") else "miss", {"hit": END, "miss": "agent"})
    workflow.add_edge("agent", "generate")
    workflow.add_edge("generate", "update_cache")
    workflow.add_edge("update_cache", END)

    return workflow.compile()


# ── 3 graphs only: CISO, SRE, Byte (NO CTO graph) ──

ciso_graph = compile_agent_graph(ciso_node, [similarity_search])
sre_graph  = compile_agent_graph(sre_node,  [similarity_search])
byte_graph = compile_agent_graph(byte_node, [similarity_search])

print("✅ Compiled: ciso_graph, sre_graph, byte_graph (no cto_graph)")