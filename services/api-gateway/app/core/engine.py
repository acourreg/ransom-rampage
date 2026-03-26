# Core game engine — turn resolution, mutation primitives, revenue, win/lose.
# game_service is the only caller: engine owns all GDD business logic.

from typing import List, Dict, Any, Tuple
import copy
import random


# ══════════════════════════════════════════════════════════════
# MUTATION PRIMITIVES (public — used by engine + tests)
# ══════════════════════════════════════════════════════════════

def extract_mutations(agent_recommendation: dict) -> list:
    """Validate and extract mutations from an agent recommendation dict."""
    if not isinstance(agent_recommendation, dict):
        return []
    mutations = agent_recommendation.get('mutations', [])
    if not isinstance(mutations, list):
        return []
    valid = []
    for mut in mutations:
        if not isinstance(mut, dict):
            continue
        if not all(k in mut for k in ('node_id', 'attribute', 'value')):
            continue
        if not isinstance(mut['node_id'], str) or not isinstance(mut['attribute'], str):
            continue
        if not isinstance(mut['value'], (int, float, bool)):
            continue
        valid.append({'node_id': mut['node_id'], 'attribute': mut['attribute'], 'value': mut['value']})
    return valid


def apply_mutations(state: dict, mutations: list) -> tuple:
    """
    Apply mutations IN-PLACE on state (caller is responsible for isolation).
    Returns: (state, list_of_applied_mutations_with_old_value)
    """
    applied = []
    node_map = {n['id']: n for n in state.get('nodes', []) if isinstance(n, dict) and 'id' in n}

    for mut in mutations:
        node_id   = mut.get('node_id')
        attribute = mut.get('attribute')
        value     = mut.get('value')
        if not node_id or not attribute or node_id not in node_map:
            continue

        node = node_map[node_id]
        if attribute not in node:
            # All boolean flags (including 'fogged') are guaranteed present by _normalize_nodes
            # + _distribute_fog in generation.py. This init is a safety net for legacy states.
            node[attribute] = False if isinstance(value, bool) else 0

        old_value = node[attribute]
        if hasattr(value, 'item'):
            value = value.item()

        if attribute in ('defense', 'visibility', 'cost', 'compliance_score', 'throughput'):
            value = int(max(0, min(10, value)))
        elif isinstance(value, bool) or attribute in (
            'compromised', 'locked', 'offline', 'isolated', 'fogged',
            'has_mfa', 'monitored', 'has_backdoor'
        ):
            value = bool(value)

        node[attribute] = value
        applied.append({'node_id': node_id, 'attribute': attribute, 'old_value': old_value, 'new_value': value})

    return state, applied


# ══════════════════════════════════════════════════════════════
# REVENUE (public)
# ══════════════════════════════════════════════════════════════

def calculate_revenue(state: dict) -> dict:
    """
    GDD §10 — Revenue + Cash reconciliation.
    Revenue: base × min_throughput_in_path / 10.
    Costs: sum(node.cost × 5) + sum(effect.cost_per_turn).
    Mutates state in-place; returns financials dict.
    """
    company  = state.get('company', {})
    nodes    = state.get('nodes', [])
    node_map = {n['id']: n for n in nodes if isinstance(n, dict) and 'id' in n}
    flows    = state.get('flows', [])
    effects  = state.get('effects', [])

    total_revenue = 0
    for flow in flows:
        path = flow.get('node_path', [])
        if not path:
            flow['is_active'] = False
            flow['current_revenue'] = 0
            continue

        flow['is_active'] = all(
            not node_map.get(nid, {}).get('offline') and
            not node_map.get(nid, {}).get('locked') and
            not node_map.get(nid, {}).get('isolated')
            for nid in path
        )
        if not flow['is_active']:
            flow['current_revenue'] = 0
            continue

        min_tp = min(int(node_map.get(nid, {}).get('throughput', 5)) for nid in path)
        base   = flow.get('base_revenue', 0)
        flow['current_revenue'] = int(base * min_tp / 10)
        total_revenue += flow['current_revenue']

    node_costs   = sum(int(n.get('cost', 0)) * 5 for n in nodes)
    effect_costs = sum(int(e.get('cost_per_turn', 0)) for e in effects)
    total_costs  = node_costs + effect_costs
    net_income   = total_revenue - total_costs
    company['cash'] = max(0, int(company.get('cash', 0)) + net_income)

    # Per-node revenue exposure
    for n in nodes:
        n['revenue_exposure'] = sum(
            f['current_revenue'] for f in flows
            if n['id'] in f.get('node_path', []) and f.get('is_active')
        )

    # Flow risk_level
    vuln_node_ids = {v['node_id'] for v in state.get('vulnerabilities', [])}
    for flow in flows:
        path_nodes = [node_map.get(nid) for nid in flow.get('node_path', []) if nid in node_map]
        if any(n.get('compromised') for n in path_nodes if n):
            flow['risk_level'] = 'critical'
        elif any(nid in vuln_node_ids for nid in flow.get('node_path', [])) or \
             any(n.get('defense', 10) < 5 for n in path_nodes if n):
            flow['risk_level'] = 'high'
        elif any(n.get('fogged') for n in path_nodes if n):
            flow['risk_level'] = 'unknown'
        else:
            flow['risk_level'] = 'low'

    company['total_revenue_at_risk'] = sum(
        f['current_revenue'] for f in flows
        if f.get('risk_level') in ('critical', 'high')
    )

    return {
        'total_revenue': total_revenue,
        'total_costs':   total_costs,
        'node_costs':    node_costs,
        'effect_costs':  effect_costs,
        'net_income':    net_income,
        'net_revenue':   net_income,
        'cash':          company['cash'],
    }


