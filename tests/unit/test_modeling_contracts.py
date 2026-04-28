from cognition_engine.modeling.contracts import (
    DEFAULT_PROVIDER,
    STATUS_SUCCESS,
    ModelRequest,
    ModelResponse,
)


def test_model_request_constructs_with_defaults() -> None:
    request = ModelRequest(
        purpose="unit",
        input_text="hello",
        instruction="answer briefly",
    )

    assert request.provider == DEFAULT_PROVIDER
    assert request.model == "mock"
    assert request.temperature == 0.0
    assert request.timeout_seconds == 30.0
    assert request.metadata == {}
    assert request.to_dict()["input_text"] == "hello"


def test_model_response_constructs_and_serializes() -> None:
    response = ModelResponse(
        status=STATUS_SUCCESS,
        output_text="OK",
        model="mock",
        provider="mock",
        latency_ms=1.5,
        raw_summary={"event_count": 1},
    )

    assert response.error_code is None
    assert response.fallback_used is False
    assert response.to_dict()["raw_summary"] == {"event_count": 1}
