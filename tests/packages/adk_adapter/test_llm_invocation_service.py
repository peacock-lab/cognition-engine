from __future__ import annotations

import os
import re
from pathlib import Path

from adk_adapter.llm_invocation import (
    AdkGovernedLlmInvocationOptions,
    AdkGovernedLlmInvocationService,
)
from behavior_contracts.llm_invocation import GovernedLlmInvocationService
from observability_hub import build_llm_call_observation_candidate
from schemas.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationRequest,
)
from schemas.model_routing import ModelRouteFacts


REPO_ROOT = Path(__file__).resolve().parents[3]
ADK_ADAPTER_SOURCE_ROOT = REPO_ROOT / "packages" / "adk_adapter" / "src" / "adk_adapter"


def test_adk_governed_llm_invocation_service_satisfies_contract() -> None:
    service: GovernedLlmInvocationService = AdkGovernedLlmInvocationService()

    result = service.invoke(_request(allowed=False, decision="block"))

    assert result.failure_type == LlmInvocationFailureType.GOVERNANCE_BLOCKED
    assert result.call_attempted is False
    assert result.call_allowed is False
    assert result.runtime_call_performed is False
    assert result.success is False


def test_adk_governed_llm_invocation_returns_need_evidence_before_call() -> None:
    service = AdkGovernedLlmInvocationService()

    result = service.invoke(_request(allowed=False, decision="need_evidence"))

    assert result.failure_type == LlmInvocationFailureType.GOVERNANCE_NEEDS_EVIDENCE
    assert result.call_attempted is False
    assert result.runtime_call_performed is False


def test_adk_governed_llm_invocation_returns_live_disabled_by_default() -> None:
    service = AdkGovernedLlmInvocationService()

    result = service.invoke(_request(allowed=True))

    assert result.failure_type == LlmInvocationFailureType.LIVE_DISABLED
    assert result.call_attempted is False
    assert result.call_allowed is True
    assert result.runtime_call_performed is False
    assert result.metadata["live_enabled"] is False


def test_adk_governed_llm_invocation_rejects_invalid_route_facts() -> None:
    service = AdkGovernedLlmInvocationService()

    result = service.invoke(
        _request(
            allowed=True,
            route_facts=_route_facts(
                metadata={
                    "backend_provider": "ollama",
                    "route_target": "ollama/gemma4-pro:latest",
                    "route_kind": "other_route",
                }
            ),
        )
    )

    assert result.failure_type == LlmInvocationFailureType.ROUTE_FACTS_INVALID
    assert result.call_attempted is False
    assert result.call_allowed is False
    assert result.runtime_call_performed is False


def test_adk_governed_llm_invocation_live_enabled_runs_fake_client_success() -> None:
    fake_client = _FakeLiteLlmClient("controlled live output")
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
            timeout_seconds=9,
            max_tokens=11,
            metadata={
                "controlled_live": True,
                "live_options_source": (
                    "config_contexts.runtime.RuntimeLiveLlmConfigView"
                ),
                "live_service_profile": "adk_litellm_ollama",
                "configured_model_name": "ollama/gemma4-pro:latest",
            },
        )
    )

    result = service.invoke(_request(allowed=True))

    assert result.failure_type is None
    assert result.call_attempted is True
    assert result.call_allowed is True
    assert result.runtime_call_performed is True
    assert result.success is True
    assert result.response_non_empty is True
    assert result.sanitized_response_length == len("controlled live output")
    assert result.sanitized_response_preview == "controlled live output"
    assert result.metadata["live_enabled"] is True
    assert result.metadata["adapter_boundary"] == "adk_adapter.llm_invocation"
    assert result.metadata["adk_litellm_route_constructed"] is True
    assert result.metadata["options"]["local_no_proxy_applied"] is True
    assert result.metadata["llm_live_profile"] == {
        "controlled_live": True,
        "timeout_seconds": 9,
        "temperature": 0,
        "max_tokens": 11,
        "local_no_proxy_applied": True,
        "live_options_source": "config_contexts.runtime.RuntimeLiveLlmConfigView",
        "live_service_profile": "adk_litellm_ollama",
        "configured_model_name": "ollama/gemma4-pro:latest",
    }
    assert fake_client.calls == [
        {
            "model": "ollama/gemma4-pro:latest",
            "messages": [{"role": "user", "content": "sanitized prompt preview"}],
            "tools": [],
            "api_base": "http://127.0.0.1:11434",
            "temperature": 0,
            "max_tokens": 11,
            "timeout": 9,
        }
    ]