# ══════════════════════════════════════════════════════════════
# GDD PLAYER ACTION RESOLUTION (private — only called by execute_turn)
# ══════════════════════════════════════════════════════════════

def _add_effect(state: dict, effect: dict) -> None:
    """Add / refresh a paradigm effect (replaces same name if exists)."""
    effects = state.setdefault('effects', [])
    effects[:] = [e for e in effects if e.get('name') != effect.get('name')]
    effects.append(effect)
    print(f"[EFFECT] added: {effect['name']} ({effect['turns_remaining']} turns)")


def _resolve_player_action(action_id: str, target: str | None, state: dict) -> list:
    """
    Deterministic GDD rules for all CTO / CISO / SRE actions.
    Mutates state directly for non-node effects (cash, timers, effects list).
    Returns mutation list for apply_mutations().
    """
    nodes = {n['id']: n for n in state.get('nodes', [])}
    node  = nodes.get(target) if target else None

    print(f"[_resolve] action={action_id} target={target} node_found={node is not None}")

    # ── CTO TACTICAL ──

    if action_id == 'C1':   # Report Breach
        state['company']['breach_reported'] = True
        state['regulator']['breach_timer']  = 0
        state['company']['reputation'] = max(0.0, float(state['company'].get('reputation', 0.8)) - 0.05)
        print('[C1] breach_timer reset, reputation -0.05')
        return []

    if action_id == 'C2' and node:  # Boost Throughput
        cur = node.get('throughput', 5)
        if not isinstance(cur, int) or cur >= 10:
            print(f'[C2] throughput already maxed on {target}')
            return []
        return [{'node_id': target, 'attribute': 'throughput', 'value': min(10, cur + 2)}]

    if action_id == 'C3' and node:  # Patch Vuln
        vulns = state.get('vulnerabilities', [])
        known = [v for v in vulns if v.get('node_id') == target and v.get('known_by_player')]
        if not known:
            print(f'[C3] no known vuln on {target} — no-op')
            return []
        vulns.remove(known[0])
        print(f'[C3] removed vuln sev={known[0].get("severity")} from {target}')
        return [
            {'node_id': target, 'attribute': 'offline',       'value': True},
            {'node_id': target, 'attribute': 'offline_turns', 'value': 1},
        ]

    if action_id == 'C4' and node:  # Cut Costs
        cur = node.get('cost', 5)
        if isinstance(cur, int):
            return [{'node_id': target, 'attribute': 'cost', 'value': max(1, cur - 1)}]
        return []

    if action_id == 'C5' and node:  # Evict Attacker
        if not node.get('compromised'):
            print(f'[C5] {target} not compromised — no-op')
            return []
        result = [{'node_id': target, 'attribute': 'compromised', 'value': False}]
        edges = state.get('edges', [])
        adjacency: dict[str, set] = {}
        for e in edges:
            frm, to = e.get('from'), e.get('to')
            if frm and to:
                adjacency.setdefault(frm, set()).add(to)
                adjacency.setdefault(to, set()).add(frm)
        for nid in adjacency.get(target, set()):
            lateral = nodes.get(nid)
            if not lateral or not lateral.get('compromised'):
                continue
            other_foothold = [
                adj for adj in adjacency.get(nid, set())
                if adj != target and nodes.get(adj, {}).get('compromised')
            ]
            if not other_foothold:
                result.append({'node_id': nid, 'attribute': 'compromised', 'value': False})
                print(f'[C5] lateral clear: {nid}')
        return result

    if action_id == 'C6' and node:  # Pay Ransom
        if not node.get('locked'):
            print(f'[C6] {target} not locked — no-op')
            return []
        state['company']['cash'] = max(0, int(state['company'].get('cash', 0)) - 200)
        state['company']['reputation'] = max(0.0, float(state['company'].get('reputation', 0.8)) - 0.10)
        return [{'node_id': target, 'attribute': 'locked', 'value': False}]

    if action_id == 'C7' and node:  # Reinforce
        cur = node.get('defense', 5)
        if not isinstance(cur, int) or cur >= 9:
            print(f'[C7] defense already maxed on {target}')
            return []
        new_val = min(10, cur + 3)
        print(f'[C7 REINFORCE] {target} defense: {cur} → {new_val}')
        return [{'node_id': target, 'attribute': 'defense', 'value': new_val}]

    if action_id == 'C8' and node:  # Deploy MFA
        if node.get('has_mfa'):
            print(f'[C8] MFA already on {target}')
            return []
        new_def = min(10, int(node.get('defense', 5)) + 4)
        print(f'[C8 MFA] {target} defense: {node.get("defense")} → {new_def}')
        return [
            {'node_id': target, 'attribute': 'has_mfa',  'value': True},
            {'node_id': target, 'attribute': 'defense',  'value': new_def},
        ]

    if action_id == 'C9':   # Do Nothing
        unfogged = [n for n in state.get('nodes', []) if not n.get('fogged')]
        if unfogged:
            victim = random.choice(unfogged)
            return [{'node_id': victim['id'], 'attribute': 'fogged', 'value': True}]
        return []

    # ── CISO TACTICAL ──

    if action_id == 'S1' and node:  # Scan
        discovered = []
        for v in state.get('vulnerabilities', []):
            if v.get('node_id') == target:
                v['known_by_player'] = True
                discovered.append(f"sev={v.get('severity')}")
        fog_was = node.get('fogged', False)
        print(f'[S1 SCAN] target={target} fogged_was={fog_was} vulns_revealed={discovered or "none"}')
        return [{'node_id': target, 'attribute': 'fogged', 'value': False}]

    if action_id == 'S3' and node:  # Harden
        cur = node.get('defense', 5)
        return [{'node_id': target, 'attribute': 'defense',
                 'value': min(10, int(cur) + 3 if isinstance(cur, int) else 8)}]

    # ── CISO PARADIGM SHIFTS ──

    if action_id == 'S2':   # Zero Trust Mode
        _add_effect(state, {'name': 'zero_trust', 'turns_remaining': 4, 'cost_per_turn': 0,
                            'description': 'Zero Trust: compromised nodes auto-isolated'})
        return []

    if action_id == 'S4' and node:  # Honeypot
        _add_effect(state, {'name': f'honeypot_{target}', 'node_id': target, 'turns_remaining': 3,
                            'cost_per_turn': 0,
                            'description': f"Honeypot on {node.get('business_name', target)}"})
        edges = state.get('edges', [])
        adjacent = [
            e.get('to') if e.get('from') == target else e.get('from')
            for e in edges if target in (e.get('from'), e.get('to'))
        ]
        return [{'node_id': adj, 'attribute': 'fogged', 'value': False}
                for adj in adjacent if adj and adj in nodes]

    if action_id == 'S5':   # SOC Contract
        _add_effect(state, {'name': 'soc_contract', 'turns_remaining': 4, 'cost_per_turn': 0,
                            'description': 'SOC Contract: Byte position revealed each turn'})
        return [{'node_id': n['id'], 'attribute': 'fogged', 'value': False}
                for n in state.get('nodes', [])]

    if action_id == 'S6':   # IR Retainer
        _add_effect(state, {'name': 'ir_retainer', 'turns_remaining': 3, 'cost_per_turn': 0,
                            'description': 'IR Retainer: no fines for 3 turns'})
        state['regulator']['breach_timer'] = 0
        return []

    # ── SRE TACTICAL ──

    if action_id == 'E1' and node:  # Optimize
        cur = node.get('throughput', 5)
        if isinstance(cur, int):
            return [{'node_id': target, 'attribute': 'throughput', 'value': min(10, cur + 2)}]
        return []

    if action_id == 'E2' and node:  # Restore
        return [
            {'node_id': target, 'attribute': 'locked',        'value': False},
            {'node_id': target, 'attribute': 'offline',       'value': False},
            {'node_id': target, 'attribute': 'offline_turns', 'value': 0},
        ]

    # ── SRE PARADIGM SHIFTS ──

    if action_id == 'E3':   # Full Observability
        _add_effect(state, {'name': 'full_observability', 'turns_remaining': 4, 'cost_per_turn': 10,
                            'description': 'Full Observability: all nodes visible'})
        mutations = []
        for n in state.get('nodes', []):
            mutations.append({'node_id': n['id'], 'attribute': 'visibility', 'value': 9})
            mutations.append({'node_id': n['id'], 'attribute': 'fogged',     'value': False})
        return mutations

    if action_id == 'E4':   # Auto-Failover
        _add_effect(state, {'name': 'auto_failover', 'turns_remaining': 5, 'cost_per_turn': 0,
                            'description': 'Auto-Failover: 70% revenue preserved if node offline'})
        return []

    if action_id == 'E5':   # Infrastructure Freeze
        _add_effect(state, {'name': 'infra_freeze', 'turns_remaining': 1, 'cost_per_turn': 0,
                            'description': 'Infra Freeze: DDoS blocked this turn'})
        return []

    if action_id == 'E6':   # Cost Optimization Drive
        return [
            {'node_id': n['id'], 'attribute': 'cost', 'value': max(1, n.get('cost', 5) - 1)}
            for n in state.get('nodes', [])
            if isinstance(n.get('cost'), int)
        ]

    print(f'[_resolve] ⚠ no handler for action_id={action_id}')
    return []


