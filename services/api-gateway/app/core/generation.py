# Game generation pipeline — LangGraph orchestration of 4 agents.
# Each agent is a focused function; the node wrappers are thin.

from app.storage.vector_store import vectorstore

from typing import TypedDict, Dict, Any
import json
import random
from langgraph.graph import StateGraph, END
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from app.config import settings


# ══════════════════════════════════════════════════════════════
# PIPELINE STATE
# ══════════════════════════════════════════════════════════════

class GameCreationState(TypedDict):
    user_prompt:       str
    shape:             str
    node_count:        int
    threat_agent_name: str
    threat_agent_desc: str
    threat_agent_id:   str
    company_data:      Dict[str, Any]
    infra_data:        Dict[str, Any]
    final_gamestate:   Dict[str, Any]


gen_llm = ChatOpenAI(
    model='gpt-4o-mini', temperature=0, max_tokens=2000,
    api_key=settings.OPENAI_API_KEY
)

fintech_retriever = vectorstore.as_retriever(search_kwargs={'filter': {'agent': 'fintech'}, 'k': 3})
tech_retriever    = vectorstore.as_retriever(search_kwargs={'filter': {'agent': 'techno'}, 'k': 10})


# ══════════════════════════════════════════════════════════════
# AGENT 1: VENTURE ARCHITECT — LLM generates company + flow specs
# ══════════════════════════════════════════════════════════════

def venture_architect_node(state: GameCreationState):
    print('🚀 [Venture Architect] Generating startup concept...')

    prompt = ChatPromptTemplate.from_template("""
    You are the Venture Architect. Define a Fintech startup that is janky but functional.
    It just raised a decent round and needs a CTO to clean up.

    CONTEXT: {context}
    PLAYER REQUEST: {input}

    RULES:
    - NAME: Creative startup name.
    - DESCRIPTION: Cynical but slightly optimistic. Max 2 sentences.
    - SECTOR: One of: neobank, p2p, hft, payments.
    - ADVERSARY: One of: script_kiddie, mafia, state.
    - CASH: 3000-4500 €K.
    - FLOWS: 3-4 flows. Each flow MUST use DIFFERENT node type combinations.
      Do NOT make all flows use the same path pattern.

    OUTPUT FORMAT (strict JSON, no markdown):
    {{
        "name": "...",
        "description": "...",
        "sector": "neobank|p2p|hft|payments",
        "adversary": "script_kiddie|mafia|state",
        "cash": 5000,
        "flows": [
            {{
                "name": "Flow Name",
                "description": "Monetization logic",
                "node_path_types": ["entry", "middleware", "database"],
                "base_revenue": 40
            }}
        ]
    }}
    """)

    chain  = ({'context': fintech_retriever, 'input': RunnablePassthrough()} | prompt | gen_llm | JsonOutputParser())
    result = chain.invoke(state['user_prompt'])
    return {'company_data': result}


# ══════════════════════════════════════════════════════════════
# AGENT 2: LEAD SRE — LLM generates raw infrastructure
# ══════════════════════════════════════════════════════════════

_SHAPE_DESCRIPTIONS = {
    'star':         '1 central hub connected to ALL other nodes. Minimal edges between non-hub nodes.',
    'linear':       'Nodes mostly in sequence A→B→C→D. Max 1-2 shortcuts between non-adjacent nodes.',
    'mesh':         'Dense cross-connections. Most nodes connect to 3+ others. Multiple paths to database.',
    'siloed':       '2 separate sub-clusters. Connected ONLY through 1 shared bridge node.',
    'hub_and_spoke':'2 distinct hub nodes each with 2-3 satellite nodes. Hubs connected to each other.',
    'layered':      'Strict left-to-right columns: entry → middleware → database. Minimal cross-column edges.',
    'binary_tree':  'Branching tree: 1 root entry → 2 middleware → 2-4 leaf nodes. No cycles.',
}


