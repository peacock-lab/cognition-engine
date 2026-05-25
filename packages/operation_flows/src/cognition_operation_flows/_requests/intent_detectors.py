"""Local intent detectors for operation flow routing candidates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re


PLAN_DISPLAY_PREVIEW_LIMIT = 4000
PLAN_REQUEST_KEYWORDS = (
    "方案",
    "设计",
    "规划",
    "建设",
    "搭建",
    "实施",
    "部署",
    "开个",
    "建一个",
)
PLAN_DOMAIN_KEYWORDS = (
    "鱼塘",
    "养鸡场",
    "鸡场",
    "农场",
    "厂房",
    "门店",
)
FORMAT_REQUEST_KEYWORDS = ("排版", "换行", "重排", "整理", "太乱", "格式")
PLAN_CONTINUATION_KEYWORDS = (
    "所有的",
    "全部",
    "完整",
    "继续",
    "展开",
    "详细",
    "细节",
    "深入",
    "发给我",
    "发给我吧",
    "给我吧",
    "全面展开",
)

OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME = "operation_flow_reference_review_workflow"
OPERATION_FLOW_REFERENCE_REVIEW_TASK_KIND = "reference_review"
REFERENCE_REVIEW_KEYWORDS = (
    "查",
    "查看",
    "查找",
    "找",
    "读取",
    "审查",
    "复核",
    "检查",
    "评审",
    "文件",
    "文件夹",
    "目录",
    "任务包",
    "结果包",
    "编号",
    "总结",
    "摘要",
    "整理",
    "梳理",
    "专有名词",
    "术语",
    "提炼",
    "对比",
    "差异",
    "风险",
    "问题",
    "建议",
    "是否符合",
    "是否一致",
    "是否需要更新",
    "看看",
)
REFERENCE_REVIEW_STRONG_KEYWORDS = (
    "查找",
    "审查",
    "复核",
    "检查",
    "评审",
    "读取",
    "摘要",
    "整理",
    "梳理",
    "专有名词",
    "术语",
    "文件",
    "文件夹",
    "目录",
    "对比",
    "差异",
    "风险",
    "问题",
    "是否符合",
    "是否一致",
    "是否需要更新",
)

OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME = "operation_flow_config_profile_explain_workflow"
OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_TASK_KIND = "config_profile_explain"
CONFIG_PROFILE_EXPLAIN_DISPLAY_PREVIEW_LIMIT = 4000
CONFIG_PROFILE_EXPLAIN_KEYWORDS = (
    "解释配置",
    "配置为什么",
    "配置生效",
    "配置来源",
    "覆盖关系",
    "当前配置",
    "配置解释",
    "profile",
    "config profile",
    "tool exposure",
    "工具暴露",
    "reference-reader",
    "reference reader",
    "run workspace",
    "运行工作区",
    "live llm",
    "ollama",
    "approval",
    "audit",
    "risk",
    "output budget",
    "live gate",
)
CONFIG_PROFILE_MUTATION_MARKERS = (
    "修改配置",
    "写配置",
    "更新配置",
    "改配置",
    "设置配置",
    "生成配置文件",
)
RUNTIME_OPEN_MARKERS = ("打开", "开启", "启用", "接入", "集成", "上线")
PROTECTED_RUNTIME_TERMS = ("Agent runtime", "Skills runtime", "ADK SkillRegistry")

OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME = (
    "operation_flow_run_workspace_evidence_audit_workflow"
)
OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_TASK_KIND = "run_workspace_evidence_audit"
RUN_WORKSPACE_EVIDENCE_AUDIT_DISPLAY_PREVIEW_LIMIT = 4000
AUDIT_WORKSPACE_KEYWORDS = (
    "审计 run workspace",
    "审计 workspace",
    "检查运行工作区",
    "运行工作区证据",
    "证据完整",
    "证据链",
    "manifest 是否完整",
    "结果文件齐",
    "workspace evidence",
    "evidence audit",
    "run workspace audit",
)


def detect_operation_flow_plan_request(
    user_text: str,
    *,
    history: Sequence[Mapping[str, str]] | None = None,
    previous_plan_text: str | None = None,
) -> bool:
    """Return whether a turn should route into the plan workflow."""

    normalized = _compact_without_spaces(user_text)
    if not normalized:
        return False
    has_plan_intent = any(keyword in normalized for keyword in PLAN_REQUEST_KEYWORDS)
    has_domain = any(keyword in normalized for keyword in PLAN_DOMAIN_KEYWORDS)
    if has_plan_intent and (has_domain or "方案" in normalized):
        return True
    has_previous_plan = bool(previous_plan_text) or _history_contains_plan(history or ())
    if has_previous_plan and any(
        keyword in normalized for keyword in FORMAT_REQUEST_KEYWORDS
    ):
        return True
    if has_previous_plan and any(
        keyword in normalized for keyword in PLAN_CONTINUATION_KEYWORDS
    ):
        return True
    return False


def detect_operation_flow_reference_review_request(
    user_text: str,
    *,
    reference_paths: Sequence[str] = (),
    external_readonly_evidence_paths: Sequence[str] = (),
) -> bool:
    """Return whether a turn should route into reference review."""

    normalized = _compact_with_spaces(user_text)
    has_reference_material = bool(
        tuple(path for path in reference_paths if path.strip())
        or tuple(path for path in external_readonly_evidence_paths if path.strip())
    )
    if not normalized or not has_reference_material:
        return False
    lowered = normalized.lower()
    has_review_intent = any(
        keyword.lower() in lowered for keyword in REFERENCE_REVIEW_KEYWORDS
    )
    if not has_review_intent:
        return False
    has_strong_review_intent = any(
        keyword.lower() in lowered for keyword in REFERENCE_REVIEW_STRONG_KEYWORDS
    )
    if detect_operation_flow_plan_request(user_text) and not has_strong_review_intent:
        return False
    return True


def detect_operation_flow_config_profile_explain_request(user_text: str) -> bool:
    """Return whether a turn should route into config profile explain."""

    normalized = _compact_with_spaces(user_text)
    if not normalized:
        return False
    lowered = normalized.lower()
    if any(marker in normalized for marker in CONFIG_PROFILE_MUTATION_MARKERS):
        return False
    if _requests_protected_runtime_open(normalized):
        return False
    return any(keyword.lower() in lowered for keyword in CONFIG_PROFILE_EXPLAIN_KEYWORDS)


def detect_operation_flow_run_workspace_evidence_audit_request(
    user_text: str,
    *,
    audit_target_requested: bool = False,
) -> bool:
    """Return whether a turn should route into run workspace evidence audit."""

    normalized = _compact_with_spaces(user_text)
    if not normalized or not audit_target_requested:
        return False
    lowered = normalized.lower()
    return any(keyword.lower() in lowered for keyword in AUDIT_WORKSPACE_KEYWORDS)


def _history_contains_plan(history: Sequence[Mapping[str, str]]) -> bool:
    for item in history:
        assistant = item.get("assistant")
        if isinstance(assistant, str) and "建设方案" in assistant:
            return True
    return False


def _requests_protected_runtime_open(value: str) -> bool:
    lowered = value.lower()
    has_runtime = any(term.lower() in lowered for term in PROTECTED_RUNTIME_TERMS)
    if not has_runtime:
        return False
    return any(marker in value for marker in RUNTIME_OPEN_MARKERS)


def _compact_without_spaces(value: str) -> str:
    return "".join(value.strip().split())


def _compact_with_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()
