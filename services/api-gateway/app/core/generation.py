# Core business logic only
from app.storage.vector_store import vectorstore, similarity_search

from typing import TypedDict, List, Dict, Any
import json
import copy
import random
from langgraph.graph import StateGraph, END
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from app.config import settings


class GameCreationState(TypedDict):
    user_prompt: str
    company_data: Dict[str, Any]
    infra_data: Dict[str, Any]
    final_gamestate: Dict[str, Any]


gen_llm = ChatOpenAI(model="gpt-4o", temperature=0.7, api_key=settings.OPENAI_API_KEY)

fintech_retriever = vectorstore.as_retriever(search_kwargs={'filter': {'agent': 'fintech'}, 'k': 3})
tech_retriever = vectorstore.as_retriever(search_kwargs={'filter': {'agent': 'techno'}, 'k': 10})


# ── Validators ──

def validate_type_distribution(nodes: list) -> None:
    types = [n.get("type") for n in nodes]
    if "entry" not in types or "database" not in types:
        raise ValueError("Must have entry and database node types")


def validate_core_db_edges(nodes: list, edges: list) -> None:
    core_db = next((n for n in nodes if n.get("type") == "database"), None)
    if core_db:
        edge_count = sum(
            1 for e in edges
            if e.get("from") == core_db["id"] or e.get("to") == core_db["id"]
        )
        if edge_count < 1:
            raise ValueError("Core DB must have at least 1 connected edge")


def validate_vulns(vulnerabilities: list, nodes: list) -> None:
    core_db = next((n for n in nodes if n.get("type") == "database"), None)
    if core_db:
        for vuln in vulnerabilities:
            if vuln.get("node_id") == core_db["id"]:
                raise ValueError("Core DB cannot have vulnerabilities")


def validate_fog(nodes: list) -> None:
    total = len(nodes)
    fogged = sum(1 for n in nodes if n.get("fogged"))
    print(f"Fog validation: {fogged}/{total} nodes fogged")


def wire_flows(nodes: list, base_flows: list = None) -> list:
    if base_flows is None:
        base_flows = []
    entry = next((n for n in nodes if n.get("type") == "entry"), None)
    core = next((n for n in nodes if n.get("type") == "database"), None)
    flows = [
        {
            "name": "Primary Flow",
            "node_path": [entry["id"], core["id"]] if entry and core else [],
            "base_revenue": 50,
            "is_active": True,
            "current_revenue": 35,
        }
    ] if entry and core else []
    return flows


# ── Agent 1: Venture Architect ──

def venture_architect_node(state: GameCreationState):
    print("🚀 [Venture Architect] Generating startup concept...")

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
    - CASH: 4500-6000 €K.
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

    chain = ({"context": fintech_retriever, "input": RunnablePassthrough()} | prompt | gen_llm | JsonOutputParser())
    result = chain.invoke(state["user_prompt"])
    return {"company_data": result}


# ── Agent 2: Lead SRE ──