def test_adk_governed_llm_invocation_live_enabled_wraps_cli_chat_prompt() -> None:
    fake_client = _FakeLiteLlmClient("聊聊当然可以")
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="心情不好，能聊聊吗",
            metadata={"interaction_mode": "cli_chat"},
        )
    )

    message = fake_client.calls[0]["messages"][0]

    assert result.failure_type is None
    assert message["role"] == "user"
    assert message["content"].endswith("心情不好，能聊聊吗")
    assert "严禁输出 JSON" in message["content"]
    assert "上下文" in message["content"]
    assert "系统状态" in message["content"]
    assert "system_context" in message["content"]
    assert "直接输出方案" in message["content"]
    assert "继续" in message["content"]
    assert "不要反问" in message["content"]


def test_adk_governed_llm_invocation_live_enabled_includes_cli_chat_context() -> None:
    fake_client = _FakeLiteLlmClient("《爱在黎明破晓前》很适合慢慢看。")
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="能详细解释下这个电影吗",
            metadata={
                "interaction_mode": "cli_chat",
                "cli_chat_context": {
                    "current_user_input": "能详细解释下这个电影吗",
                    "history": [
                        {
                            "user": "电影，有什么电影推荐",
                            "assistant": "推荐了《爱在黎明破晓前》。",
                        }
                    ],
                },
            },
        )
    )

    message = fake_client.calls[0]["messages"][0]["content"]

    assert result.failure_type is None
    assert "最近对话：" in message
    assert "用户：电影，有什么电影推荐" in message
    assert "助手：推荐了《爱在黎明破晓前》。" in message
    assert "当前用户输入：" in message
    assert message.endswith("能详细解释下这个电影吗")


def test_adk_governed_llm_invocation_live_enabled_includes_reference_review_context() -> None:
    fake_client = _FakeLiteLlmClient(
        '{"response_to_user":"主要结论：资料符合当前主线。"}'
    )
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="资料审查，输出主要结论",
            metadata={
                "interaction_mode": "operation_flow_reference_review_workflow",
                "reference_review_context": {
                    "current_user_input": "请审查这些资料",
                    "reference_labels": ["359-result.md"],
                    "evidence_refs": ["evidence://reference-reader/abc"],
                    "reference_excerpts": [
                        "reference: 359-result.md\n1: Agent runtime 未打开。"
                    ],
                },
            },
        )
    )

    message = fake_client.calls[0]["messages"][0]["content"]

    assert result.failure_type is None
    assert result.sanitized_response_preview == "主要结论：资料符合当前主线。"
    assert "中文资料审查助手" in message
    assert "主要结论、判断依据、发现的问题、风险边界、建议动作" in message
    assert "符合、部分符合、不符合或信息不足" in message
    assert "不要要求用户再次上传或粘贴文档" in message
    assert "359-result.md" in message
    assert "evidence://reference-reader/abc" in message
    assert "Agent runtime 未打开" in message
    assert "必须按以下中文小标题和顺序输出" in message
    assert "风险边界" in message
    assert "不得建议打开、接入、集成、启用或开始实施" in message
    assert "严禁把未打开、关闭、暂不接入类边界改写成打开" in message


