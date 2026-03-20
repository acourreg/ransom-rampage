import pytest
import copy
from app.services.game_service import apply_fog_filter

class TestFogFilter:
    def test_fogged_nodes_redacted(self, fake_state):
        filtered = apply_fog_filter(fake_state)
        for node in filtered["nodes"]:
            if node.get("fogged"):
                assert node["throughput"] == "???"
                assert node["defense"] == "???"
                assert node["visibility"] == "???"
                assert node["cost"] == "???"
                assert node["compliance_score"] == "???"

    def test_unfogged_nodes_intact(self, fake_state):
        filtered = apply_fog_filter(fake_state)
        n1 = next(n for n in filtered["nodes"] if n["id"] == "n1")
        assert isinstance(n1["defense"], int)

    def test_byte_presence_hidden(self, fake_state):
        filtered = apply_fog_filter(fake_state)
        assert "byte" not in filtered or "byte_presence" not in filtered.get("byte", {})

    def test_unknown_vulns_hidden(self, fake_state):
        filtered = apply_fog_filter(fake_state)
        for v in filtered.get("vulnerabilities", []):
            assert v["known_by_player"] is True

    def test_original_not_mutated(self, fake_state):
        original = copy.deepcopy(fake_state)
        apply_fog_filter(fake_state)
        assert fake_state == original