def resolve_player_mutations(action_id: str, target: str | None, state: dict) -> list:
    """
    Public thin wrapper around _resolve_player_action.
    For use by game_service ONLY for pre-engine logging — does NOT modify state.
    Receives a deepcopy of state so side-effects are discarded.
    """
    return _resolve_player_action(action_id, target, copy.deepcopy(state))


# ══════════════════════════════════════════════════════════════
# TURN PHASE HELPERS (private)
# ══════════════════════════════════════════════════════════════

def _tick_state(state: dict) -> None:
    """
    Phase 0 — Timers & active effects.
    • Decrement offline_turns; bring nodes back online when counter hits 0.
    • Tick down effect turns_remaining; prune expired effects.
    • Apply active paradigm effects (zero_trust, soc_contract, ir_retainer, infra_freeze).
    """
    nodes    = state.get('nodes', [])
    regulator = state.setdefault('regulator', {})

    for n in nodes:
        ot = n.get('offline_turns', 0)
        if ot > 0:
            n['offline_turns'] = ot - 1
            if n['offline_turns'] == 0:
                n['offline'] = False

    effects = state.get('effects', [])
    for e in effects:
        e['turns_remaining'] = e.get('turns_remaining', 0) - 1
    state['effects'] = [e for e in effects if e['turns_remaining'] > 0]

    active = {e.get('name'): e for e in state['effects']}

    if 'zero_trust' in active:
        for n in nodes:
            if n.get('compromised') and not n.get('isolated'):
                n['isolated'] = True
                print(f"[EFFECT zero_trust] auto-isolated {n['id']}")

    if 'soc_contract' in active or 'full_observability' in active:
        for n in nodes:
            n['fogged'] = False

    if 'ir_retainer' in active:
        regulator['breach_timer'] = 0
        print('[EFFECT ir_retainer] breach_timer reset')

    if 'infra_freeze' in active:
        state['_infra_freeze_active'] = True
        print('[EFFECT infra_freeze] B4 DDoS blocked this turn')