def test_adk_governed_llm_invocation_live_enabled_includes_evidence_summary_answer_context() -> None:
    fake_client = _FakeLiteLlmClient(
        "该资料支持后续审查，可引用 evidence://external-readonly/cli-fetch/answer.json。"
    )
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="这条资料是否可用",
            metadata={
                "interaction_mode": "evidence_summary_answer_generation",
                "evidence_summary_answer_context": {
                    "user_question": "这条资料是否可用",
                    "summary_facts": [
                        "The reference is suitable for follow-up review.",
                        "ProductGatewayResponse hidden marker must stay out.",
                    ],
                    "evidence_refs": [
                        {
                            "ref": (
                                "evidence://external-readonly/cli-fetch/"
                                "answer.json"
                            ),
                            "kind": "external_readonly_evidence",
                            "purpose": "answer_context",
                            "sanitized_excerpt_preview": (
                                "hidden excerpt must stay out"
                            ),
                        }
                    ],
                    "digest_refs": [
                        "governed-evidence-digest://cli-fetch/answer",
                        "raw_payload://hidden",
                    ],
                    "additional_refs": [
                        {
                            "ref": "governed-evidence-digest://cli-fetch/answer",
                            "kind": "governed_evidence_digest",
                            "purpose": "answer_context",
                            "observability_candidate_body": (
                                "hidden observation body"
                            ),
                        }
                    ],
                    "answer_constraints": [
                        "Use only governed summary facts and listed refs.",
                        "product_response_summary hidden marker must stay out.",
                    ],
                    "answer_policy_ref": (
                        "policy://product-application-assembly/"
                        "evidence-summary-answer/generation/result-v1"
                    ),
                    "citation_policy_ref": (
                        "policy://product-application-assembly/"
                        "evidence-summary-answer/citation-v1"
                    ),
                    "external_readonly_answer_context": "hidden legacy context",
                    "product_response_summary": {"raw_payload": "hidden raw payload"},
                    "config_context_value": "hidden config value",
                },
            },
        )
    )

    message = fake_client.calls[0]["messages"][0]["content"]

    assert result.failure_type is None
    assert "中文证据摘要回答助手" in message
    assert "用户问题：" in message
    assert "这条资料是否可用" in message
    assert "The reference is suitable for follow-up review." in message
    assert "evidence://external-readonly/cli-fetch/answer.json" in message
    assert "governed-evidence-digest://cli-fetch/answer" in message
    assert "Use only governed summary facts and listed refs." in message
    assert "不主动触发 external-readonly fetch/search" in message
    assert "自然语言完整回答" in message
    assert "JSON / YAML object wrapper" in message
    assert "thought、reasoning、analysis、chain_of_thought、scratchpad" in message
    assert "第一行直接回答问题" in message
    assert "不得以 {、[、```、thought、analysis、reasoning、scratchpad 开头" in message
    assert "信息不足" in message
    assert "ProductGatewayResponse" not in message
    assert "external_readonly_answer_context" not in message
    assert "product_response_summary" not in message
    assert "hidden legacy context" not in message
    assert "hidden raw payload" not in message
    assert "raw_payload" not in message
    assert "hidden excerpt must stay out" not in message
    assert "sanitized_excerpt_preview" not in message
    assert "hidden observation body" not in message
    assert "observability_candidate_body" not in message
    assert "hidden config value" not in message
    assert "config_context_value" not in message


def test_adk_governed_llm_invocation_live_enabled_adds_direct_plan_instruction() -> None:
    fake_client = _FakeLiteLlmClient("方案如下。")
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="我没有概念，请你直接输出方案",
            metadata={
                "interaction_mode": "cli_chat",
                "cli_chat_context": {
                    "current_user_input": "我没有概念，请你直接输出方案",
                    "history": [],
                },
            },
        )
    )

    message = fake_client.calls[0]["messages"][0]["content"]

    assert result.failure_type is None
    assert "本轮执行要求：" in message
    assert "用户要求直接输出方案" in message
    assert "不要反问" in message
    assert "不要说请稍等" in message


def test_adk_governed_llm_invocation_live_enabled_adds_continuation_instruction() -> None:
    fake_client = _FakeLiteLlmClient("继续展开。")
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="继续",
            metadata={
                "interaction_mode": "cli_chat",
                "cli_chat_context": {
                    "current_user_input": "继续",
                    "history": [
                        {
                            "user": "请输出智能家居方案",
                            "assistant": "智能家居方案包括安全、感知和自动化。",
                        }
                    ],
                },
            },
        )
    )

    message = fake_client.calls[0]["messages"][0]["content"]

    assert result.failure_type is None
    assert "用户要求继续" in message
    assert "承接上一轮主题继续输出具体内容" in message
    assert "不要反问从哪里开始" in message


def test_adk_governed_llm_invocation_live_enabled_adds_full_expansion_instruction() -> None:
    fake_client = _FakeLiteLlmClient("全面展开。")
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="全面展开",
            metadata={
                "interaction_mode": "cli_chat",
                "cli_chat_context": {
                    "current_user_input": "全面展开",
                    "history": [],
                },
            },
        )
    )

    message = fake_client.calls[0]["messages"][0]["content"]

    assert result.failure_type is None
    assert "用户要求全面展开" in message
    assert "完整结构化方案" in message
    assert "不要只写开场白" in message


