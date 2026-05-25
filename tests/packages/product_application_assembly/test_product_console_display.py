from __future__ import annotations

from product_application_assembly import (
    PRODUCT_APPLICATION_PRODUCT_CONSOLE_DISPLAY_MODEL_POLICY_REF,
    PRODUCT_APPLICATION_PRODUCT_CONSOLE_DISPLAY_SOURCE,
    PRODUCT_CONSOLE_DISPLAY_MODEL_CANDIDATE_REF,
    build_product_console_ask_output_display,
    build_product_console_home_display,
    product_console_ask_output_display_dict,
    product_console_home_display_dict,
)


def test_product_console_display_model_is_candidate_not_public_schema() -> None:
    display = build_product_console_home_display()

    assert display.display_model_ref == PRODUCT_CONSOLE_DISPLAY_MODEL_CANDIDATE_REF
    assert display.display_model_status == "candidate"
    assert display.source == PRODUCT_APPLICATION_PRODUCT_CONSOLE_DISPLAY_SOURCE
    assert display.runtime_backed is False
    assert display.public_schema is False
    assert display.task_api_semantic == "semantic_placeholder_only"
    assert display.workflow_runtime_semantic == "semantic_placeholder_only"
    assert display.metadata["policy_ref"] == (
        PRODUCT_APPLICATION_PRODUCT_CONSOLE_DISPLAY_MODEL_POLICY_REF
    )


def test_product_console_display_dict_exposes_safe_product_console_facts() -> None:
    payload = product_console_home_display_dict(build_product_console_home_display())

    assert payload["display_model_status"] == "candidate"
    assert payload["runtime_backed"] is False
    assert payload["public_schema"] is False
    assert payload["products"][0]["product_id"] == "reviewable-evidence-answer-pack"
    assert payload["products"][0]["answer_run"]["status"] == "not_started"
    assert payload["products"][0]["answer_run"]["answer_run_ref"] is None
    assert payload["products"][0]["entrypoint"] == "cognition-console ask --guided"
    assert payload["products"][0]["actions"][0]["status"] == "available"
    assert payload["products"][0]["actions"][0]["scope"] == (
        "product_console_ask_entry"
    )
    assert any("不执行模型路由" in hint for hint in payload["boundary_hints"])


def test_product_console_ask_display_defaults_to_answer_run_review_ref() -> None:
    display = build_product_console_ask_output_display(
        {
            "status": "success",
            "answer": "这是一个示例域名。",
            "answer_run_ref": "evidence-summary-answer-run://run-test",
            "answer_trace_ref": "evidence-summary-answer-trace://trace-test",
            "answer_artifact_ref": "evidence-summary-answer-artifact://artifact-test",
            "observability_summary_ref": (
                "evidence-summary-answer-observability-summary://summary-test"
            ),
            "trace_inspect_ref": (
                "evidence-summary-answer-trace-inspect://inspect-test"
            ),
            "follow_up_available": True,
        },
        command="cognition-console ask",
    )
    payload = product_console_ask_output_display_dict(display)

    assert payload["product"] == "可复查资料问答包"
    assert payload["command"] == "cognition-console ask"
    assert payload["review"]["answer_run_ref"] == (
        "evidence-summary-answer-run://run-test"
    )
    assert payload["review"]["detail_available"] is True
    assert payload["review"]["answer_trace_ref"] == (
        "evidence-summary-answer-trace://trace-test"
    )
    assert payload["follow_up_available"] is True


def test_product_console_ask_display_explains_answer_scoped_transformation() -> None:
    display = build_product_console_ask_output_display(
        {
            "status": "success",
            "answer": "1. 示例域名。",
            "answer_scoped_transformation": True,
            "answer_run_ref": None,
            "answer_run_status": "unavailable",
            "answer_run_unavailable_reason": (
                "answer_scoped_transformation_uses_previous_answer"
            ),
        },
        command="cognition-console ask",
    )
    payload = product_console_ask_output_display_dict(display)

    assert payload["review"]["answer_run_ref"] is None
    assert payload["review"]["status"] == "answer_scoped_transformation"
    assert "上一轮可见答案变换" in payload["review"]["explanation"]
    assert payload["review"]["detail_available"] is False