def _apply_byte_action(pending: dict, state: dict, node_map: dict) -> list:
    """
    Resolve a previously queued Byte action (from _pending_byte_action).
    Mutates state in-place (nodes via node_map). Returns list of applied mutations.
    """
    byte_action = pending.get('action_id', 'B1').split('+')[0]
    byte_target = pending.get('target')

    nodes     = state.get('nodes', [])
    company   = state.get('company', {})
    regulator = state.setdefault('regulator', {})

    ap_costs         = {'B1': 1, 'B2': 2, 'B3': 2, 'B4': 1}
    byte_ap_available = state.get('byte', {}).get('byte_ap', 2)
    action_cost       = ap_costs.get(byte_action, 1)

    applied_byte = []
    target_node  = node_map.get(byte_target) if byte_target else None

    print(f'[BYTE RESOLVE] action={byte_action} target={byte_target} ap={byte_ap_available}/{action_cost}')

    if action_cost > byte_ap_available:
        print('[BYTE RESOLVE] ❌ Not enough AP')
        return []

    if byte_action == 'B1' and target_node:
        defense             = target_node.get('defense', 10)
        already             = target_node.get('compromised', False)
        is_offline          = target_node.get('offline', False)
        is_direct           = target_node.get('type') in ('entry', 'human')
        adjacent_compromised = any(
            node_map.get(
                e.get('from') if e.get('to') == byte_target else e.get('to'), {}
            ).get('compromised')
            for e in state.get('edges', [])
            if byte_target in (e.get('from'), e.get('to'))
        )
        can_b1 = not already and not is_offline and defense < 6 and (is_direct or adjacent_compromised)
        print(f'[BYTE RESOLVE] B1 check — defense={defense} already={already} offline={is_offline} '
              f'is_direct={is_direct} adj_comp={adjacent_compromised} → can={can_b1}')

        if can_b1:
            target_node['compromised'] = True
            applied_byte = [{'node_id': byte_target, 'attribute': 'compromised', 'old_value': False, 'new_value': True}]
            print(f'[BYTE RESOLVE] ✅ B1 Compromise — {byte_target}')
        elif not adjacent_compromised and not is_direct:
            candidates = [
                n for n in nodes
                if n.get('type') in ('entry', 'human')
                and n.get('compromised') is not True
                and not n.get('isolated') and not n.get('offline')
                and isinstance(n.get('defense'), int) and n.get('defense', 10) < 6
            ]
            if candidates:
                best = min(candidates, key=lambda n: n.get('defense', 10))
                best['compromised'] = True
                applied_byte = [{'node_id': best['id'], 'attribute': 'compromised', 'old_value': False, 'new_value': True}]
                print(f"[BYTE RESOLVE] ✅ B1 redirect → {best['id']} (defense={best.get('defense')})")
            else:
                print('[BYTE RESOLVE] ⏸ No valid target — all entries defended. Byte reconnoiters.')
        else:
            print(f'[BYTE RESOLVE] ❌ B1 blocked — defense={defense} already={already} offline={is_offline}')

    elif byte_action == 'B2' and target_node:
        if target_node.get('compromised') and target_node.get('type') != 'human':
            target_node['locked']         = True
            regulator['breach_timer']     = 3
            applied_byte = [{'node_id': byte_target, 'attribute': 'locked', 'old_value': False, 'new_value': True}]
            print(f'[BYTE RESOLVE] ✅ B2 Encrypt — {byte_target} locked')
        else:
            print('[BYTE RESOLVE] ❌ B2 blocked')

    elif byte_action == 'B3' and target_node:
        if target_node.get('compromised') and target_node.get('type') == 'database':
            company['reputation']    = max(0.0, float(company.get('reputation', 0.8)) - 0.15)
            company['compliance']    = max(0.0, float(company.get('compliance', 0.7)) - 0.10)
            regulator['breach_timer'] = 3
            applied_byte = [{'node_id': byte_target, 'attribute': 'compromised', 'new_value': True}]
            print('[BYTE RESOLVE] ✅ B3 Exfiltrate — rep-0.15 compliance-0.10')
        else:
            print('[BYTE RESOLVE] ❌ B3 blocked')

    elif byte_action == 'B4' and target_node:
        if state.get('_infra_freeze_active'):
            print('[BYTE RESOLVE] ⛔ B4 blocked by Infra Freeze')
        elif not target_node.get('offline'):
            target_node['offline']       = True
            target_node['offline_turns'] = 2
            applied_byte = [{'node_id': byte_target, 'attribute': 'offline', 'old_value': False, 'new_value': True}]
            print(f'[BYTE RESOLVE] ✅ B4 DDoS — {byte_target} offline 2 turns')

    elif byte_action == 'B1':   # Auto-escalate B1 → B2 when foothold exists but no target
        for cn in nodes:
            if cn.get('compromised') and not cn.get('locked') and cn.get('type') != 'human':
                cn['locked']              = True
                regulator['breach_timer'] = max(regulator.get('breach_timer', 0), 3)
                applied_byte = [{'node_id': cn['id'], 'attribute': 'locked', 'old_value': False, 'new_value': True}]
                print(f"[BYTE RESOLVE] ✅ Auto-escalate B1→B2 on {cn['id']}")
                break

    if len(applied_byte) > 1:
        print('[BYTE RESOLVE] ⚠ AP cap — truncating to 1, rolling back extras')
        for extra in applied_byte[1:]:
            node = node_map.get(extra['node_id'])
            if node:
                node[extra['attribute']] = extra.get('old_value', False)
        applied_byte = applied_byte[:1]

    return applied_byte