def test_adk_governed_llm_invocation_live_enabled_normalizes_json_response() -> None:
    fake_client = _FakeLiteLlmClient('{"response":"当然可以，我在这里听你说。"}')
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="心情不好，能聊聊吗",
            metadata={"interaction_mode": "cli_chat"},
        )
    )

    assert result.failure_type is None
    assert result.sanitized_response_preview == "当然可以，我在这里听你说。"
    assert result.sanitized_response_length == len("当然可以，我在这里听你说。")


def test_adk_governed_llm_invocation_live_enabled_replaces_internal_json_for_cli_chat() -> None:
    fake_client = _FakeLiteLlmClient(
        (
            '{"system_context":{"role":"AI Solution Architect",'
            '"environment":"Local MacBook M5","protocol_support":"MCP"},'
            '"user_input":"人工智能",'
            '"response_strategy":{"mode":"Cognitive System Terminal Assistant"}}'
        )
    )
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="人工智能",
            metadata={
                "interaction_mode": "cli_chat",
                "cli_chat_context": {
                    "current_user_input": "人工智能",
                    "history": [
                        {
                            "user": "我之前是做销售和运营的",
                            "assistant": "可以从转型方向开始梳理。",
                        }
                    ],
                },
            },
        )
    )

    assert result.failure_type is None
    assert result.sanitized_response_preview is not None
    assert "人工智能" in result.sanitized_response_preview
    assert "system_context" not in result.sanitized_response_preview
    assert "response_strategy" not in result.sanitized_response_preview
    assert not result.sanitized_response_preview.startswith("{")


def test_adk_governed_llm_invocation_live_enabled_replaces_structured_json_for_cli_chat() -> None:
    fake_client = _FakeLiteLlmClient(
        (
            '{"user_input":"人工智能",'
            '"context":"用户正在讨论销售运营背景下的转型方向",'
            '"persona":"认知系统的中文终端聊天助手",'
            '"constraints":["只输出普通中文自然语言"]}'
        )
    )
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="人工智能",
            metadata={
                "interaction_mode": "cli_chat",
                "cli_chat_context": {
                    "current_user_input": "人工智能",
                    "history": [],
                },
            },
        )
    )

    assert result.failure_type is None
    assert result.sanitized_response_preview is not None
    assert "人工智能" in result.sanitized_response_preview
    assert "user_input" not in result.sanitized_response_preview
    assert "constraints" not in result.sanitized_response_preview
    assert not result.sanitized_response_preview.startswith("{")


def test_adk_governed_llm_invocation_live_enabled_direct_plan_json_fallback_is_useful() -> None:
    fake_client = _FakeLiteLlmClient('{"user_input":"请你直接输出方案"}')
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
            metadata={"response_preview_limit": 1000},
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="我没有概念，请你直接输出方案",
            metadata={
                "interaction_mode": "cli_chat",
                "cli_chat_context": {
                    "current_user_input": "我没有概念，请你直接输出方案",
                    "history": [
                        {
                            "user": "如果做一个智能家居方案，可否结合机器视觉？",
                            "assistant": "可以结合机器视觉做智能家居方案。",
                        }
                    ],
                },
            },
        )
    )

    display = result.metadata["sanitized_response_display"]

    assert result.failure_type is None
    assert "可执行方案" in display
    assert "智能家居" in display
    assert "机器视觉" in display
    assert "目标" in display
    assert "风险" in display
    assert "user_input" not in display


def test_adk_governed_llm_invocation_live_enabled_full_expansion_json_fallback_is_useful() -> None:
    fake_client = _FakeLiteLlmClient('{"user_input":"全面展开"}')
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
            metadata={"response_preview_limit": 1000},
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="全面展开",
            metadata={
                "interaction_mode": "cli_chat",
                "cli_chat_context": {
                    "current_user_input": "全面展开",
                    "history": [
                        {
                            "user": "请输出智能家居机器视觉方案",
                            "assistant": "方案包括安防、照护和舒适体验。",
                        }
                    ],
                },
            },
        )
    )

    display = result.metadata["sanitized_response_display"]

    assert result.failure_type is None
    assert "全面展开" in display
    assert "智能家居" in display
    assert "机器视觉" in display
    assert "目标" in display
    assert "风险" in display
    assert "user_input" not in display


