"""Safe detection helpers for ADK native evaluation capabilities."""

from __future__ import annotations

from cognition_evaluation.models import AdkNativeEvaluationCapability


def detect_adk_native_evaluation_capability() -> AdkNativeEvaluationCapability:
    """Detect locally installed ADK evaluation entry points.

    This function only returns safe capability facts. It does not expose ADK raw
    objects and does not execute ADK evaluation runtime.
    """

    optional_warnings: list[str] = []
    try:
        import google.adk.evaluation as adk_evaluation  # noqa: F401
    except Exception as exc:
        return AdkNativeEvaluationCapability(
            module_available=False,
            agent_evaluator_available=False,
            eval_config_available=False,
            eval_metric_available=False,
            optional_dependency_warnings=[
                f"google.adk.evaluation:{type(exc).__name__}"
            ],
        )

    agent_evaluator_available = False
    eval_config_available = False
    eval_metric_available = False
    eval_status_values: list[str] = []

    try:
        from google.adk.evaluation import AgentEvaluator  # noqa: F401

        agent_evaluator_available = True
    except Exception as exc:  # pragma: no cover - depends on local ADK extras
        optional_warnings.append(f"AgentEvaluator:{type(exc).__name__}")

    try:
        from google.adk.evaluation.eval_config import EvalConfig  # noqa: F401

        eval_config_available = True
    except Exception as exc:  # pragma: no cover - depends on local ADK extras
        optional_warnings.append(f"EvalConfig:{type(exc).__name__}")

    try:
        from google.adk.evaluation.eval_metrics import EvalMetric, EvalStatus

        eval_metric_available = True
        eval_status_values = [str(item.value) for item in EvalStatus]
        _ = EvalMetric
    except Exception as exc:  # pragma: no cover - depends on local ADK extras
        optional_warnings.append(f"EvalMetric:{type(exc).__name__}")

    try:
        import google.adk.evaluation.final_response_match_v1  # noqa: F401
    except Exception as exc:
        optional_warnings.append(
            f"final_response_match_v1_optional:{type(exc).__name__}"
        )

    return AdkNativeEvaluationCapability(
        module_available=True,
        agent_evaluator_available=agent_evaluator_available,
        eval_config_available=eval_config_available,
        eval_metric_available=eval_metric_available,
        eval_status_values=eval_status_values,
        optional_dependency_warnings=optional_warnings,
        raw_object_exported=False,
    )