def _tick_regulator(state: dict, breach_occurred: bool, turn_num: int) -> str | None:
    """
    Phase 4 — Regulator.
    Increments breach_timer on fresh breach, ticks it down, fires fine when it expires.
    Returns deletion_event string or None.
    """
    company   = state.get('company', {})
    regulator = state.get('regulator', {})
    nodes     = state.get('nodes', [])

    if breach_occurred:
        regulator['breach_timer'] = regulator.get('breach_timer', 0) + 1

    if regulator.get('breach_timer', 0) > 0:
        regulator['breach_timer'] -= 1
        if regulator['breach_timer'] == 0 and not company.get('breach_reported', False):
            fine = min(2000, 500 + turn_num * 150)
            company['cash']       = max(0, company.get('cash', 0) - fine)
            company['compliance'] = max(0, company.get('compliance', 0.7) - 0.10)

    if company.get('compliance', 0.7) < 0.2:
        worst = min(nodes, key=lambda n: n.get('compliance_score', 5))
        worst['offline']       = True
        worst['offline_turns'] = 3

    deletion_event = None
    if turn_num in (6, 7) and not regulator.get('deletion_requested'):
        regulator['deletion_requested'] = True
        deletion_event = 'DELETION_REQUEST'

    return deletion_event


def _drift_metrics(state: dict) -> None:
    """
    Phase 5 — Compliance drift + reputation decay.
    • Reputation: -0.02 × compromised_count (capped at -0.05/turn).
    • Compliance: drift toward avg node compliance_score; -0.05 penalty when incident active.
      Without incident, natural downward drift is capped at -0.01/turn.
    """
    company   = state.get('company', {})
    nodes     = state.get('nodes', [])
    regulator = state.get('regulator', {})

    compromised_count = sum(1 for n in nodes if n.get('compromised'))
    if compromised_count > 0:
        rep_penalty = min(0.05, 0.02 * compromised_count)
        company['reputation'] = max(0.0, float(company.get('reputation', 0.8)) - rep_penalty)

    online_nodes = [n for n in nodes if not n.get('offline')]
    if not online_nodes:
        return

    avg_comp         = sum(n.get('compliance_score', 5) for n in online_nodes) / len(online_nodes) / 10
    current          = company.get('compliance', 0.7)
    drift            = (avg_comp - current) * 0.1
    has_incident     = (
        regulator.get('breach_timer', 0) > 0 or
        any(n.get('compromised') for n in nodes) or
        any(n.get('locked') for n in nodes)
    )
    breach_penalty   = -0.05 if has_incident else 0.0

    if drift < 0 and not has_incident:
        drift = max(drift, -0.01)

    new_compliance = max(0.0, min(1.0, current + drift + breach_penalty))
    print(f'[COMPLIANCE] current={current:.2f} avg_node={avg_comp:.2f} drift={drift:.3f} '
          f'penalty={breach_penalty} → {new_compliance:.2f} incident={has_incident}')
    company['compliance'] = new_compliance


