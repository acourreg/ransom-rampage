"""
Game logger — persistent file logging for debugging scenarios, decisions and state evolution.

Log file: logs/game.log (rotating, 10 MB × 5 files)
All print() statements remain for Docker/console viewing.
This module adds structured persistent logs for post-mortem debugging.
"""
import json
import logging
import os
from logging.handlers import RotatingFileHandler

# ── Setup ──

_LOG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
_LOG_FILE = os.path.join(_LOG_DIR, 'game.log')


def _build_logger() -> logging.Logger:
    os.makedirs(_LOG_DIR, exist_ok=True)
    logger = logging.getLogger('ransom_rampage.game')
    if logger.handlers:
        return logger  # already configured (e.g. hot-reload)

    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # avoid doubling to root logger

    fh = RotatingFileHandler(
        _LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)-5s] %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    ))
    logger.addHandler(fh)
    return logger


glog = _build_logger()


# ── Public helpers ──

def log_game_created(session_id: str, gamestate: dict) -> None:
    """Log full generated scenario — company, nodes, flows, vulns, Byte setup."""
    co = gamestate.get('company', {})
    nodes = gamestate.get('nodes', [])
    flows = gamestate.get('flows', [])
    vulns = gamestate.get('vulnerabilities', [])
    byte = gamestate.get('byte', {})

    node_summary = ' | '.join(
        f"{n['id']}:{n.get('business_name', n.get('name', '?'))} "
        f"def={n.get('defense')} fog={n.get('fogged')}"
        for n in nodes
    )
    flow_summary = ' | '.join(
        f"{f.get('name')} base=€{f.get('base_revenue')}K path={f.get('node_path')}"
        for f in flows
    )
    vuln_summary = ' | '.join(
        f"{v.get('node_id')} sev={v.get('severity')} known={v.get('known_by_player')}"
        for v in vulns
    )

    glog.info(
        f"[GAME_CREATED] session={session_id}\n"
        f"  Company : {co.get('name')} | sector={co.get('sector')} "
        f"adversary={co.get('adversary')} cash=€{co.get('cash')}K\n"
        f"  Nodes   : {node_summary}\n"
        f"  Flows   : {flow_summary}\n"
        f"  Vulns   : {vuln_summary}\n"
        f"  Byte AP : {byte.get('byte_ap', 2)}"
    )
    # Full JSON dump for deep inspection
    glog.debug(
        f"[GAME_CREATED] session={session_id} FULL_STATE={json.dumps(gamestate, default=str)}"
    )


_ACTION_LABELS = {
    'C1': 'Report Breach',    'C2': 'Boost Throughput', 'C3': 'Patch Vuln',
    'C4': 'Cut Costs',        'C5': 'Evict Attacker',   'C6': 'Pay Ransom',
    'C7': 'Reinforce',        'C8': 'Deploy MFA',        'C9': 'Do Nothing',
    'S1': 'Scan',             'S2': 'Zero Trust',        'S3': 'Harden',
    'S4': 'Honeypot',         'S5': 'SOC Contract',      'S6': 'IR Retainer',
    'E1': 'Optimize',         'E2': 'Restore',           'E3': 'Full Observability',
    'E4': 'Auto-Failover',    'E5': 'Infra Freeze',      'E6': 'Cost Drive',
}


def log_player_action(session_id: str, turn: int, action_id: str, target: str | None) -> None:
    """Log what the player chose this turn."""
    glog.info(
        f"[PLAYER_ACTION] session={session_id} turn={turn} action={action_id} target={target}"
    )


def log_player_decision(
    session_id: str,
    turn: int,
    action_id: str,
    target: str | None,
    state: dict,
    player_mutations: list,
    byte_action_id: str | None,
    byte_target: str | None,
) -> None:
    """Full pre-engine snapshot: what the player chose + node state before mutations."""
    nodes = {n['id']: n for n in state.get('nodes', [])}
    label = _ACTION_LABELS.get(action_id, action_id)

    # Target node current state
    tnode = nodes.get(target) if target else None
    if tnode:
        target_line = (
            f"  Target  : {target} {tnode.get('business_name', tnode.get('name', '?'))[:28]} "
            f"({tnode.get('type', '?')}) "
            f"def={tnode.get('defense', '?')} tp={tnode.get('throughput', '?')} "
            f"compromised={tnode.get('compromised', False)} "
            f"locked={tnode.get('locked', False)} "
            f"offline={tnode.get('offline', False)} "
            f"isolated={tnode.get('isolated', False)}"
        )
    else:
        target_line = f"  Target  : {target or '(none)'}"

    # Planned mutations
    if player_mutations:
        mut_lines = '\n'.join(
            f"    {m.get('node_id')}.{m.get('attribute')} → {m.get('value')}"
            for m in player_mutations
        )
        mutations_line = f"  Mutations:\n{mut_lines}"
    else:
        mutations_line = "  Mutations: (none / direct state effect)"

    # Byte intent
    byte_tnode = nodes.get(byte_target) if byte_target else None
    byte_target_name = byte_tnode.get('business_name', byte_target) if byte_tnode else byte_target or '?'
    byte_line = f"  Byte    : {byte_action_id or '?'} → {byte_target_name}"

    glog.info(
        f"[DECISION] session={session_id} turn={turn}\n"
        f"  Action  : {action_id} {label}\n"
        f"{target_line}\n"
        f"{mutations_line}\n"
        f"{byte_line}"
    )


