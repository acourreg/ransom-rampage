# Merged from app/engine/resolvers.py + revenue.py + orchestrator.py
# Core business logic only

from typing import List, Dict, Any, Tuple
import copy


def extract_mutations(agent_recommendation: dict) -> list:
    """
    Extract and validate mutations from agent recommendation.

    Validates:
    - Input is dict with 'mutations' key containing list of dicts.
    - Each mutation has required keys: 'node_id' (str), 'attribute' (str), 'value' (int/float/bool).
    - Ignores invalid entries (e.g., missing keys, wrong types).

    Returns list of valid mutation dicts, or empty list if invalid input.
    """
    if not isinstance(agent_recommendation, dict):
        return []

    mutations = agent_recommendation.get('mutations', [])
    if not isinstance(mutations, list):
        return []

    valid_mutations = []
    for mut in mutations:
        if not isinstance(mut, dict):
            continue
        required_keys = ['node_id', 'attribute', 'value']
        if not all(key in mut for key in required_keys):
            continue
        node_id = mut['node_id']
        attribute = mut['attribute']
        value = mut['value']
        if not isinstance(node_id, str) or not isinstance(attribute, str):
            continue
        if not isinstance(value, (int, float, bool)):
            continue
        valid_mutations.append({
            'node_id': node_id,
            'attribute': attribute,
            'value': value
        })
    return valid_mutations


def apply_mutations(state: dict, mutations: list) -> tuple:
    """
    Apply mutations IN-PLACE on state (no deepcopy — caller is responsible).
    Returns: (state, list_of_applied_mutations)
    """
    applied = []

    raw_nodes = state.get('nodes', [])
    node_map = {n['id']: n for n in raw_nodes if isinstance(n, dict) and 'id' in n}

    for mut in mutations:
        node_id = mut.get('node_id')
        attribute = mut.get('attribute')
        value = mut.get('value')

        if not node_id or not attribute or node_id not in node_map:
            continue

        node = node_map[node_id]

        # Create attribute if missing (LLM may set tags not yet present)
        if attribute not in node:
            node[attribute] = False if isinstance(value, bool) else 0

        old_value = node[attribute]

        # Convert numpy types
        if hasattr(value, 'item'):
            value = value.item()

        # Clamp int attributes to valid ranges
        if attribute in ('defense', 'visibility', 'cost', 'compliance_score', 'throughput'):
            value = int(max(0, min(10, value)))
        elif isinstance(value, bool) or attribute in ('compromised', 'locked', 'offline', 'isolated', 'fogged', 'has_mfa', 'monitored', 'has_backdoor'):
            value = bool(value)

        node[attribute] = value
        applied.append({
            'node_id': node_id,
            'attribute': attribute,
            'old_value': old_value,
            'new_value': value
        })

    return state, applied


def calculate_revenue(state: dict) -> dict:
    """
    GDD §10 Revenue + Cash reconciliation.
    Revenue: base × min_throughput_in_path / 10 (NOT /100).
    Costs: sum(node.cost × 5) + sum(effect.cost_per_turn).
    Cash: += total_revenue - total_costs
    Returns: {total_revenue, total_costs, net_income, cash}
    """
    company = state.get('company', {})
    nodes = state.get('nodes', [])
    node_map = {n['id']: n for n in nodes if isinstance(n, dict) and 'id' in n}
    flows = state.get('flows', [])
    effects = state.get('effects', [])

    # 1. Revenue per flow (GDD §10)
    total_revenue = 0
    for flow in flows:
        path = flow.get('node_path', [])
        if not path:
            flow['is_active'] = False
            flow['current_revenue'] = 0
            continue

        flow['is_active'] = all(
            not node_map.get(nid, {}).get('offline', False) and
            not node_map.get(nid, {}).get('locked', False) and
            not node_map.get(nid, {}).get('isolated', False)
            for nid in path
        )

        if not flow['is_active']:
            flow['current_revenue'] = 0
            continue

        throughputs = [int(node_map.get(nid, {}).get('throughput', 5)) for nid in path]
        min_tp = min(throughputs) if throughputs else 5
        base = flow.get('base_revenue', 0)
        flow['current_revenue'] = int(base * min_tp / 10)  # GDD: /10 not /100
        total_revenue += flow['current_revenue']

    # 2. Operational costs (GDD §10: cost × 5 per node per turn)
    node_costs = sum(int(n.get('cost', 0)) * 5 for n in nodes)
    effect_costs = sum(int(e.get('cost_per_turn', 0)) for e in effects)
    total_costs = node_costs + effect_costs

    # 3. Net income
    net_income = total_revenue - total_costs
    company['cash'] = max(0, int(company.get('cash', 0)) + net_income)

    return {
        'total_revenue': total_revenue,
        'total_costs': total_costs,
        'node_costs': node_costs,
        'effect_costs': effect_costs,
        'net_income': net_income,
        'net_revenue': net_income,  # alias for backwards compat
        'cash': company['cash']
    }


