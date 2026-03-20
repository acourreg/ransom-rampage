import pytest
from app.core.generation import game_generator

class TestGenerationE2E:
    """Test d'intégration complet : venture_architect → sre_infra → assembler → validation.
    Utilise de vrais appels LLM. Vérifie la conformité GDD du state généré."""

    def test_full_entity_generation(self):
        """Invoque la pipeline complète et valide le game_state produit."""

        # 1. Invoquer la pipeline (vrais LLM calls)
        result = game_generator.invoke({"user_prompt": "Generate a fintech startup"})
        state = result["final_gamestate"]

        # 2. Company — champs requis
        company = state["company"]
        assert company["cash"] >= 3000
        assert company["cash"] <= 6000
        assert company["sector"] in ("neobank", "p2p", "hft", "payments")
        assert company["adversary"] in ("script_kiddie", "mafia", "state")
        assert 0 <= company["compliance"] <= 1
        assert 0 <= company["reputation"] <= 1

        # 3. Nodes — 6 à 8, types variés
        nodes = state["nodes"]
        assert 6 <= len(nodes) <= 8
        types = {n["type"] for n in nodes}
        assert "database" in types
        assert "entry" in types
        for n in nodes:
            assert all(k in n for k in ["throughput", "defense", "visibility", "cost", "compliance_score"])
            assert 1 <= n["throughput"] <= 10
            assert 1 <= n["defense"] <= 10

        # 4. Edges — pas d'orphelins
        edges = state["edges"]
        assert len(edges) >= len(nodes) - 1
        node_ids = {n["id"] for n in nodes}
        for e in edges:
            assert e["from"] in node_ids
            assert e["to"] in node_ids

        # 5. Core DB — 3+ edges
        core_db = next(n for n in nodes if n["type"] == "database")
        core_edges = sum(1 for e in edges if e["from"] == core_db["id"] or e["to"] == core_db["id"])
        assert core_edges >= 3

        # 6. Flows — 3-4, paths valides
        flows = state["flows"]
        assert 3 <= len(flows) <= 4
        for f in flows:
            assert f["base_revenue"] >= 5
            assert f["base_revenue"] <= 50
            assert all(nid in node_ids for nid in f["node_path"])

        # 7. Vulns — 3-5
        vulns = state.get("vulnerabilities", [])
        assert 3 <= len(vulns) <= 5
        for v in vulns:
            assert v["node_id"] != core_db["id"]
            assert 1 <= v["severity"] <= 3

        # 8. Fog — 25-55%
        fogged = sum(1 for n in nodes if n.get("fogged"))
        pct = fogged / len(nodes)
        assert 0.25 <= pct <= 0.55

        # 9. Byte — AP selon adversary
        byte = state["byte"]
        expected_ap = 3 if company["adversary"] == "state" else 2
        assert byte["byte_ap"] == expected_ap

        print(f"  Generated: {company.get('name', '?')} ({company['sector']})")
        print(f"  {len(nodes)} nodes, {len(flows)} flows, {len(vulns)} vulns")