def _check_win_lose(state: dict, turn_num: int) -> tuple[bool, str | None]:
    """
    Phase 7 — GDD §12 win/lose conditions.
    Returns (game_over, reason_string).
    """
    company = state.get('company', {})
    nodes   = state.get('nodes', [])
    core_db = next((n for n in nodes if n.get('type') == 'database'), None)

    if company.get('cash', 0) <= 0:
        return True, '💀 Faillite — cash ≤ 0'
    if company.get('compliance', 0.7) <= 0:
        return True, '⚖️ Shutdown réglementaire — compliance ≤ 0'
    if company.get('reputation', 0.8) <= 0:
        return True, '📉 Exode clients — reputation ≤ 0'
    if core_db and core_db.get('locked'):
        return True, '🔒 Breach — Core DB locked, game over'
    if turn_num > 10:
        if (company.get('cash', 0) > 0 and
                company.get('compliance', 0.7) > 0.5 and
                company.get('reputation', 0.8) > 0.3):
            return True, '🏆 VICTOIRE — survécu 10 tours !'
        return True, '❌ Défaite — survécu mais pas assez solide'

    return False, None


# ══════════════════════════════════════════════════════════════
# MAIN TURN ORCHESTRATOR (public)
# ══════════════════════════════════════════════════════════════