def sre_infra_node(state: GameCreationState):
    print("🛠️ [Lead SRE] Provisioning infrastructure...")

    tech_docs = tech_retriever.invoke("gateway database server middleware vendor human fintech infrastructure")
    tech_context = "\n".join([d.page_content for d in tech_docs])

    prompt = ChatPromptTemplate.from_template("""
    You are the Lead SRE. Build an infra that has survived 2 years.

    COMPANY: {specs}
    TECH DATABASE: {tech_context}

    STRICT RULES:
    - 7 nodes total. Node IDs: n1 through n7.
    - TYPE DISTRIBUTION (mandatory):
      * Exactly 1 "entry" node (API gateway / load balancer)
      * Exactly 1 "human" node (HR portal, admin panel — low defense, phishing target)
      * Exactly 1 "vendor" node (external third-party service)
      * Exactly 1 "database" node — this is the Core DB, mark it clearly in the name
      * 3 nodes of type "middleware" or "server" (mix as you see fit)
    - STATS: All integers 1-10. No node should have ALL stats high — each has a tradeoff.
      * "human" nodes: defense 1-3, throughput 2-4
      * "vendor" nodes: visibility 2-4 (opaque third-party)
      * "database" (Core DB): defense 7-9, throughput 8-10, cost 6-8
    - EDGES: 8-10 edges. Core DB must have 3+ edges. No orphan nodes.
      Include at least one "lateral" path (entry → human → middleware) for Byte.
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

    chain = (prompt | gen_llm | JsonOutputParser())
    result = chain.invoke({"specs": json.dumps(state["company_data"]), "tech_context": tech_context})
    return {"infra_data": result}


# ── Agent 3: Assembler (DETERMINISTIC) ──

def game_assembler_node(state: GameCreationState):
    print("🏁 [Assembler] Validating GDD compliance & wiring flows...")

    comp = state["company_data"]
    infra = state["infra_data"]
    nodes = infra["nodes"]

    # ── FIX: Flatten any nested stats/tags from LLM ──
    for n in nodes:
        if "stats" in n:
            n.update(n.pop("stats"))
        if "tags" in n:
            n.update(n.pop("tags"))
        for tag in ["compromised", "locked", "offline", "isolated", "fogged", "has_mfa", "monitored"]:
            n.setdefault(tag, False)
        n.setdefault("offline_turns", 0)

    types_present = {n["type"] for n in nodes}

    node_map = {n["id"]: n for n in nodes}

    # ── VALIDATE: Core DB has 3+ edges ──
    core_db = next((n for n in nodes if n["type"] == "database"), None)
    if core_db:
        core_edges = sum(1 for e in infra["edges"] if e["from"] == core_db["id"] or e["to"] == core_db["id"])
        if core_edges < 3:
            print(f"  ⚠️ Core DB {core_db['id']} has {core_edges} edges (need 3+) — adding edges")
            other_ids = [n["id"] for n in nodes if n["id"] != core_db["id"]]
            while core_edges < 3 and other_ids:
                target = other_ids.pop(0)
                edge = {"from": core_db["id"], "to": target}
                rev_edge = {"from": target, "to": core_db["id"]}
                existing = {(e["from"], e["to"]) for e in infra["edges"]}
                if (edge["from"], edge["to"]) not in existing and (rev_edge["from"], rev_edge["to"]) not in existing:
                    infra["edges"].append(edge)
                    core_edges += 1

    # ── VALIDATE: Vulns severity 1-3 only, not on Core DB ──
    vulns = infra.get("vulnerabilities", [])
    vulns = [v for v in vulns if v.get("severity", 1) in [1, 2, 3]]
    if core_db:
        vulns = [v for v in vulns if v.get("node_id") != core_db["id"]]
    eligible_for_vulns = [n["id"] for n in nodes if n["type"] != "database"]
    while len(vulns) < 3 and eligible_for_vulns:
        nid = random.choice(eligible_for_vulns)
        if nid not in {v["node_id"] for v in vulns}:
            vulns.append({"node_id": nid, "severity": random.randint(1, 3), "known_by_player": False})
    vulns = vulns[:5]

    # ── VALIDATE: Fog 30-50% ──
    num_nodes = len(nodes)
    target_fog = random.randint(max(2, num_nodes * 3 // 10), num_nodes * 5 // 10)
    for n in nodes:
        n["fogged"] = False
    foggable = [n for n in nodes if n["type"] not in ("entry",)]
    random.shuffle(foggable)
    for n in foggable[:target_fog]:
        n["fogged"] = True
    actual_fog = sum(1 for n in nodes if n["fogged"])
    print(f"  📊 Fog: {actual_fog}/{num_nodes} ({100*actual_fog//num_nodes}%)")

    # ── WIRE FLOWS to actual node IDs ──
    type_nodes = {}
    for n in nodes:
        type_nodes.setdefault(n["type"], []).append(n["id"])

    all_node_ids = [n["id"] for n in nodes]
    final_flows = []
    used_paths = set()

    for f in comp.get("flows", [])[:4]:
        path_ids = []
        for t in f.get("node_path_types", ["entry", "middleware", "database"]):
            candidates = type_nodes.get(t, type_nodes.get("server", type_nodes.get("middleware", [])))
            pick = next((nid for nid in candidates if nid not in path_ids), None)
            if pick is None:
                pick = next((nid for nid in all_node_ids if nid not in path_ids), None)
            if pick is None:
                continue
            path_ids.append(pick)

        if len(path_ids) < 2:
            continue

        path_key = tuple(path_ids)
        if path_key in used_paths and len(path_ids) > 2:
            mid_idx = len(path_ids) // 2
            mid_type = next((n["type"] for n in nodes if n["id"] == path_ids[mid_idx]), "middleware")
            alts = [nid for nid in type_nodes.get(mid_type, []) + all_node_ids if nid != path_ids[mid_idx] and nid not in path_ids]
            if alts:
                path_ids[mid_idx] = alts[0]
        used_paths.add(tuple(path_ids))

        tp_values = [node_map[pid]["throughput"] for pid in path_ids if pid in node_map]
        tp_min = min(tp_values) if tp_values else 5
        base_rev = f.get("base_revenue", random.randint(15, 50))
        base_rev = max(5, min(50, base_rev))

        is_active = all(
            not node_map.get(pid, {}).get("locked") and
            not node_map.get(pid, {}).get("offline") and
            not node_map.get(pid, {}).get("isolated")
            for pid in path_ids
        )

        final_flows.append({
            "name": f.get("name", f"Flow {len(final_flows)+1}"),
            "node_path": path_ids,
            "base_revenue": base_rev,
            "is_active": is_active,
            "current_revenue": int(base_rev * tp_min / 10) if is_active else 0
        })

    if not final_flows:
        final_flows = wire_flows(nodes, comp.get("flows", []))

    # ── Byte setup ──
    adversary = comp.get("adversary", "script_kiddie")
    byte_ap = 3 if adversary == "state" else 2
    entries = [n["id"] for n in nodes if n["type"] in ("entry", "human")]

    # ── Assemble final state ──
    game_state = {
        "company": {
            "name": comp.get("name", "UnnamedCorp"),
            "description": comp.get("description", ""),
            "sector": comp.get("sector", "payments"),
            "adversary": adversary,
            "cash": max(3000, min(6000, comp.get("cash", 5000))),
            "turn": 1,
            "compliance": 0.7,
            "reputation": 0.8,
            "insurance_active": False,
            "insurance_premium": 0,
            "breach_reported": False,
        },
        "nodes": nodes,
        "edges": infra.get("edges", []),
        "flows": final_flows,
        "vulnerabilities": vulns,
        "byte": {"byte_presence": {}, "byte_ap": byte_ap, "byte_active_ops": []},
        "regulator": {"breach_timer": None, "deletion_requested": False},
        "effects": [],
        "turn_log": [{
            "source": "system", "action": "INIT", "target": None,
            "message": f"{comp.get('name', '?')} generated. Adversary: {adversary}. Entry points: {entries}",
            "visible_to_player": True
        }],
    }

    print(f"  ✅ Nodes: {len(nodes)} | Edges: {len(game_state['edges'])} | Flows: {len(final_flows)}")
    print(f"  ✅ Vulns: {len(vulns)} (severity range: {min(v['severity'] for v in vulns) if vulns else 0}-{max(v['severity'] for v in vulns) if vulns else 0})")
    print(f"  ✅ Types: {', '.join(sorted(types_present))}")
    print(f"  ✅ Byte AP: {byte_ap} | Entries: {entries}")
    if core_db:
        final_core_edges = sum(1 for e in game_state["edges"] if e["from"] == core_db["id"] or e["to"] == core_db["id"])
        print(f"  ✅ Core DB: {core_db['id']} ({core_db['name']}) — {final_core_edges} edges")

    return {"final_gamestate": game_state}


# ── Build the Entity Gen Graph ──

builder = StateGraph(GameCreationState)
builder.add_node("venture_architect", venture_architect_node)
builder.add_node("sre_infra", sre_infra_node)
builder.add_node("assembler", game_assembler_node)

builder.set_entry_point("venture_architect")
builder.add_edge("venture_architect", "sre_infra")
builder.add_edge("sre_infra", "assembler")
builder.add_edge("assembler", END)

game_generator = builder.compile()
print("✅ Entity Gen pipeline: venture_architect → sre_infra → assembler")