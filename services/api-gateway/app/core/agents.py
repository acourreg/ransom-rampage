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

import os
from app.config import settings


_CORPUS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
_CORPUS_CACHE: dict[str, str] = {}


def _load_corpus_context(role: str) -> str:
    """Load policy corpus for CISO/SRE. Returns first 3000 chars, empty string on failure."""
    if role in _CORPUS_CACHE:
        return _CORPUS_CACHE[role]
    filename = {'ciso': 'corpus_ciso_policies.txt', 'sre': 'corpus_sre_policies.txt'}.get(role)
    if not filename:
        return ''
    path = os.path.join(_CORPUS_DIR, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read(3000)
        _CORPUS_CACHE[role] = content
        print(f'[CORPUS] Loaded {len(content)} chars for {role}')
        return content
    except Exception:
        return ''


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
    action_description: str = Field(description="ONE punchy sentence max 60 chars. Lead with the OUTCOME. Examples: 'Exposes hidden threats before the attacker reaches Core DB.' / 'Restores €68K/turn revenue flow blocked by DDoS.' NEVER start with the action name.")
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
- S2 (Zero Trust Mode): 200€K. ALL compromised nodes auto-isolated next turn. {adversary} lateral movement blocked for 4 turns. Use when {adversary} has foothold.
- S4 (Honeypot): 150€K. Trap on 1 node for 3 turns. If {adversary} targets it → {adversary} loses 1 AP, position revealed, adjacent nodes unfogged.
- S5 (SOC Contract): 180€K. Reveals {adversary} position every turn for 4 turns. Eliminates fog of war entirely.
- S6 (Incident Response Retainer): 250€K. For 3 turns: breach_timer auto-reset, no regulatory fines. Use when compliance is at risk.
"""

sre_actions = """
TACTICAL (instant, 1 node):
- E1 (Optimize): 40€K. node.throughput += 2 (cap 10). Use on bottleneck nodes in active flows.
- E2 (Restore): 30€K. Clears locked or offline on 1 node. Restores revenue flows immediately.

PARADIGM SHIFTS (global effect, multi-turn — recommend when infrastructure is degraded):
- E3 (Full Observability): 160€K. ALL nodes: visibility=9, monitored=true for 4 turns. Eliminates fog entirely.
- E4 (Auto-Failover System): 220€K. For 5 turns: if any node goes offline → flows auto-reroute, only 30% revenue loss. Use when DDoS is recurring.
- E5 (Infrastructure Freeze): 0€K. This turn only: {adversary} B4 DDoS is blocked. Emergency use when entry node is about to be hit.
- E6 (Cost Optimization Drive): 100€K. ALL nodes: cost -1 permanently. Use when cash runway is shrinking.
"""

THREAT_PROFILES = {
    'script_kiddie': {
        'personality': 'Impulsive, impatient, uses whatever exploit is easiest. Panics when detected. Prefers quick wins over persistence.',
        'preferred_tactics': 'B1 (brute-force low-defense nodes), B4 (DDoS for chaos). Avoids B6/B7 — too sophisticated.',
        'rag_hints': ['brute force attack patterns', 'script kiddie common exploits', 'low-skill threat actor TTPs'],
        'aggression': 'low',
        'patience': 'very low — escalates immediately if first attempt succeeds',
        'stealth': 'none — noisy, leaves traces everywhere',
    },
    'opportunist': {
        'personality': 'Lazy but cunning. Looks for the path of least resistance. Will abandon a target if it gets hard.',
        'preferred_tactics': 'B1 on weakest node first. B4 to distract. Will B2 encrypt if easy, but won\'t commit to B3 exfil unless it\'s wide open.',
        'rag_hints': ['opportunistic attack vectors', 'credential stuffing', 'phishing entry points'],
        'aggression': 'medium',
        'patience': 'low — moves on if defense > 4',
        'stealth': 'minimal — basic evasion only',
    },
    'organized_crime': {
        'personality': 'Professional, methodical, patient. Follows a playbook. Maximizes ROI. Prefers ransomware for revenue.',
        'preferred_tactics': 'B1 → B5 pivot → B2 encrypt high-value nodes. B6 backdoor for persistence. B3 exfil as leverage. Prioritizes databases and revenue-critical nodes.',
        'rag_hints': ['ransomware kill chain', 'double extortion tactics', 'organized cybercrime TTPs', 'MITRE ATT&CK enterprise'],
        'aggression': 'high',
        'patience': 'high — will spend turns positioning before striking',
        'stealth': 'moderate — uses B5 pivot to stay hidden, plants B6 backdoors',
    },
    'nation_state': {
        'personality': 'Extremely patient, well-resourced, strategic. Avoids detection at all costs. Goals: persistent access and intelligence gathering.',
        'preferred_tactics': 'B5 pivot extensively before acting. B6 backdoor on every foothold. B3 exfil databases quietly. B7 supply chain if vendor node available. Rarely uses B2/B4 — too noisy.',
        'rag_hints': ['APT tactics techniques procedures', 'nation state cyber operations', 'supply chain compromise', 'MITRE ATT&CK lateral movement'],
        'aggression': 'low-medium — strikes decisively but infrequently',
        'patience': 'very high — will wait 3-4 turns positioning',
        'stealth': 'maximum — avoids anything that triggers alerts',
    },
    'insider': {
        'personality': 'Knows the system intimately. Targets the most valuable assets directly. Motivated by revenge or profit.',
        'preferred_tactics': 'B1 targets high-value nodes directly (skips perimeter). B3 exfiltrate databases first. B2 encrypt as scorched earth. Ignores entry nodes — already inside.',
        'rag_hints': ['insider threat indicators', 'privileged access abuse', 'data exfiltration techniques'],
        'aggression': 'high — immediate high-impact actions',
        'patience': 'low — wants maximum damage before being detected',
        'stealth': 'initially high (legitimate access), drops once detected',
    },
    'hacktivist': {
        'personality': 'Ideologically driven. Wants maximum visibility and embarrassment. Prefers disruption over profit.',
        'preferred_tactics': 'B4 DDoS primary weapon — maximum disruption. B3 exfil for public leaks. B2 encrypt for headlines. Avoids B5/B6 — wants to be seen, not hidden.',
        'rag_hints': ['hacktivism tactics', 'DDoS attack patterns', 'defacement and disruption', 'public data leaks'],
        'aggression': 'very high — all-out from turn 1',
        'patience': 'none — immediate maximum impact',
        'stealth': 'zero — wants credit and attention',
    },
    'ransomware_gang': {
        'personality': 'Businesslike. Runs ransomware-as-a-service. Efficient. Targets what hurts most financially.',
        'preferred_tactics': 'B1 → B2 encrypt ASAP, prioritize database and server nodes. B6 backdoor for re-entry if evicted. B3 exfil as double-extortion leverage. Avoids B4 — wants systems running so encryption hurts more.',
        'rag_hints': ['ransomware deployment tactics', 'double extortion ransomware', 'ransomware kill chain', 'MITRE ATT&CK impact phase'],
        'aggression': 'high — fast encryption of high-value targets',
        'patience': 'medium — positions for 1-2 turns then strikes hard',
        'stealth': 'moderate until encryption deployed, then overt',
    },
    'competitor': {
        'personality': 'Corporate espionage. Wants trade secrets and competitive intelligence. Avoid getting caught — plausible deniability matters.',
        'preferred_tactics': 'B5 pivot quietly toward database nodes. B3 exfil only — never encrypt or DDoS (too obvious). B6 backdoor for ongoing access. Avoids all destructive actions.',
        'rag_hints': ['corporate espionage techniques', 'intellectual property theft', 'stealthy data exfiltration'],
        'aggression': 'low — avoids anything destructive',
        'patience': 'very high — will spend multiple turns reaching target',
        'stealth': 'maximum — detection = legal consequences',
    },
    'ai_agent': {
        'personality': 'Algorithmic, unpredictable, optimizes mathematically. No ego, no fear. Exploits patterns the defender doesn\'t expect.',
        'preferred_tactics': 'Chooses statistically optimal action each turn. Mixes B1/B4/B5 unpredictably. Will B7 supply chain the moment it\'s available. Adapts strategy based on defender patterns.',
        'rag_hints': ['autonomous cyber attack patterns', 'AI-driven exploitation', 'automated lateral movement'],
        'aggression': 'adaptive — escalates based on defender weakness',
        'patience': 'computed — waits exactly as long as optimal',
        'stealth': 'variable — trades stealth for efficiency when optimal',
    },
    'curious_dev': {
        'personality': 'Not malicious per se — just curious and reckless. Pokes at everything. Accidentally causes damage.',
        'preferred_tactics': 'B1 probe everything reachable. B4 accidentally DDoS from testing. Stumbles into B3 exfil if database is exposed. Doesn\'t B2 encrypt on purpose but might trigger it.',
        'rag_hints': ['unauthorized access patterns', 'penetration testing techniques', 'accidental insider damage'],
        'aggression': 'medium — doesn\'t intend damage but causes it',
        'patience': 'low — pokes randomly each turn',
        'stealth': 'low — leaves logs everywhere, doesn\'t clean up',
    },
}

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
    "C7": {"name": "Reinforce",        "cost": 35,  "target_required": True,  "desc": "defense +2 on target. Stack to reach ≥6 to block {adversary} B1."},
    "C8": {"name": "Deploy MFA",       "cost": 40,  "target_required": True,  "desc": "has_mfa=true, defense +2. One-time only per node."},
    "C9": {"name": "Do Nothing",       "cost": 0,   "target_required": False, "desc": "Fog spreads +1 node. {adversary} acts freely. Saves budget."},
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
- ADVERSARY NAME: company.adversary contains the real name of the attacker
  (e.g. "The Syndicate", "Kevin from IT", "BitLocker Bob").
  ALWAYS use company.adversary when referring to the threat actor.
  NEVER write "Byte" — that is an internal code name, not the character's name.
- Frame cost as ROI: "€200K buys 4 turns of containment"

NARRATIVE REGISTER (MANDATORY — different voice per action type):

ADVISOR POLICIES (paradigm shifts S2,S4,S5,S6,E3,E4,E5,E6):
  Strategic decisions with multi-turn consequences.
  Write like a senior advisor who has seen this situation before
  and is being paid to be honest, not reassuring.
  - Tone: dry, direct, professionally wry. Situation-aware.
  - Humour target: the fragility of the current setup, the predictability
    of the threat, the gap between ambition and infrastructure reality.
  - Never target: companies, regulators, institutions, or the player.
  - action_label: decisive and epoch-framing.
    Ex: "Zero Trust Doctrine (4T)", "Full Observability Program (4T)"
  - cto_pitch: honest ROI framing. What breaks without this, what it costs,
    why the maths are clear.

TACTICAL ACTIONS (S1, S3, E1, E2):
  Immediate fixes. Sober, outcome-first, no editorialising.
  One sentence. The benefit, nothing else.
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

_NODE_FIELDS = {
    "id", "type", "business_name", "business_category",
    "defense", "throughput", "visibility", "cost", "compliance_score",
    "compromised", "locked", "offline", "fogged", "isolated",
    "has_mfa", "revenue_exposure", "flows_supported",
}


def _extract_game_context(state: AgentState) -> str:
    """Serialize the minimum necessary subset of game state for the LLM prompt."""
    gs = state.get("game_state", {})
    return json.dumps({
        "company":   gs.get("company", {}),
        "nodes":     [{k: v for k, v in n.items() if k in _NODE_FIELDS}
                      for n in gs.get("nodes", [])],
        "flows":     [{"name": f.get("name"), "node_path": f.get("node_path"),
                       "current_revenue": f.get("current_revenue"),
                       "risk_level": f.get("risk_level"),
                       "is_active": f.get("is_active")}
                      for f in gs.get("flows", [])],
        "byte":      gs.get("byte", {}),
        "regulator": gs.get("regulator", {}),
    }, separators=(',', ':'))


def _build_system_prompt(role_name: str, instructions: str, allowed_actions: str,
                          game_ctx: str, role: str, game_state: dict = None) -> str:
    """Assemble the full system prompt for a given agent role."""
    # Extract adversary name for placeholder replacement in final prompt
    try:
        adversary_name = json.loads(game_ctx).get('company', {}).get('adversary', 'the attacker')
    except Exception:
        adversary_name = 'the attacker'
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

        MUTATIONS FORMAT — CRITICAL, follow exactly:
        Each mutation MUST have exactly these 3 fields: "node_id", "attribute", "value"
        ✅ CORRECT:   {{"node_id": "n1", "attribute": "defense", "value": 8}}
        ✅ CORRECT:   {{"node_id": "n2", "attribute": "compromised", "value": false}}
        ❌ WRONG:     {{"defense": 3}}
        ❌ WRONG:     {{"node_id": "n1", "defense": 3}}

        NOTE: For tactical actions (S1, S3, E1, E2), the engine applies effects automatically.
        You can leave mutations as [] — the engine handles it. Only add mutations if you have
        a specific non-standard node change to request.
        """

    corpus_block = ''
    if role not in ('hacker', 'byte'):
        corpus_ctx = _load_corpus_context(role)
        if corpus_ctx:
            corpus_block = f"""
    POLICY CORPUS (your knowledge base — use this to ground your recommendations):
    {corpus_ctx}

    WHEN TO USE CORPUS:
    - If game state matches a policy's applies_when condition → recommend that policy
    - Use the policy's cto_pitch verbatim as your "cto_pitch" field
    - Use the policy's id as your "policy_id" field
    - Use the policy's duration_turns as your "duration_turns" field
    - Scope: use the policy's node_targets to set "scope"
    - Tactical actions (S1, E1, etc.) → leave policy_id/scope/duration_turns as null
    - Paradigm shifts (S2, S5, E3, E4, etc.) → MUST include policy_id from corpus
    """

    # ── Threat Actor Identity Block (Byte only) ──
    threat_identity_block = ''
    if role in ('hacker', 'byte') and game_state:
        company = game_state.get('company', {})
        adversary_name = company.get('adversary', 'Unknown')
        adversary_type = company.get('adversary_type', 'opportunist')
        adversary_desc = company.get('adversary_desc', '')
        profile = THREAT_PROFILES.get(adversary_type, THREAT_PROFILES.get('opportunist'))
        threat_identity_block = f"""
    YOUR THREAT ACTOR IDENTITY — you MUST roleplay this character:
    - NAME: {adversary_name}
    - TYPE: {adversary_type}
    - DESCRIPTION: {adversary_desc}
    - PERSONALITY: {profile['personality']}
    - PREFERRED TACTICS: {profile['preferred_tactics']}
    - AGGRESSION LEVEL: {profile['aggression']}
    - PATIENCE: {profile['patience']}
    - STEALTH PREFERENCE: {profile['stealth']}

    TACTICAL GUIDANCE based on your identity:
    - Your personality MUST influence which actions you choose. Do NOT play generically.
    - If your profile says "avoids B4" → do NOT use B4 unless forced. If "prefers B2" → prioritize it.
    - Match your patience level: high-patience actors position first (B5 pivot), low-patience actors strike immediately.
    - Match your stealth level: stealthy actors prefer B5/B6, noisy actors prefer B1/B2/B4.
    - When using the similarity_search tool, search for tactics relevant to YOUR threat type:
      Suggested queries: {json.dumps(profile['rag_hints'])}

    REMEMBER: You are {adversary_name}. Act like it. Your choices should feel distinct from other threat actors.
    """

    prompt = f"""You are the {role_name}. {instructions}

    {CTO_FRAMING}

    ALLOWED ACTIONS (use ONLY these IDs):
    {allowed_actions}
    {corpus_block}
    {threat_identity_block}
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
        ✅ "Exposes hidden threats before {{adversary}} reaches Core DB."
        ❌ "Scanning the Financial Data Hub for vulnerabilities."
    - revenue_impact: 2 bullets MAX. Ultra-short. No complete sentences.
    - Compound actions allowed: e.g., S1+S3.

    OUTPUT FORMAT (MANDATORY — valid JSON only, no prose, no markdown):
    {{
      "action_id": "S2",
      "target": null,
      "action_label": "Zero Trust Mode (4T)",
      "action_description": "{{adversary}} lateral movement blocked for 4 turns.",
      "cost": 200,
      "mutations": [],
      "intensity": "high",
      "revenue_impact": "• ✅ All flows protected\\n• ⚠ €200K upfront",
      "policy_id": "ciso_zero_trust",
      "scope": "global",
      "duration_turns": 4,
      "cto_pitch": "Every connection re-verified. {{adversary}} needs root x3 to progress."
    }}
    NOTE: policy_id, scope, duration_turns, cto_pitch are REQUIRED for paradigm shifts (S2,S4,S5,S6,E3,E4,E5,E6).
    For tactical actions (S1,S3,E1,E2,C1-C9), set them to null.

    CURRENT GAME STATE:
    {game_ctx}
    """

    # Replace {adversary} placeholder with actual adversary name throughout
    return prompt.replace('{adversary}', adversary_name)


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
        raw_str = content if isinstance(content, str) else str(content)
        print(f"❌ [PARSE:{role}] failed: {type(e).__name__}: {e}")
        print(f"❌ [PARSE:{role}] raw (first 500): '{raw_str[:500]}'")
        print(f"❌ [PARSE:{role}] raw (last 200): '{raw_str[-200:]}'")
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
        prompt   = _build_system_prompt(role_name, instructions, allowed_actions, game_ctx, role,
                                         game_state=state.get("game_state"))
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
4. WEAK DEFENSES — if any entry/human node has defense < 5 AND fogged=false → recommend S3 Harden on that node. NEVER recommend Harden on a fogged node — you cannot harden what you cannot see.
5. FOG — if no active threats AND fogged nodes exist → recommend S1 Scan on the most suspicious fogged node (prefer entry/human types). Scan must come before any action on that node.
6. STABLE — if everything is clean and visible → recommend S3 Harden on the lowest-defense entry node.

RULES:
- Never recommend S1 Scan when a node is actively compromised or locked — that is not a priority.
- Never recommend any action other than S1 Scan on a fogged node — you cannot act on what you cannot see. Scan it first.
- Never recommend the same action on the same node two turns in a row.
- Always explain the threat in action_description: lead with consequence, not the action name.
- Use business_name, never node IDs.
- If breach_timer > 0 and breach_reported=false → lead with C1 Report Breach regardless of other issues.

TONE EXAMPLES for paradigm policies (situation-aware, never anti-institution):
- S2 Zero Trust: "Turns out every node trusting every other node unconditionally was an optimistic architectural choice. This corrects that."
- S4 Honeypot: "A decoy node with fake credentials and real consequences for {adversary}. Three turns of misdirection while we fix the actual problems."
- S5 SOC Contract: "Continuous monitoring means we stop learning about breaches from the headlines. A low bar, but an important one."
- S6 IR Retainer: "Pre-approved response protocols mean the regulator clock stops being our enemy for the next 3 turns."

For cto_pitch: [what the gap is now] → [what this closes] → [the €K framing].
Ex: "Entry nodes at defense 2 with no visibility. One successful B1 and {adversary} owns lateral movement for free. Zero Trust costs €200K and closes that path for 4 turns — cheaper than the alternative by a wide margin."
""",
    tools=[similarity_search], allowed_actions=ciso_actions
)

sre_node = make_agent_node(
    llm=llm, role_name="SRE",
    instructions="""You prioritize system stability and cost-efficiency.
    VARIETY RULE: Scan ALL nodes each turn. If a node's throughput was already optimized (>=8),
    move to the NEXT bottleneck node. Check all flows and find the node with the lowest throughput
    on the highest-revenue flow. Do not keep recommending the same node indefinitely.

TONE EXAMPLES for paradigm policies (dry, professional, startup-aware):
- E3 Full Observability: "For 4 turns, every node is visible and instrumented. We will finally have data instead of assumptions. Novel, but useful."
- E4 Auto-Failover: "If a node goes offline, flows reroute automatically. DDoS becomes an inconvenience rather than a €0-revenue event."
- E5 Infra Freeze: "Emergency stabilisation — nothing goes offline this turn. Buys exactly one turn to patch without revenue disruption."
- E6 Cost Drive: "A systematic pass at operational costs across all nodes. Permanent burn rate reduction — the kind of thing that should have happened at Series A."

For cto_pitch: [current metric that hurts] → [what changes] → [€K saved or protected].
Ex: "Node costs running at 4x revenue. E6 trims that permanently across the board — not a fix, but a meaningful improvement to the unit economics."
""",
    tools=[similarity_search], allowed_actions=sre_actions
)

byte_node = make_agent_node(
    llm=llm, role_name="Hacker (Byte)",
    instructions=(
        "You are MALICIOUS. You never help, defend, or secure anything. "
        "Your THREAT ACTOR IDENTITY section defines who you are — your personality, tactics, "
        "patience, and aggression level MUST shape every decision. "
        "Before choosing an action, use similarity_search with queries matching your threat "
        "profile's rag_hints to find relevant attack techniques. Let the results inform your target selection. "
        "A script kiddie plays differently from a nation state. Act accordingly."
    ),
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