def test_adk_governed_llm_invocation_live_enabled_repairs_generic_plan_response() -> None:
    fake_client = _FakeLiteLlmClient(
        [
            (
                "可以，先给你一个通用方案框架：目标先定义清楚，"
                "再拆成感知、分析、决策、执行四层；每层只做一个最小可验证能力。"
            ),
            (
                "## 500只鸡养鸡场方案\n"
                "1. 目标：先稳定饲养、防疫和成本核算。\n"
                "2. 鸡舍：按500只鸡规划通风、温湿度和分区。\n"
                "3. 运营：建立饲料、饮水、清粪和巡检节奏。"
            ),
        ]
    )
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
            metadata={"response_preview_limit": 1000},
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="我要开个养鸡场，帮我设计个方案，规模500只鸡",
            metadata={
                "interaction_mode": "cli_chat",
                "cli_chat_context": {
                    "current_user_input": "我要开个养鸡场，帮我设计个方案，规模500只鸡",
                    "history": [],
                },
            },
        )
    )

    display = result.metadata["sanitized_response_display"]
    repair_prompt = fake_client.calls[1]["messages"][0]["content"]

    assert result.failure_type is None
    assert len(fake_client.calls) == 2
    assert result.metadata["repair_retry_attempted"] is True
    assert result.metadata["repair_retry_performed"] is True
    assert result.metadata["repair_retry_failed"] is False
    assert result.metadata["repair_retry_max_once"] is True
    assert result.metadata["repair_retry_reason"] == "plan_request_not_answered"
    assert "500只鸡" in display
    assert "养鸡场" in display
    assert "失败原因" in repair_prompt
    assert "用户要求方案" in repair_prompt
    assert "上一版 assistant 回复摘要" in repair_prompt
    assert "500只鸡" in repair_prompt
    assert "养鸡场" in repair_prompt
    assert "不反问" in repair_prompt


def test_adk_governed_llm_invocation_live_enabled_repairs_format_rewrite_deflection() -> None:
    fake_client = _FakeLiteLlmClient(
        [
            "请告诉我，您希望我从哪个部分重新开始梳理？",
            (
                "## 500只鸡养鸡场方案\n"
                "### 一、目标\n"
                "把鸡舍、防疫、饲料、饮水和销售节奏整理成一张可执行清单。\n"
                "### 二、模块\n"
                "1. 场地与鸡舍；2. 饲养管理；3. 成本与风险。"
            ),
        ]
    )
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
            metadata={"response_preview_limit": 1000},
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="你先给我重新做个排版吧，当前的有点乱",
            metadata={
                "interaction_mode": "cli_chat",
                "cli_chat_context": {
                    "current_user_input": "你先给我重新做个排版吧，当前的有点乱",
                    "history": [
                        {
                            "user": "我要开个养鸡场，帮我设计个方案，规模500只鸡",
                            "assistant": "感知层、鸡舍、饲料、防疫和成本都要考虑。",
                        }
                    ],
                },
            },
        )
    )

    display = result.metadata["sanitized_response_display"]
    repair_prompt = fake_client.calls[1]["messages"][0]["content"]

    assert result.failure_type is None
    assert len(fake_client.calls) == 2
    assert result.metadata["repair_retry_reason"] == "direct_request_deflected"
    assert "500只鸡" in display
    assert "养鸡场" in display
    assert "请告诉我" not in display
    assert "上一版 assistant 回复摘要" in repair_prompt
    assert "感知层、鸡舍、饲料、防疫和成本都要考虑" in repair_prompt
    assert "如果用户要求重新排版，请直接重排已有内容" in repair_prompt


def test_adk_governed_llm_invocation_live_enabled_repairs_structured_json_without_display() -> None:
    fake_client = _FakeLiteLlmClient(
        [
            '{"user_input":"我要开个养鸡场","constraints":["No JSON"]}',
            "## 养鸡场方案\n1. 先明确规模、场地、防疫和销售路径。",
        ]
    )
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
            metadata={"response_preview_limit": 1000},
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="我要开个养鸡场，帮我设计个方案",
            metadata={
                "interaction_mode": "cli_chat",
                "cli_chat_context": {
                    "current_user_input": "我要开个养鸡场，帮我设计个方案",
                    "history": [],
                },
            },
        )
    )

    display = result.metadata["sanitized_response_display"]

    assert result.failure_type is None
    assert len(fake_client.calls) == 2
    assert result.metadata["repair_retry_reason"] == "structured_json_without_display"
    assert "养鸡场方案" in display
    assert "user_input" not in display