_ACTION_NAMES = {
    'S1': 'Scan',             'S2': 'Zero Trust',       'S3': 'Harden',
    'S4': 'Honeypot',         'S5': 'SOC Contract',     'S6': 'IR Retainer',
    'E1': 'Optimize',         'E2': 'Restore',          'E3': 'Full Observability',
    'E4': 'Auto-Failover',    'E5': 'Infra Freeze',     'E6': 'Cost Drive',
    'C1': 'Report Breach',    'C2': 'Boost Throughput', 'C3': 'Patch Vuln',
    'C4': 'Cut Costs',        'C5': 'Evict',            'C6': 'Pay Ransom',
    'C7': 'Reinforce',        'C8': 'Deploy MFA',       'C9': 'Do Nothing',
}


def execute_turn(state: dict, action_id: str, target: str | None, byte_rec: dict) -> dict:
    """
    Execute a complete turn.

    Phase order:
      0  Tick        — timers, effect tick-down, active paradigm effects
      1  Player      — resolve action_id/target via GDD rules (defenses land BEFORE Byte)
      2  Byte        — apply _pending_byte_action from previous turn (sees player's new defenses)
      3  Revenue     — cash reconciliation
      4  Regulator   — fines, compliance triggers, deletion events
      5  Metrics     — compliance drift, reputation decay
      6  Queue Byte  — store next Byte action as _pending_byte_action
      7  Win/Lose    — GDD §12 conditions
      8  Narrative   — turn_log entries + analytics snapshot

    Returns: updated state dict.
    """
    new_state = copy.deepcopy(state)
    company   = new_state['company']
    regulator = new_state.setdefault('regulator', {})
    nodes     = new_state['nodes']
    node_map  = {n['id']: n for n in nodes}

    if regulator.get('breach_timer') is None:
        regulator['breach_timer'] = 0

    turn_num     = company.get('turn', 0) + 1
    forced_audit = company.get('compliance', 0.7) < 0.5

    # ── Phase 0: TICK ──
    _tick_state(new_state)

    # ── Phase 1: PLAYER ──
    # Player acts first so defensive moves (C7 Reinforce, C8 MFA, S3 Harden) take effect
    # before the pending Byte action resolves. This prevents the phase-order exploit where
    # Byte redirects to a node the player is defending this same turn.
    player_mutations = _resolve_player_action(action_id, target, new_state)
    _, applied_player = apply_mutations(new_state, player_mutations)
    print(f'[ENGINE PLAYER] action={action_id} target={target} applied={len(applied_player)} mutations')
    for a in applied_player:
        print(f"  → {a['node_id']}.{a['attribute']}: {a.get('old_value')} → {a['new_value']}")

    # ── Phase 2: APPLY PENDING BYTE ──
    # Resolves the Byte action queued at the END of the previous turn.
    # Runs after Player so defenses raised this turn are visible to Byte's eligibility checks.
    pending_byte = new_state.pop('_pending_byte_action', None)
    applied_byte = []
    byte_action_resolved = None
    byte_target_resolved = None

    if pending_byte:
        print('[BYTE RESOLVE] Applying pending Byte action from previous turn')
        applied_byte         = _apply_byte_action(pending_byte, new_state, node_map)
        byte_action_resolved = pending_byte.get('action_id', 'B1').split('+')[0]
        byte_target_resolved = applied_byte[0].get('node_id') if applied_byte else pending_byte.get('target')

    breach_occurred = len(applied_byte) > 0

    # ── Phase 3: REVENUE ──
    financials = calculate_revenue(new_state)
    print(f"[REVENUE] rev={financials['total_revenue']} costs={financials['total_costs']} "
          f"net={financials['net_income']} cash={company['cash']}")
    for f in new_state.get('flows', []):
        print(f"  flow {f.get('name')}: active={f.get('is_active')} rev={f.get('current_revenue')}")

    # ── Phase 4: REGULATOR ──
    deletion_event = _tick_regulator(new_state, breach_occurred, turn_num)

    # ── Phase 5: METRICS DRIFT ──
    _drift_metrics(new_state)

    # ── Phase 6: QUEUE NEXT BYTE ──
    next_byte_action = byte_rec.get('action_id', 'B1').split('+')[0] if isinstance(byte_rec, dict) else 'B1'
    next_byte_target = byte_rec.get('target') if isinstance(byte_rec, dict) else None
    new_state['_pending_byte_action'] = {'action_id': next_byte_action, 'target': next_byte_target}
    print(f"[BYTE QUEUE] → {new_state['_pending_byte_action']} (replaces any previous pending)")

    # ── Phase 7: WIN/LOSE ──
    company['turn'] = turn_num
    game_over, game_over_reason = _check_win_lose(new_state, turn_num)

    # ── Phase 8: NARRATIVE + SNAPSHOT ──
    narrative_logs = new_state.setdefault('turn_log', [])

    # Byte resolve message
    if applied_byte and byte_action_resolved:
        target_node_log = node_map.get(byte_target_resolved, {})
        target_name = target_node_log.get('business_name', byte_target_resolved or 'unknown node')
        byte_resolve_msgs = {
            'B1': f'Breach confirmed — {target_name} is now compromised. 👁',
            'B2': f'Encryption deployed on {target_name}. Ransom note incoming. 💀',
            'B3': f'Data exfiltrated from {target_name}. Breach timer started. 🔓',
            'B4': f'DDoS executed on {target_name}. Node offline. 🌊',
        }
        narrative_logs.append({
            'source': 'byte', 'action': byte_action_resolved, 'target': byte_target_resolved,
            'message': byte_resolve_msgs.get(byte_action_resolved, f'Attack resolved on {target_name}.'),
            'visible_to_player': True,
        })
    elif pending_byte:
        narrative_logs.append({
            'source': 'byte', 'action': 'BLOCKED', 'target': byte_target_resolved,
            'message': 'Attack vector closed. Reconsidering approach.',
            'visible_to_player': True,
        })
    elif turn_num > 1:
        lurk_msgs = [
            'Scanning entry points... patience. 🕵',
            "Mapping your network topology. You won't see me coming.",
            'Probing defenses on exposed nodes. Waiting for the right moment.',
            f'Turn {turn_num}: Reconnaissance complete. Attack vector identified.',
        ]
        narrative_logs.append({
            'source': 'byte', 'action': 'RECON', 'target': None,
            'message': random.choice(lurk_msgs),
            'visible_to_player': True,
        })

    # Byte queue message
    narrative_logs.append({
        'source': 'byte', 'action': 'QUEUE', 'target': next_byte_target,
        'message': 'Probing defenses. Attack queued for next turn.',
        'visible_to_player': True,
    })

    # Regulator messages
    if breach_occurred and regulator['breach_timer'] == 0:
        fine = min(2000, 500 + turn_num * 150)
        narrative_logs.append({
            'source': 'regulator', 'action': 'R1', 'target': None,
            'message': f'Breach detected. Fine issued: €{fine}K. Compliance −0.10.',
            'visible_to_player': True,
        })
    if forced_audit:
        narrative_logs.append({
            'source': 'regulator', 'action': 'R2', 'target': None,
            'message': 'Compliance audit underway. Regulator is watching closely.',
            'visible_to_player': True,
        })
    if deletion_event:
        narrative_logs.append({
            'source': 'regulator', 'action': 'R4', 'target': None,
            'message': 'Data deletion request received. Purge or face automatic fine next turn.',
            'visible_to_player': True,
        })

    # Vulnerable nodes warning
    vulnerable = [n for n in nodes if isinstance(n.get('defense'), int) and n.get('defense', 10) < 6 and not n.get('fogged')]
    if vulnerable:
        names = ', '.join(n.get('business_name', n['id']) for n in vulnerable[:3])
        narrative_logs.append({
            'source': 'system', 'action': 'WARN', 'target': None,
            'message': f'⚠ Vulnerable nodes (defense<6): {names}',
            'visible_to_player': True,
        })

    # Player action message
    if action_id != 'C9':
        net  = financials['net_income']
        sign = '+' if net >= 0 else ''
        narrative_logs.append({
            'source': 'cto', 'action': action_id, 'target': target,
            'message': f"Executing {_ACTION_NAMES.get(action_id, action_id)}. Net this turn: {sign}€{net}K.",
            'visible_to_player': True,
        })

    # Turn summary
    narrative_logs.append({
        'source': 'system', 'action': 'TICK', 'target': None,
        'message': (
            f"Turn {turn_num} complete — "
            f"Cash €{company['cash']}K | "
            f"Revenue €{financials['total_revenue']}K | "
            f"Costs €{financials['total_costs']}K"
        ),
        'visible_to_player': True,
    })

    # Analytics snapshot
    new_state.setdefault('snapshots', []).append({
        'turn':                     turn_num,
        'cash':                     company.get('cash', 0),
        'reputation':               company.get('reputation', 0.8),
        'compliance':               company.get('compliance', 0.7),
        'net_income':               financials.get('net_income', 0),
        'byte_mutations_applied':   len(applied_byte),
        'breach_occurred':          breach_occurred,
        'action_id':                action_id,
        'target':                   target,
        'player_mutations_applied': len(applied_player),
        'game_over':                game_over,
        'game_over_reason':         game_over_reason,
    })

    new_state['game_over']        = game_over
    new_state['game_over_reason'] = game_over_reason

    return new_state
