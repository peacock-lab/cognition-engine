from types import SimpleNamespace

from adk_adapter.invocation_mapper import AdkInvocationMapper
from schemas.runtime import InvocationRef


def test_invocation_mapper_preserves_requested_and_adk_invocation_ids() -> None:
    mapper = AdkInvocationMapper()

    binding = mapper.bind_from_events(
        requested_invocation_id="requested-001",
        events=[SimpleNamespace(invocation_id="adk-actual-001")],
        session_id="session-001",
        app_name="app",
        user_id="user",
        workflow_id="workflow-001",
    )

    assert binding.requested_invocation_id == "requested-001"
    assert binding.adk_invocation_id == "adk-actual-001"
    assert binding.session_id == "session-001"
    assert binding.to_metadata()["workflow_id"] == "workflow-001"


def test_invocation_mapper_merges_binding_into_invocation_ref_metadata() -> None:
    mapper = AdkInvocationMapper()
    binding = mapper.create_binding(
        requested_invocation_id="requested-001",
        adk_invocation_id="adk-actual-001",
    )

    invocation_ref = mapper.merge_into_invocation_ref(
        InvocationRef(
            invocation_id="requested-001",
            workflow_id="workflow-001",
            source="runtime",
            metadata={"kept": True},
        ),
        binding,
    )

    assert invocation_ref.invocation_id == "requested-001"
    assert invocation_ref.metadata["kept"] is True
    assert (
        invocation_ref.metadata["adk_invocation_binding"]["adk_invocation_id"]
        == "adk-actual-001"
    )