def test_adk_governed_llm_invocation_live_enabled_does_not_repair_plain_chat() -> None:
    fake_client = _FakeLiteLlmClient("你好！我在这里。")
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="你好",
            metadata={
                "interaction_mode": "cli_chat",
                "cli_chat_context": {
                    "current_user_input": "你好",
                    "history": [],
                },
            },
        )
    )

    assert result.failure_type is None
    assert len(fake_client.calls) == 1
    assert result.metadata["repair_retry_attempted"] is False
    assert result.metadata["repair_retry_performed"] is False
    assert "repair_retry_reason" not in result.metadata


def test_adk_governed_llm_invocation_live_enabled_repair_is_max_once() -> None:
    fake_client = _FakeLiteLlmClient(
        [
            "可以，先给你一个通用方案框架：目标先定义清楚，再逐步扩大功能。",
            "可以，先给你一个通用方案框架：目标先定义清楚，再逐步扩大功能。",
            "这一条不应该被调用。",
        ]
    )
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="我要开个养鸡场，帮我设计个方案，规模500只鸡",
            metadata={
                "interaction_mode": "cli_chat",
                "cli_chat_context": {
                    "current_user_input": "我要开个养鸡场，帮我设计个方案，规模500只鸡",
                    "history": [],
                },
            },
        )
    )

    assert result.failure_type is None
    assert len(fake_client.calls) == 2
    assert result.metadata["repair_retry_attempted"] is True
    assert result.metadata["repair_retry_performed"] is True
    assert result.metadata["repair_retry_max_once"] is True


def test_adk_governed_llm_invocation_live_enabled_replaces_truncated_internal_json_for_cli_chat() -> None:
    fake_client = _FakeLiteLlmClient(
        '{"system_context":{"role":"AI Solution Architect"},"user_input":"你怎么了？"'
    )
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="你怎么了？",
            metadata={
                "interaction_mode": "cli_chat",
                "cli_chat_context": {
                    "current_user_input": "你怎么了？",
                    "history": [],
                },
            },
        )
    )

    assert result.failure_type is None
    assert result.sanitized_response_preview is not None
    assert "格式跑偏" in result.sanitized_response_preview
    assert "system_context" not in result.sanitized_response_preview
    assert not result.sanitized_response_preview.startswith("{")


def test_adk_governed_llm_invocation_live_enabled_extracts_truncated_json_response() -> None:
    fake_client = _FakeLiteLlmClient('{"response":"这是一个被截断但仍可展示的回复')
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="请详细解释这部电影",
            metadata={"interaction_mode": "cli_chat"},
        )
    )

    assert result.failure_type is None
    assert result.sanitized_response_preview == "这是一个被截断但仍可展示的回复"
    assert '{"response"' not in (result.sanitized_response_preview or "")


def test_adk_governed_llm_invocation_live_enabled_honors_response_preview_limit() -> None:
    output_text = (
        "这是一段比较长的终端聊天回复，用于验证 chat 可以展示更长的脱敏预览。"
        "它不会改变 LlmInvocationResult 的 preview 契约，但会把脱敏展示文本放入 metadata。"
    )
    fake_client = _FakeLiteLlmClient(output_text)
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
            metadata={"response_preview_limit": 200},
        )
    )

    result = service.invoke(
        _request(
            allowed=True,
            prompt_preview_sanitized="请详细解释这部电影",
            metadata={"interaction_mode": "cli_chat"},
        )
    )

    assert result.failure_type is None
    assert result.sanitized_response_preview == output_text[:120]
    assert result.sanitized_response_length == len(output_text)
    assert result.metadata["sanitized_response_display"] == output_text


def test_adk_governed_llm_invocation_live_enabled_sets_local_no_proxy(
    monkeypatch,
) -> None:
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    fake_client = _FakeLiteLlmClient("controlled live output")
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
            ollama_api_base="http://127.0.0.1:11434",
        )
    )

    result = service.invoke(_request(allowed=True))

    assert result.failure_type is None
    assert "127.0.0.1" in os.environ["NO_PROXY"].split(",")
    assert "localhost" in os.environ["NO_PROXY"].split(",")
    assert "127.0.0.1" in os.environ["no_proxy"].split(",")
    assert "localhost" in os.environ["no_proxy"].split(",")
    assert result.metadata["llm_live_profile"]["local_no_proxy_applied"] is True