def log_mutations(session_id: str, turn: int, source: str, applied: list) -> None:
    """Log mutations actually written to the graph (post apply_mutations)."""
    if not applied:
        glog.debug(f"[MUTATIONS] session={session_id} turn={turn} source={source} count=0")
        return
    detail = '\n'.join(
        f"    {m.get('node_id')}.{m.get('attribute')}: "
        f"{m.get('old_value')} → {m.get('new_value')}"
        for m in applied
    )
    glog.info(
        f"[MUTATIONS] session={session_id} turn={turn} source={source} "
        f"count={len(applied)}\n{detail}"
    )


def log_byte_action(
    session_id: str, turn: int, action: str, target: str | None, result: str
) -> None:
    """Log Byte hacker decision + outcome."""
    glog.info(
        f"[BYTE] session={session_id} turn={turn} action={action} "
        f"target={target} result={result}"
    )


def log_state_snapshot(session_id: str, turn: int, state: dict) -> None:
    """Log company metrics + full per-node state after a turn resolves."""
    co = state.get('company', {})
    nodes = state.get('nodes', [])
    flows = state.get('flows', [])
    effects = state.get('effects', [])
    regulator = state.get('regulator', {})

    # Company headline
    glog.info(
        f"[STATE] session={session_id} turn={turn} "
        f"cash=€{co.get('cash')}K "
        f"rep={co.get('reputation', 0):.2f} "
        f"compliance={co.get('compliance', 0):.2f} "
        f"breach_timer={regulator.get('breach_timer', 0)}"
    )

    # Per-node full state table
    node_lines = []
    for n in nodes:
        flags = []
        if n.get('compromised'): flags.append('COMPROMISED')
        if n.get('locked'):      flags.append('LOCKED')
        if n.get('offline'):     flags.append(f"OFFLINE({n.get('offline_turns', 0)}t)")
        if n.get('isolated'):    flags.append('ISOLATED')
        if n.get('fogged'):      flags.append('FOGGED')
        if n.get('has_mfa'):     flags.append('MFA')
        status = ' '.join(flags) if flags else 'clean'
        node_lines.append(
            f"    {n['id']:4s} {n.get('business_name', n.get('name', '?'))[:28]:28s} "
            f"type={n.get('type', '?'):10s} "
            f"def={str(n.get('defense', '?')):>3s} "
            f"tp={str(n.get('throughput', '?')):>3s} "
            f"cost={str(n.get('cost', '?')):>2s} "
            f"rev_exp=€{n.get('revenue_exposure', 0)}K  "
            f"{status}"
        )
    glog.info(f"[NODES] session={session_id} turn={turn}\n" + '\n'.join(node_lines))

    # Console summary: only nodes in a bad state
    hot = [n for n in nodes if n.get('compromised') or n.get('locked') or n.get('offline')]
    print(f"[TURN RESULT] turn={turn} game_over={state.get('game_over')}")
    for n in hot:
        print(f"  ⚠ {n['id']} {n.get('business_name', '?')} — "
              f"compromised={n.get('compromised')} locked={n.get('locked')} offline={n.get('offline')}")

    # Flow health
    flow_lines = []
    for f in flows:
        flow_lines.append(
            f"    {f.get('name', '?')[:30]:30s} "
            f"active={str(f.get('is_active', '?')):>5s} "
            f"rev=€{f.get('current_revenue', 0)}K/€{f.get('base_revenue', 0)}K "
            f"risk={f.get('risk_level', '?')}"
        )
    if flow_lines:
        glog.info(f"[FLOWS] session={session_id} turn={turn}\n" + '\n'.join(flow_lines))

    # Active effects
    if effects:
        eff_summary = ', '.join(f"{e.get('name')}({e.get('turns_remaining')}t)" for e in effects)
        glog.info(f"[EFFECTS] session={session_id} turn={turn} active={eff_summary}")


def log_advisor_suggestion(
    session_id: str,
    turn: int,
    role: str,
    action_id: str,
    target: str | None,
    label: str,
    description: str,
    cost: int,
) -> None:
    """Log advisor recommendation (CISO / SRE / Byte)."""
    glog.info(
        f"[ADVISOR] session={session_id} turn={turn} role={role} "
        f"action={action_id} target={target} cost=€{cost}K "
        f"label='{label}' | {description}"
    )


def log_game_over(session_id: str, turn: int, reason: str) -> None:
    glog.info(f"[GAME_OVER] session={session_id} turn={turn} reason='{reason}'")