def sre_infra_node(state: GameCreationState):
    print('🛠️ [Lead SRE] Provisioning infrastructure...')

    shape      = state.get('shape', 'layered')
    node_count = state.get('node_count', 6)
    shape_desc = _SHAPE_DESCRIPTIONS.get(shape, _SHAPE_DESCRIPTIONS['layered'])
    print(f'  🗺  shape={shape} node_count={node_count}')

    tech_docs    = tech_retriever.invoke('gateway database server middleware vendor human fintech infrastructure')
    tech_context = '\n'.join([d.page_content for d in tech_docs])

    prompt = ChatPromptTemplate.from_template("""
    You are the Lead SRE. Build an infra that has survived 2 years.

    COMPANY: {specs}
    TECH DATABASE: {tech_context}

    TOPOLOGY (MANDATORY — follow exactly, do NOT deviate):
    Shape: {shape}
    Description: {shape_desc}
    Node count: exactly {node_count} nodes. Node IDs: n1 through n{node_count}.
    Respect this topology strictly when defining edges.

    Type distribution — vary it each time:
    - Sometimes 2 entry nodes, sometimes 1
    - Sometimes 2 databases, sometimes 1 (one is the Core DB, clearly named)
    - Sometimes 0 vendor nodes, sometimes 2
    - Sometimes 3 middleware, sometimes 1
    - Human nodes: 0, 1, or 2
    Do NOT always generate: 1 entry + 1 human + 1 vendor + 2 middleware + 1 server + 1 database.

    STRICT RULES:
    - Must have at least 1 "entry" and at least 1 "database" node (Core DB).
    - STATS: All integers 1-10. No node should have ALL stats high — each has a tradeoff.
      * node.cost range: 2-5 (aim LOW — higher costs drain cash too fast).
      * "human" nodes: defense 1-3, throughput 2-4, cost 2-4
      * "vendor" nodes: visibility 2-4 (opaque third-party), cost 3-5
      * "database" (Core DB): defense 7-9, throughput 8-10, cost 4-6

    ECONOMIC BALANCE RULE (MANDATORY):
    Total operational costs = sum(node.cost × 5) per turn.
    Total base revenue = sum(flow.base_revenue) per turn.
    CONSTRAINT: total_costs MUST be < 60% of total_base_revenue at game start.
    - EDGES: Core DB must have 2+ edges. No orphan nodes.
      Include at least one "lateral" path (entry → human or vendor → middleware) for Byte.
    - VULNERABILITIES: 3-5 vulns. severity 1-3 ONLY. NOT on the Core DB node.
    - All nodes start: compromised=false, locked=false, offline=false.
    - Max 1 node fogged initially (assembler will add more).

    OUTPUT FORMAT (strict JSON, no markdown):
    {{
        "nodes": [
            {{
                "id": "n1", "name": "...", "type": "entry|human|middleware|database|vendor|server",
                "throughput": 7, "defense": 5, "visibility": 6, "cost": 4, "compliance_score": 5,
                "compromised": false, "locked": false, "offline": false, "fogged": false
            }}
        ],
        "edges": [{{"from": "n1", "to": "n2"}}],
        "vulnerabilities": [{{"node_id": "n2", "severity": 2, "description": "...", "known_by_player": false}}]
    }}
    """)

    chain  = (prompt | gen_llm | JsonOutputParser())
    result = chain.invoke({
        'specs':       json.dumps(state['company_data']),
        'tech_context': tech_context,
        'shape':       shape,
        'shape_desc':  shape_desc,
        'node_count':  node_count,
    })
    return {'infra_data': result}


# ══════════════════════════════════════════════════════════════
# AGENT 3: ASSEMBLER — deterministic validation, repair and assembly
# ══════════════════════════════════════════════════════════════

def _normalize_nodes(nodes: list) -> None:
    """Flatten nested stats/tags from LLM output; set boolean defaults."""
    for n in nodes:
        if 'stats' in n:
            n.update(n.pop('stats'))
        if 'tags' in n:
            n.update(n.pop('tags'))
        for flag in ('compromised', 'locked', 'offline', 'isolated', 'fogged', 'has_mfa', 'monitored'):
            n.setdefault(flag, False)
        n.setdefault('offline_turns', 0)


def _repair_core_db_connectivity(nodes: list, edges: list) -> None:
    """Ensure the Core DB node has at least 3 edges; add synthetic edges if needed."""
    core_db = next((n for n in nodes if n['type'] == 'database'), None)
    if not core_db:
        return
    core_edges = sum(1 for e in edges if e['from'] == core_db['id'] or e['to'] == core_db['id'])
    if core_edges >= 3:
        return
    print(f"  ⚠️ Core DB {core_db['id']} has {core_edges} edges (need 3+) — adding")
    existing  = {(e['from'], e['to']) for e in edges}
    other_ids = [n['id'] for n in nodes if n['id'] != core_db['id']]
    for other_id in other_ids:
        if core_edges >= 3:
            break
        edge = {'from': core_db['id'], 'to': other_id}
        rev  = {'from': other_id, 'to': core_db['id']}
        if (edge['from'], edge['to']) not in existing and (rev['from'], rev['to']) not in existing:
            edges.append(edge)
            existing.add((edge['from'], edge['to']))
            core_edges += 1


