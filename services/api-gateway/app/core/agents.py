from app.storage.vector_store import vectorstore, similarity_search
# Merged from app/agents/configs.py, cache.py, factory.py, graphs.py
# Core business logic only: no FastAPI/Redis imports

from typing import Optional, List, Union, Literal, Annotated, TypedDict
import copy
import json

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
    action_label: str = Field(description="Label court pour l'UI (max 20 chars)")
    action_description: str = Field(description="Justification en UNE phrase (max 140 chars).")
    cost: int = Field(description="Coût total en €K")
    mutations: List[NodeMutation] = Field(description="Liste des mutations physiques à appliquer sur le graph")
    intensity: Literal["low", "medium", "high"] = Field(default="medium")
    revenue_impact: Optional[str] = Field(
        default=None,
        description="Expected impact on revenue flows"
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
- S1 (Scan): 50€K. Reveals compromised + vulns on 1 node. Reliable if visibility ≥ 5, else misses vulns. No revenue impact.
- S2 (Isolate): 100€K. node.isolated = true → Byte blocked, but ALL flows through node = €0 revenue. High cost, use sparingly.
- S3 (Harden): 80€K. node.defense += 3 (cap 10). No direct revenue impact but prevents future compromise.
- S4 (Honeypot): 150€K. Place trap on 1 node. If Byte targets it next turn, Byte wastes 1 AP and is revealed. node.fogged = false on adjacent nodes. Expensive but reveals Byte position.
- S5 (Segment): 120€K. Remove 1 edge from the graph. Limits Byte lateral movement but may break a flow path → check revenue impact before cutting.
- S6 (Threat Hunt): 70€K. Reveals byte_presence on target node + all adjacent nodes. Unlike S1, works regardless of visibility. Does not reveal vulns.
"""

sre_actions = """
- E1 (Optimize): 40€K. node.throughput += 2 (cap 10). If node is bottleneck on a flow → revenue ↑ immediately.
- E2 (Restore): 30€K. Clears locked or offline on 1 node. Takes 1 turn (offline_turns = 1). Re-enables flows through node.
- E3 (Monitor): 50€K + 10€K/turn recurring. node.monitored = true, visibility = 9. Ongoing cost eats into margin.
- E4 (Scale Up): 60€K. node.throughput += 3 (cap 10) BUT node.cost += 2. More revenue but higher burn rate. Choose bottleneck nodes.
- E5 (Failover): 80€K. Clone 1 node as backup. If original goes offline/locked, flows auto-reroute to clone. Clone has same stats, cost = original.cost + 1. Adds 1 node + edges to graph.
- E6 (Cost Cut): 20€K. node.cost -= 2 (min 1) BUT node.throughput -= 1. Reduces burn rate at expense of revenue. Good for non-bottleneck support nodes.
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
    "C1": {"name": "Report breach",   "cost": 20,  "desc": "Reset breach_timer. reputation −0.05 but avoids fine R1"},
    "C2": {"name": "Deploy MFA",      "cost": 40,  "desc": "node.has_mfa = true → defense += 3 on human nodes"},
    "C3": {"name": "Patch",           "cost": 60,  "desc": "Remove 1 known vuln. Node offline_turns = 1 → flows disrupted 1 turn"},
    "C4": {"name": "Pay ransom",      "cost": 200, "desc": "Clear locked on 1 node. reputation −0.10. Expensive but instant recovery"},
    "C5": {"name": "Evict",           "cost": 30,  "desc": "Clear compromised on 1 node (unless B6 Backdoor planted)"},
    "C6": {"name": "Do nothing",      "cost": 0,   "desc": "Fog spreads +1 node. Byte acts freely. Save cash for next turn"},
    "C7": {"name": "Buy insurance",   "cost": 100, "desc": "insurance_active = true. premium = 20€K/turn. Caps fine R1 at −300€K. Ongoing cost"},
    "C8": {"name": "Hire consultant", "cost": 150, "desc": "All nodes: visibility += 2 for 3 turns. Temporary effect. Expensive but reveals everything"},
    "C9": {"name": "Emergency fund",  "cost": 0,   "desc": "Sacrifice 1 active flow (set is_active=false permanently). Gain +500€K cash immediately. Desperate move"},
}

REGULATOR_RULES_REF = """
R1 Fine: breach_timer expires → cash −500..−2000, compliance −0.10
R2 Audit: compliance < 0.5 → player loses action
R3 Suspend: compliance < 0.2 → lowest compliance_score node → offline 3 turns
R4 Deletion: scripted T6-7 → purge or ignore
"""


# ── LLM ──

llm = ChatOpenAI(
    model="gpt-5-nano",
    temperature=0,
    max_completion_tokens=2000,
    model_kwargs={"reasoning": {"effort": "low"}},
    api_key=settings.OPENAI_API_KEY,
)


# ── Agent node factory (SYNC) ──