def execute_turn(state: dict, player_action_id: str, agent_recommendations: dict) -> dict:
    """
    Execute a complete turn: Tick → Byte → Regulator → Player → Revenue → Win/Lose.
    GDD §4 turn structure + §10 resolution + §12 win/lose conditions.

    Returns: updated state with turn_log, snapshots, game_over flag.
    """
    new_state = copy.deepcopy(state)
    company = new_state['company']
    regulator = new_state.setdefault('regulator', {})
    nodes = new_state['nodes']
    node_map = {n['id']: n for n in nodes}

    # Normalize
    if regulator.get('breach_timer') is None:
        regulator['breach_timer'] = 0

    # ── Phase 0: TICK (GDD §4 step 1) ──
    for n in nodes:
        ot = n.get('offline_turns', 0)
        if ot > 0:
            n['offline_turns'] = ot - 1
            if n['offline_turns'] == 0:
                n['offline'] = False

    effects = new_state.get('effects', [])
    for e in effects:
        e['turns_remaining'] = e.get('turns_remaining', 0) - 1
    new_state['effects'] = [e for e in effects if e['turns_remaining'] > 0]

    # ── Phase 1: BYTE (GDD §4 step 2) ──
    byte_rec = agent_recommendations.get('byte', agent_recommendations.get('hacker', {'mutations': []}))
    byte_mutations = extract_mutations(byte_rec)
    _, applied_byte = apply_mutations(new_state, byte_mutations)
    breach_occurred = len(applied_byte) > 0

    # ── Phase 2: REGULATOR (GDD §4 step 3) ──
    turn_num = company.get('turn', 0) + 1

    if breach_occurred:
        regulator['breach_timer'] = regulator.get('breach_timer', 0) + 1

    if regulator['breach_timer'] > 0:
        regulator['breach_timer'] -= 1
        if regulator['breach_timer'] == 0 and not company.get('breach_reported', False):
            fine = min(2000, 500 + turn_num * 150)
            company['cash'] = max(0, company.get('cash', 0) - fine)
            company['compliance'] = max(0, company.get('compliance', 0.7) - 0.10)

    forced_audit = company.get('compliance', 0.7) < 0.5

    if company.get('compliance', 0.7) < 0.2:
        worst = min(nodes, key=lambda n: n.get('compliance_score', 5))
        worst['offline'] = True
        worst['offline_turns'] = 3

    deletion_event = None
    if turn_num in (6, 7) and not regulator.get('deletion_requested'):
        regulator['deletion_requested'] = True
        deletion_event = "DELETION_REQUEST"

    # ── Phase 3: PLAYER (GDD §4 step 5) ──
    if not forced_audit:
        if player_action_id in agent_recommendations:
            player_mutations = extract_mutations(agent_recommendations[player_action_id])
        else:
            player_mutations = []
        _, applied_player = apply_mutations(new_state, player_mutations)
    else:
        applied_player = []

    # ── Phase 4: REVENUE + COSTS (GDD §10) ──
    financials = calculate_revenue(new_state)

    # ── Phase 5: COMPLIANCE DRIFT (GDD §10) ──
    online_nodes = [n for n in nodes if not n.get('offline')]
    if online_nodes:
        avg_comp = sum(n.get('compliance_score', 5) for n in online_nodes) / len(online_nodes) / 10
        company['compliance'] = max(0, min(1,
            company.get('compliance', 0.7) + (avg_comp - company.get('compliance', 0.7)) * 0.1
        ))

    # ── Phase 6: WIN/LOSE CHECK (GDD §12) ──
    company['turn'] = turn_num
    game_over = False
    game_over_reason = None

    core_db = next((n for n in nodes if n.get('type') == 'database'), None)

    if company.get('cash', 0) <= 0:
        game_over, game_over_reason = True, "💀 Faillite — cash ≤ 0"
    elif company.get('compliance', 0.7) <= 0:
        game_over, game_over_reason = True, "⚖️ Shutdown réglementaire — compliance ≤ 0"
    elif company.get('reputation', 0.8) <= 0:
        game_over, game_over_reason = True, "📉 Exode clients — reputation ≤ 0"
    elif core_db and core_db.get('locked'):
        game_over, game_over_reason = True, "🔒 Breach — Core DB locked, game over"
    elif turn_num > 10:
        if (company.get('cash', 0) > 0 and
                company.get('compliance', 0.7) > 0.5 and
                company.get('reputation', 0.8) > 0.3):
            game_over, game_over_reason = True, "🏆 VICTOIRE — survécu 10 tours !"
        else:
            game_over, game_over_reason = True, "❌ Défaite — survécu mais pas assez solide"

    # ── Phase 7: TURN LOG ──
    log_entry = {
        'turn': turn_num,
        'byte_mutations_applied': len(applied_byte),
        'breach_occurred': breach_occurred,
        'breach_timer': regulator['breach_timer'],
        'deletion_requested': regulator.get('deletion_requested', False),
        'deletion_event': deletion_event,
        'forced_audit': forced_audit,
        'player_action_id': player_action_id if not forced_audit else "BLOCKED_BY_AUDIT",
        'player_mutations_applied': len(applied_player),
        'financials': financials,
        'company_metrics': {
            'cash': company.get('cash', 0),
            'reputation': company.get('reputation', 0.8),
            'compliance': company.get('compliance', 0.7),
        },
        'game_over': game_over,
        'game_over_reason': game_over_reason,
    }
    new_state.setdefault('turn_log', []).append(log_entry)

    new_state.setdefault('snapshots', []).append({
        'turn': turn_num,
        'cash': company.get('cash', 0),
        'reputation': company.get('reputation', 0.8),
        'compliance': company.get('compliance', 0.7),
        'net_income': financials.get('net_income', 0),
    })

    new_state['game_over'] = game_over
    new_state['game_over_reason'] = game_over_reason

    return new_state