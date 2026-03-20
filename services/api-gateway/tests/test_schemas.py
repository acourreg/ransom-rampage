import pytest
from pydantic import ValidationError
from app.models.schemas import (
    NodeMutation,
    AgentRecommendation,
    CreateGameRequest,
    TurnRequest,
    GameResponse,
    TurnResponse,
)

class TestNodeMutation:
    def test_valid_mutation(self):
        m = NodeMutation(node_id="n1", attribute="defense", value=3)
        assert m.node_id == "n1"
        assert m.attribute == "defense"
        assert m.value == 3

    def test_mutation_with_bool_value(self):
        m = NodeMutation(node_id="n2", attribute="compromised", value=True)
        assert m.value is True

    def test_mutation_with_float_value(self):
        m = NodeMutation(node_id="n3", attribute="compliance_score", value=0.75)
        assert m.value == 0.75

    def test_mutation_with_string_value(self):
        m = NodeMutation(node_id="n4", attribute="name", value="New Name")
        assert m.value == "New Name"

class TestAgentRecommendation:
    def test_valid_recommendation(self):
        rec = AgentRecommendation(
            action_id="S1",
            target="n1",
            action_label="Scan node",
            action_description="Scan for threats",
            cost=50,
            mutations=[{"node_id": "n1", "attribute": "visibility", "value": 3}],
        )
        assert rec.action_id == "S1"
        assert rec.target == "n1"
        assert len(rec.mutations) == 1

    def test_empty_mutations_allowed(self):
        rec = AgentRecommendation(
            action_id="C6",
            action_label="Wait",
            action_description="Do nothing",
            cost=0,
        )
        assert rec.mutations == []

    def test_optional_target(self):
        rec = AgentRecommendation(
            action_id="C6",
            action_label="Do nothing",
            action_description="Pass this turn",
        )
        assert rec.target is None

    def test_default_cost(self):
        rec = AgentRecommendation(
            action_id="S1",
            action_label="Scan",
            action_description="Scan infrastructure",
        )
        assert rec.cost == 0

class TestApiSchemas:
    def test_create_game_request_defaults(self):
        req = CreateGameRequest()
        assert "Fintech" in req.user_prompt or "fintech" in req.user_prompt.lower()

    def test_create_game_request_custom(self):
        req = CreateGameRequest(user_prompt="Custom prompt")
        assert req.user_prompt == "Custom prompt"

    def test_turn_request_action_id_required(self):
        req = TurnRequest(action_id="C1")
        assert req.action_id == "C1"

    def test_turn_request_target_optional(self):
        req = TurnRequest(action_id="C6")
        assert req.target is None

    def test_turn_request_target_provided(self):
        req = TurnRequest(action_id="S1", target="n2")
        assert req.target == "n2"

    def test_game_response(self):
        resp = GameResponse(session_id="abc123", state={"test": True})
        assert resp.session_id == "abc123"
        assert resp.state["test"] is True

    def test_turn_response_defaults(self):
        resp = TurnResponse(state={"turn": 2})
        assert resp.state["turn"] == 2
        assert resp.game_over is False
        assert resp.game_over_reason is None
        assert resp.events == []

    def test_turn_response_full(self):
        resp = TurnResponse(
            state={"turn": 3},
            events=[{"type": "mutation", "target": "n1"}],
            game_over=True,
            game_over_reason="Cash depleted",
            advisor_recs={"ciso": {"action_id": "S1"}},
        )
        assert resp.game_over is True
        assert len(resp.events) == 1