def make_agent_node(llm, role_name, instructions, tools, allowed_actions):
    def call_agent(state: AgentState):
        game_ctx = json.dumps(state.get("game_state", {}), indent=2)
        role = state.get("active_role", "unknown").lower()

        if role in ["hacker", "byte"]:
            mutation_block = """
            MUTATION RULES (OFFENSIVE — MANDATORY):
            You are a MALICIOUS ATTACKER. You NEVER help, defend, or secure anything.
            - Set 'compromised' or 'locked' to TRUE (NEVER false).
            - Use NEGATIVE values for 'defense' and 'throughput' (e.g., -2, -5).
            - Action IDs MUST be B1, B2, B3, or B4. No other IDs allowed.
            - Your action_label and action_description MUST sound hostile/offensive.
            """
        else:
            mutation_block = f"""
            MUTATION RULES (DEFENSIVE):
            As {role_name}, your goal is restoration and hardening.
            - Set 'compromised' or 'locked' to FALSE.
            - Use POSITIVE values for 'defense' and 'throughput' (e.g., +2, +3).
            - Action IDs MUST match your ALLOWED ACTIONS list below. No other IDs.
            """

        system_content = f"""You are the {role_name}. {instructions}

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
        - Taking a node offline (DDoS, patch, isolate) kills ALL flows through it → revenue = 0.
        - You MUST set 'revenue_impact' in your recommendation explaining the financial consequence.
        - Consider: is the action cost + revenue loss worth the defensive/offensive gain?

        CONSTRAINTS:
        - target: must be a specific node_id (e.g., "n3"), not "Global".
        - Description: 140 chars max.
        - Compound: You can combine 2 action IDs (e.g., B1+B4 or S1+S3).

        CURRENT GAME STATE:
        {game_ctx}
        """

        messages = [{"role": "system", "content": system_content}] + state["messages"]
        response = llm.bind_tools(tools).invoke(messages)
        return {"messages": [response]}

    return call_agent


def generate_recommendation(state: AgentState):
    try:
        structured_llm = llm.with_structured_output(AgentRecommendation)
        recommendation = structured_llm.invoke(state["messages"])
        return {"messages": [AIMessage(content=recommendation.model_dump_json())]}
    except Exception as e:
        fallback = AgentRecommendation(
            action_id="wait", target=None,
            action_label="System Error",
            action_description="The procedural engine failed to sync.",
            cost=0, mutations=[], intensity="low"
        )
        return {"messages": [AIMessage(content=fallback.model_dump_json())]}


# ── Cache nodes (SYNC) ──

def gateway_cache_node(state: AgentState):
    role = state.get("active_role", "unknown")
    key = get_cache_key(copy.deepcopy(state["game_state"]), role)
    print(f"DEBUG: Role: {role} | Key Hash: {hash(key)}")

    res = vectorstore.similarity_search_with_relevance_scores(
        key, k=1,
        filter={"doc_type": "semantic_cache", "role": role}
    )

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
    if not state.get("cache_hit") and "current_cache_key" in state:
        response_text = state["messages"][-1].content
        vectorstore.add_texts(
            texts=[state["current_cache_key"]],
            metadatas=[{
                "doc_type": "semantic_cache",
                "role": role,
                "response": response_text
            }]
        )
        from app.config import settings as _s
        DB_PATH = "../data/unified_vector_db"
        vectorstore.save_local(DB_PATH)
        print(f"✅ Cache saved for {role}")
    return state


# ── Build agent nodes ──

ciso_node = make_agent_node(
    llm=llm, role_name="CISO",
    instructions="""You are risk-averse. Prioritize scanning and hardening over business speed.
    IMPORTANT: If nodes have fogged=true or unknown stats, your FIRST priority is S1 (Scan) on the most suspicious fogged node (prefer human or entry types). Never recommend 'do nothing' when fog exists.""",
    tools=[similarity_search], allowed_actions=ciso_actions
)

sre_node = make_agent_node(
    llm=llm, role_name="SRE",
    instructions="You prioritize system stability and cost-efficiency. Monitor and optimize infrastructure.",
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
    workflow.add_node("retrieve", ToolNode(tools))
    workflow.add_node("generate", generate_recommendation)
    workflow.add_node("update_cache", update_cache_node)

    workflow.set_entry_point("gateway")
    workflow.add_conditional_edges("gateway", lambda s: "hit" if s.get("cache_hit") else "miss", {"hit": END, "miss": "agent"})
    workflow.add_conditional_edges("agent", tools_condition, {"tools": "retrieve", END: "generate"})
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "update_cache")
    workflow.add_edge("update_cache", END)

    return workflow.compile()


# ── 3 graphs only: CISO, SRE, Byte (NO CTO graph) ──

ciso_graph = compile_agent_graph(ciso_node, [similarity_search])
sre_graph  = compile_agent_graph(sre_node,  [similarity_search])
byte_graph = compile_agent_graph(byte_node, [similarity_search])

print("✅ Compiled: ciso_graph, sre_graph, byte_graph (no cto_graph)")