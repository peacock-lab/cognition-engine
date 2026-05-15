from __future__ import annotations

from schemas.model_routing import ModelRouteFacts

from contract_core import model_routing


def test_model_routing_facade_reexports_route_facts() -> None:
    assert model_routing.ModelRouteFacts is ModelRouteFacts


def test_model_routing_facade_exports_are_explicit() -> None:
    assert model_routing.__all__ == ["ModelRouteFacts"]