def _filter_and_fill_vulns(nodes: list, raw_vulns: list) -> list:
    """
    Keep only severity 1-3 vulns not on the Core DB.
    Fill up to minimum 3 vulns with random assignments if needed.
    """
    core_db = next((n for n in nodes if n['type'] == 'database'), None)
    vulns   = [v for v in raw_vulns if v.get('severity') in (1, 2, 3)]
    if core_db:
        vulns = [v for v in vulns if v.get('node_id') != core_db['id']]
    print(f'  🔍 Vulns after filter: {len(vulns)} (raw={len(raw_vulns)})')

    eligible = [n['id'] for n in nodes if n['type'] != 'database']
    if len(vulns) < 3:
        targeted   = {v['node_id'] for v in vulns}
        candidates = [nid for nid in eligible if nid not in targeted]
        random.shuffle(candidates)
        for nid in candidates:
            if len(vulns) >= 3:
                break
            vulns.append({'node_id': nid, 'severity': random.randint(1, 3), 'known_by_player': False})

    print(f'  ✅ Final vulns: {len(vulns[:5])}')
    return vulns[:5]


def _distribute_fog(nodes: list) -> None:
    """Set 30-50% of non-entry nodes as fogged. Entry nodes are always visible."""
    total      = len(nodes)
    target_fog = random.randint(max(2, total * 3 // 10), total * 5 // 10)
    for n in nodes:
        n['fogged'] = False
    foggable = [n for n in nodes if n['type'] != 'entry']
    random.shuffle(foggable)
    for n in foggable[:target_fog]:
        n['fogged'] = True
    actual = sum(1 for n in nodes if n['fogged'])
    print(f'  📊 Fog: {actual}/{total} ({100 * actual // total}%)')


def _resolve_flow_paths(nodes: list, flow_specs: list) -> list:
    """
    Wire each flow's node_path_types to actual node IDs.
    Returns a list of resolved flow dicts with base_revenue, is_active, current_revenue.
    """
    node_map   = {n['id']: n for n in nodes}
    type_nodes: dict[str, list[str]] = {}
    for n in nodes:
        type_nodes.setdefault(n['type'], []).append(n['id'])
    all_ids = [n['id'] for n in nodes]

    final_flows = []
    used_paths  = set()

    for f in flow_specs[:4]:
        path_ids = []
        for t in f.get('node_path_types', ['entry', 'middleware', 'database']):
            pool = type_nodes.get(t, type_nodes.get('server', type_nodes.get('middleware', [])))
            pick = next((nid for nid in pool if nid not in path_ids), None) or \
                   next((nid for nid in all_ids if nid not in path_ids), None)
            if pick:
                path_ids.append(pick)

        if len(path_ids) < 2:
            continue

        path_key = tuple(path_ids)
        if path_key in used_paths and len(path_ids) > 2:
            mid     = len(path_ids) // 2
            mid_t   = next((n['type'] for n in nodes if n['id'] == path_ids[mid]), 'middleware')
            alts    = [nid for nid in type_nodes.get(mid_t, []) + all_ids
                       if nid != path_ids[mid] and nid not in path_ids]
            if alts:
                path_ids[mid] = alts[0]
        used_paths.add(tuple(path_ids))

        tp_values  = [node_map[pid]['throughput'] for pid in path_ids if pid in node_map]
        tp_min     = min(tp_values) if tp_values else 5
        base_rev   = max(5, min(35, f.get('base_revenue', random.randint(15, 35))))
        is_active  = all(
            not node_map.get(pid, {}).get('locked') and
            not node_map.get(pid, {}).get('offline') and
            not node_map.get(pid, {}).get('isolated')
            for pid in path_ids
        )
        final_flows.append({
            'name':            f.get('name', f'Flow {len(final_flows) + 1}'),
            'node_path':       path_ids,
            'base_revenue':    base_rev,
            'is_active':       is_active,
            'current_revenue': int(base_rev * tp_min / 10) if is_active else 0,
        })

    if not final_flows:
        # Fallback: direct entry → database path
        entry = next((n for n in nodes if n['type'] == 'entry'), None)
        core  = next((n for n in nodes if n['type'] == 'database'), None)
        if entry and core:
            final_flows.append({
                'name': 'Primary Flow', 'node_path': [entry['id'], core['id']],
                'base_revenue': 50, 'is_active': True, 'current_revenue': 35,
            })

    return final_flows


def _assemble_initial_state(comp: dict, nodes: list, edges: list,
                             flows: list, vulns: list) -> dict:
    """Package all pieces into the canonical game state dict."""
    adversary = comp.get('adversary', 'script_kiddie')
    byte_ap   = 3 if adversary == 'state' else 2
    entries   = [n['id'] for n in nodes if n['type'] in ('entry', 'human')]

    return {
        'company': {
            'name':             comp.get('name', 'UnnamedCorp'),
            'description':      comp.get('description', ''),
            'sector':           comp.get('sector', 'payments'),
            'adversary':        adversary,
            'cash':             max(2500, min(4000, comp.get('cash', 3500))),
            'turn':             1,
            'compliance':       0.7,
            'reputation':       0.8,
            'insurance_active': False,
            'insurance_premium': 0,
            'breach_reported':  False,
        },
        'nodes':           nodes,
        'edges':           edges,
        'flows':           flows,
        'vulnerabilities': vulns,
        'byte':            {'byte_presence': {}, 'byte_ap': byte_ap, 'byte_active_ops': []},
        'regulator':       {'breach_timer': None, 'deletion_requested': False},
        'effects':         [],
        'turn_log':        [{
            'source': 'system', 'action': 'INIT', 'target': None,
            'message': f"{comp.get('name', '?')} generated. Adversary: {adversary}. Entries: {entries}",
            'visible_to_player': True,
        }],
    }


def game_assembler_node(state: GameCreationState):
    print('🏁 [Assembler] Validating GDD compliance & wiring flows...')
    comp  = state['company_data']
    infra = state['infra_data']
    nodes = infra['nodes']
    edges = infra.get('edges', [])

    _normalize_nodes(nodes)
    _repair_core_db_connectivity(nodes, edges)

    vulns = _filter_and_fill_vulns(nodes, infra.get('vulnerabilities', []))
    _distribute_fog(nodes)
    flows = _resolve_flow_paths(nodes, comp.get('flows', []))

    game_state = _assemble_initial_state(comp, nodes, edges, flows, vulns)

    # Override adversary with frontend-selected threat agent
    threat_name = state.get('threat_agent_name', game_state['company']['adversary'])
    threat_id   = state.get('threat_agent_id',   game_state['company']['adversary'])
    threat_desc = state.get('threat_agent_desc', '')
    game_state['company']['adversary']      = threat_name
    game_state['company']['adversary_type'] = threat_id
    game_state['company']['adversary_desc'] = threat_desc
    # Nation-state and professional ransomware gangs get 3 AP; everyone else gets 2
    game_state['byte']['byte_ap'] = 3 if threat_id in ('nation_state', 'ransomware_gang') else 2
    print(f'  ⚔️  Threat: {threat_name} ({threat_id}) | byte_ap={game_state["byte"]["byte_ap"]}')

    # Calibrate max_turns based on economic viability
    company = game_state['company']
    total_costs_per_turn = sum(n.get('cost', 0) * 5 for n in nodes)
    total_base_revenue   = sum(f.get('base_revenue', 0) for f in flows)
    cash                 = company.get('cash', 4000)
    survival_turns_at_zero = cash // total_costs_per_turn if total_costs_per_turn > 0 else 20
    net_per_turn           = total_base_revenue - total_costs_per_turn

    if net_per_turn > 20 and survival_turns_at_zero > 15:
        max_turns = random.randint(15, 20)
    elif net_per_turn > 0 and survival_turns_at_zero > 10:
        max_turns = random.randint(12, 16)
    elif net_per_turn > -20:
        max_turns = random.randint(9, 13)
    else:
        max_turns = random.randint(6, 10)

    company['max_turns'] = max_turns
    print(f'  🕐 max_turns={max_turns} (net/turn={net_per_turn} survival_at_zero={survival_turns_at_zero})')

    node_types = {n['type'] for n in nodes}
    core_db    = next((n for n in nodes if n['type'] == 'database'), None)
    core_edge_count = sum(1 for e in edges
                          if core_db and (e['from'] == core_db['id'] or e['to'] == core_db['id']))
    print(f"  ✅ Nodes: {len(nodes)} | Edges: {len(edges)} | Flows: {len(flows)}")
    print(f"  ✅ Types: {', '.join(sorted(node_types))} | Vulns: {len(vulns)}")
    print(f"  ✅ Byte AP: {game_state['byte']['byte_ap']} | Core DB edges: {core_edge_count}")

    return {'final_gamestate': game_state}


# ══════════════════════════════════════════════════════════════
# AGENT 4: VALUE CHAIN ENRICHER — deterministic metrics + LLM labels
# ══════════════════════════════════════════════════════════════

def _compute_node_metrics(nodes: list, flows: list) -> None:
    """Compute revenue_exposure, flows_supported, and business_category per node."""
    total_revenue = sum(f.get('current_revenue', 0) for f in flows if f.get('is_active'))

    for n in nodes:
        n['revenue_exposure'] = sum(
            f['current_revenue'] for f in flows
            if n['id'] in f.get('node_path', []) and f.get('is_active')
        )
        n['flows_supported'] = [
            f['name'] for f in flows if n['id'] in f.get('node_path', [])
        ]
        t   = n.get('type', 'server')
        pct = (n['revenue_exposure'] / total_revenue) if total_revenue > 0 else 0
        if t == 'human':
            cat = 'People & Access'
        elif t == 'vendor':
            cat = 'External Dependency'
        elif t == 'database':
            cat = 'Revenue Critical'
        elif pct >= 0.30:
            cat = 'Revenue Critical'
        elif n['revenue_exposure'] > 0:
            cat = 'Operations'
        else:
            cat = 'Support'
        n['business_category'] = cat
        print(f"  📊 {n['id']} ({t}): rev_exposure={n['revenue_exposure']} pct={pct:.0%} → {cat}")


def _classify_flow_risks(flows: list, nodes: list, vulns: list) -> None:
    """Set risk_level on each flow based on node health + known vulnerabilities."""
    node_map      = {n['id']: n for n in nodes}
    vuln_node_ids = {v['node_id'] for v in vulns}

    for f in flows:
        path_nodes = [node_map.get(nid) for nid in f.get('node_path', []) if nid in node_map]
        if any(n.get('compromised') for n in path_nodes if n):
            f['risk_level'] = 'critical'
        elif (any(nid in vuln_node_ids for nid in f.get('node_path', [])) or
              any(n.get('defense', 10) < 5 for n in path_nodes if n)):
            f['risk_level'] = 'high'
        elif any(n.get('fogged') for n in path_nodes if n):
            f['risk_level'] = 'unknown'
        else:
            f['risk_level'] = 'low'


def _enrich_business_labels(company: dict, nodes: list, flows: list) -> None:
    """LLM call: assign CTO-friendly business_name per node and business_description per flow."""
    nodes_list = '\n'.join(f"- {n['id']}: {n['name']} (type: {n['type']})" for n in nodes)
    total_rev  = sum(f.get('current_revenue', 0) for f in flows if f.get('is_active')) or 1
    flows_list = '\n'.join(
        f"- {f['name']}: €{f.get('current_revenue', 0)}K/turn "
        f"({int(f.get('current_revenue', 0) * 100 / total_rev)}% of revenue)"
        for f in flows
    )

    prompt = ChatPromptTemplate.from_template("""
    You are a business analyst translating technical infrastructure into CTO-friendly language.

    COMPANY: {company_name} ({sector})
    DESCRIPTION: {company_desc}

    For each node, generate a SHORT business-friendly name (3-5 words, no jargon).
    For each flow, generate a business description that MUST include the €K/turn revenue and % of total.
    Example: "Primary card processing — €35K/turn (45% of total revenue)"

    NODES:
    {nodes_list}

    FLOWS (with revenue data — you MUST reference these numbers):
    {flows_list}

    OUTPUT FORMAT (strict JSON, no markdown):
    {{
        "nodes": [{{"id": "n1", "business_name": "..."}}],
        "flows": [{{"name": "Flow Name", "business_description": "..."}}]
    }}
    """)

    try:
        enrichment     = (prompt | gen_llm | JsonOutputParser()).invoke({
            'company_name': company.get('name', ''),
            'sector':       company.get('sector', ''),
            'company_desc': company.get('description', ''),
            'nodes_list':   nodes_list,
            'flows_list':   flows_list,
        })
        node_enrich = {e['id']: e for e in enrichment.get('nodes', [])}
        flow_enrich = {e['name']: e for e in enrichment.get('flows', [])}
        for n in nodes:
            n['business_name'] = node_enrich.get(n['id'], {}).get('business_name', n['name'])
        for f in flows:
            f['business_description'] = flow_enrich.get(f['name'], {}).get('business_description', f['name'])
    except Exception as e:
        print(f'  ⚠️ LLM enrichment failed: {e} — using fallback names')
        for n in nodes:
            n.setdefault('business_name', n['name'])
        for f in flows:
            f.setdefault('business_description', f['name'])


_INTRO_PROMPT = (
    "You are a dry British wit trapped inside a Bloomberg terminal.\n"
    "Write a 2-3 sentence intro for this fintech startup.\n"
    "Tone: Economist obituary meets Silicon Valley roast — clever wordplay, ironic understatement,\n"
    "genuinely funny but never mean-spirited.\n"
    "Max 220 chars. No emojis.\n\n"
    "STRUCTURE (mandatory):\n"
    "1. Sentence 1-2: Roast the company itself — name, model, or infra. Reference 1-2 node names.\n"
    "2. Final sentence only: Introduce the threat by name as a punchline.\n\n"
    "Company: {name}\nSector: {sector}\nThreat actor: {adversary_name} — {adversary_desc}\nKey nodes: {nodes}\n"
)


def _generate_intro(company: dict, nodes: list) -> str:
    """LLM call: generate a punchy company intro. Returns intro string."""
    try:
        node_names = ', '.join(n.get('business_name', n.get('name', '')) for n in nodes[:3])
        response   = gen_llm.invoke([{
            'role':    'user',
            'content': _INTRO_PROMPT.format(
                name=company.get('name', 'Unknown'),
                sector=company.get('sector', 'fintech'),
                adversary_name=company.get('adversary', 'unknown'),
                adversary_desc=company.get('adversary_desc', ''),
                nodes=node_names,
            ),
        }])
        intro = response.content.strip().strip('"')
        print(f'[INTRO] {intro[:100]}...')
        return intro
    except Exception as e:
        print(f'[INTRO] Failed: {e}')
        return f"{company.get('name', 'Your startup')} — good luck with that."


def value_chain_enricher_node(state: GameCreationState):
    print('💼 [Value Chain Enricher] Adding business context...')
    game_state = state['final_gamestate']
    company    = game_state['company']
    nodes      = game_state['nodes']
    flows      = game_state['flows']
    vulns      = game_state.get('vulnerabilities', [])

    _compute_node_metrics(nodes, flows)
    _classify_flow_risks(flows, nodes, vulns)
    _enrich_business_labels(company, nodes, flows)
    company['intro'] = _generate_intro(company, nodes)

    company['total_revenue_at_risk'] = sum(
        f['current_revenue'] for f in flows
        if f.get('risk_level') in ('critical', 'high')
    )

    print(f"  ✅ Enriched {len(nodes)} nodes, {len(flows)} flows")

    try:
        from app.core.logger import log_game_created
        log_game_created('__generation__', game_state)
    except Exception:
        pass

    return {'final_gamestate': game_state}


# ══════════════════════════════════════════════════════════════
# PIPELINE GRAPH
# ══════════════════════════════════════════════════════════════

builder = StateGraph(GameCreationState)
builder.add_node('venture_architect',   venture_architect_node)
builder.add_node('sre_infra',           sre_infra_node)
builder.add_node('assembler',           game_assembler_node)
builder.add_node('value_chain_enricher', value_chain_enricher_node)

builder.set_entry_point('venture_architect')
builder.add_edge('venture_architect',    'sre_infra')
builder.add_edge('sre_infra',            'assembler')
builder.add_edge('assembler',            'value_chain_enricher')
builder.add_edge('value_chain_enricher', END)

game_generator = builder.compile()
print('✅ Generation pipeline: venture_architect → sre_infra → assembler → value_chain_enricher')