def test_adk_governed_llm_invocation_live_enabled_requires_prompt_preview() -> None:
    fake_client = _FakeLiteLlmClient("unused")
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
        )
    )

    result = service.invoke(_request(allowed=True, prompt_preview_sanitized=None))

    assert result.failure_type == LlmInvocationFailureType.LIVE_CALL_FAILURE
    assert result.call_attempted is False
    assert result.call_allowed is True
    assert result.runtime_call_performed is False
    assert fake_client.calls == []


def test_adk_governed_llm_invocation_live_enabled_sanitizes_fake_failure() -> None:
    fake_client = _FailingLiteLlmClient(
        RuntimeError("raw_response carried prompt and secret token")
    )
    service = AdkGovernedLlmInvocationService(
        options=AdkGovernedLlmInvocationOptions(
            live_enabled=True,
            live_client=fake_client,
        )
    )

    result = service.invoke(_request(allowed=True))

    assert result.failure_type == LlmInvocationFailureType.LIVE_CALL_FAILURE
    assert result.call_attempted is True
    assert result.call_allowed is True
    assert result.runtime_call_performed is True
    assert result.success is False
    assert "raw_response" not in (result.error_message_sanitized or "")
    assert "prompt" not in (result.error_message_sanitized or "")
    assert "secret" not in (result.error_message_sanitized or "")
    assert "token" not in (result.error_message_sanitized or "")


def test_adk_governed_llm_invocation_result_builds_observation_candidate() -> None:
    service = AdkGovernedLlmInvocationService()
    result = service.invoke(_request(allowed=True))

    observation = build_llm_call_observation_candidate(result)

    assert observation.provider == "litellm"
    assert observation.backend_provider == "ollama"
    assert observation.route_kind == "adk_litellm"
    assert observation.failure_type == "live_disabled"
    assert observation.metadata["does_not_call_model"] is True


def test_adk_governed_llm_invocation_source_does_not_call_model_or_runner() -> None:
    source = (ADK_ADAPTER_SOURCE_ROOT / "llm_invocation.py").read_text(
        encoding="utf-8"
    )
    forbidden_calls = re.compile(
        r"\b(?:acompletion|runner\.run|run_async)\s*\("
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+litellm\b",
        re.MULTILINE,
    )

    assert forbidden_calls.search(source) is None
    assert forbidden_imports.search(source) is None
    assert "from google.adk.models.lite_llm import LiteLLMClient" in source
    assert "product_application_assembly" not in source
    assert "product_runtime_assembly" not in source
    assert "runtime_container" not in source
    assert "from composition" not in source
    assert "product_gateway" not in source


def _request(
    *,
    allowed: bool,
    decision: str = "continue",
    route_facts: ModelRouteFacts | None = None,
    prompt_preview_sanitized: str | None = "sanitized prompt preview",
    metadata: dict[str, object] | None = None,
) -> LlmInvocationRequest:
    return LlmInvocationRequest(
        request_id="llm-request-1",
        route_facts=route_facts or _route_facts(),
        governance_precondition=LlmGovernancePrecondition(
            allowed=allowed,
            reason="governance_allowed" if allowed else "governance_denied",
            decision=decision,
            governance_decision_ref="governance-decision-1",
        ),
        prompt_ref="prompt-ref-1",
        prompt_preview_sanitized=prompt_preview_sanitized,
        metadata=metadata or {},
    )


def _route_facts(
    *,
    metadata: dict[str, str] | None = None,
) -> ModelRouteFacts:
    return ModelRouteFacts(
        model_name="ollama/gemma4-pro:latest",
        provider="litellm",
        source="adk_adapter.models",
        metadata=metadata
        or {
            "backend_provider": "ollama",
            "route_target": "ollama/gemma4-pro:latest",
            "route_kind": "adk_litellm",
        },
    )


class _FakeLiteLlmClient:
    def __init__(self, content: str | list[str]) -> None:
        self._contents = [content] if isinstance(content, str) else list(content)
        self.calls: list[dict[str, object]] = []

    def completion(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        tools: list[object],
        **kwargs: object,
    ) -> object:
        content = self._contents[min(len(self.calls), len(self._contents) - 1)]
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "tools": tools,
                **kwargs,
            }
        )
        return {
            "choices": [
                {
                    "message": {
                        "content": content,
                    },
                }
            ]
        }


class _FailingLiteLlmClient:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def completion(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        tools: list[object],
        **kwargs: object,
    ) -> object:
        raise self._exc
