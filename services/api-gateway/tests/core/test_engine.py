import copy
from app.core.engine import extract_mutations, apply_mutations, calculate_revenue, execute_turn

class TestEngineE2E:
    """Test d'intégration complet : resolvers → revenue → orchestrator.
    Reproduit le flow d'un tour de jeu sans LLM (engine = pur Python)."""

    def test_full_turn_cycle(self, fake_state):
        """Enchaîne toutes les fonctions de engine.py dans l'ordre réel."""

        # 1. extract_mutations — input valide
        rec = {"mutations": [{"node_id": "n1", "attribute": "defense", "value": 3}]}
        mutations = extract_mutations(rec)
        assert len(mutations) == 1

        # 2. extract_mutations — input invalide (robustesse)
        assert extract_mutations(None) == []
        assert extract_mutations({"mutations": "garbage"}) == []

        # 3. apply_mutations — défense incrémentée
        state, applied = apply_mutations(fake_state, mutations)
        n1 = next(n for n in state["nodes"] if n["id"] == "n1")
        assert n1["defense"] == 3  # set to 3 (in-place, not +=)
        assert len(applied) == 1

        # 4. apply_mutations — node inconnu ignoré
        _, applied2 = apply_mutations(state, [{"node_id": "n99", "attribute": "defense", "value": 5}])
        assert len(applied2) == 0

        # 5. apply_mutations — bool mutation
        _, applied3 = apply_mutations(state, [{"node_id": "n2", "attribute": "compromised", "value": True}])
        n2 = next(n for n in state["nodes"] if n["id"] == "n2")
        assert n2["compromised"] is True

        # 6. calculate_revenue — flows actifs génèrent du revenu
        fresh = copy.deepcopy(fake_state)
        result = calculate_revenue(fresh)
        assert result["total_revenue"] > 0
        assert result["total_costs"] == sum(n["cost"] * 5 for n in fresh["nodes"])

        # 7. calculate_revenue — node offline tue le flow
        analytics = next(f for f in fresh["flows"] if f["name"] == "Analytics Reports")
        assert analytics["is_active"] is False

        # 8. calculate_revenue — node locked tue le flow
        fresh2 = copy.deepcopy(fake_state)
        next(n for n in fresh2["nodes"] if n["id"] == "n3")["locked"] = True
        calculate_revenue(fresh2)
        card = next(f for f in fresh2["flows"] if f["name"] == "Card Payments")
        assert card["is_active"] is False

        # 9. execute_turn — turn incrémente, revenue recalculée
        turn_state = copy.deepcopy(fake_state)
        empty_byte = {"action_id": "B1", "target": None}
        result = execute_turn(turn_state, "C6", None, empty_byte)
        assert result["company"]["turn"] == 4
        assert "cash" in result["company"]

        # 10. execute_turn — core DB locked = game over
        go_state = copy.deepcopy(fake_state)
        next(n for n in go_state["nodes"] if n["id"] == "n4")["locked"] = True
        result2 = execute_turn(go_state, "C6", None, empty_byte)
        assert result2.get("game_over") is True
        assert "Breach" in (result2.get("game_over_reason") or "")

        # 11. execute_turn — byte action queued for next turn
        byte_state = copy.deepcopy(fake_state)
        byte_rec = {"action_id": "B1", "target": "n2"}
        result3 = execute_turn(byte_state, "C6", None, byte_rec)
        # Byte action is queued as _pending_byte_action, not applied this turn
        assert result3.get("_pending_byte_action") is not None

        # 12. execute_turn — offline_turns décrémente
        ot_state = copy.deepcopy(fake_state)
        result4 = execute_turn(ot_state, "C6", None, empty_byte)
        n7 = next(n for n in result4["nodes"] if n["id"] == "n7")
        assert n7["offline_turns"] == 0
        assert n7["offline"] is False