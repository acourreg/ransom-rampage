import pytest
import json
import copy
from app.core.agents import ciso_graph, sre_graph, byte_graph, ciso_actions, sre_actions, byte_actions, CTO_ACTIONS_REF

class TestAgentsE2E:
    """Test d'intégration complet : configs → graphs → invoke → extract recommendations.
    Utilise de vrais appels LLM (OPENAI_API_KEY requis)."""

    def test_full_agent_pipeline(self, fake_state):
        """Compile les 3 graphs, invoque chacun, vérifie le format des recommandations."""

        # 1. Vérifier que les graphs sont compilés
        assert ciso_graph is not None
        assert sre_graph is not None
        assert byte_graph is not None

        # 2. Construire l'AgentState pour chaque rôle
        def build_state(role):
            return {
                "messages": [],
                "game_state": copy.deepcopy(fake_state),
                "cache_hit": False,
                "current_cache_key": "",
                "active_role": role
            }

        # 3. Invoquer CISO (vrai LLM call)
        ciso_result = ciso_graph.invoke(build_state("ciso"))
        assert "messages" in ciso_result
        assert len(ciso_result["messages"]) > 0
        ciso_msg = ciso_result["messages"][-1].content
        ciso_rec = json.loads(ciso_msg)
        assert "action_id" in ciso_rec
        assert "mutations" in ciso_rec
        assert isinstance(ciso_rec["mutations"], list)
        print(f"  CISO rec: {ciso_rec['action_id']} → {ciso_rec.get('action_label', '?')}")

        # 4. Invoquer SRE (vrai LLM call)
        sre_result = sre_graph.invoke(build_state("sre"))
        sre_msg = sre_result["messages"][-1].content
        sre_rec = json.loads(sre_msg)
        assert "action_id" in sre_rec
        assert "mutations" in sre_rec
        print(f"  SRE rec: {sre_rec['action_id']} → {sre_rec.get('action_label', '?')}")

        # 5. Invoquer Byte (vrai LLM call)
        byte_result = byte_graph.invoke(build_state("hacker"))
        byte_msg = byte_result["messages"][-1].content
        byte_rec = json.loads(byte_msg)
        assert "action_id" in byte_rec
        assert "mutations" in byte_rec
        assert any(byte_rec["action_id"].startswith(p) for p in ("B", "R", "S", "E", "C"))
        print(f"  BYTE rec: {byte_rec['action_id']} → {byte_rec.get('action_label', '?')}")

        # 6. Vérifier que les configs statiques sont cohérentes
        assert len(ciso_actions) > 0
        assert len(sre_actions) > 0
        assert len(byte_actions) > 0
        assert all(f"C{i}" in CTO_ACTIONS_REF for i in range(1, 10))