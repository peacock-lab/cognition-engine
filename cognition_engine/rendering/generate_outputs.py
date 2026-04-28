#!/usr/bin/env python3
"""
产出生成器 - 从洞察生成价值产出
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cognition_engine.formal_entries.insight_formal_entry import build_insight_formal_entry_record
from cognition_engine.formal_entries.framework_metadata_formal_entry import (
    build_framework_metadata_formal_entry_record,
)

NEW_PROJECT_PATH = Path(__file__).resolve().parents[2]

DATA_DIR_ENV = "CE_DATA_DIR"
INSIGHTS_DIR_ENV = "CE_INSIGHTS_DIR"


def resolve_data_dir() -> Path:
    """Resolve the runtime data directory."""
    env_value = os.environ.get(DATA_DIR_ENV)
    if env_value:
        return Path(env_value).expanduser().resolve()

    cwd_candidate = Path.cwd() / "data"
    if cwd_candidate.exists():
        return cwd_candidate

    return NEW_PROJECT_PATH / "data"


def resolve_insights_dir() -> Path:
    """Resolve the runtime insights directory.

    Priority:
    1. CE_INSIGHTS_DIR environment variable.
    2. CE_DATA_DIR/insights.
    3. data/insights under the current working directory.
    4. data/insights near the installed package location.
    """
    env_value = os.environ.get(INSIGHTS_DIR_ENV)
    if env_value:
        return Path(env_value).expanduser().resolve()

    return resolve_data_dir() / "insights"


def resolve_frameworks_dir() -> Path:
    """Resolve the runtime frameworks directory."""
    return resolve_data_dir() / "frameworks"

IMPACT_LABELS = {
    "high": "高",
    "medium": "中",
    "low": "低",
}

SENTENCE_ENDINGS = ("。", "！", "？", ".", "!", "?", "：", ":")

CATEGORY_BRIEF_PLAYBOOK = {
    "core_coordination": {
        "primary_use_case": "把请求执行、事件消费、状态收口和结果回传统一收进一个可治理的运行总控层。",
        "user_problem": "当执行主链分散在多个入口、节点或回调里时，团队很难解释谁负责创建上下文、谁负责收口结果、谁对外回传。",
        "product_claim": "将 Runner 视为正式请求总控层，并围绕它定义统一的执行主链、状态收口约束和对外回传接口。",
        "value_points": [
            "减少请求执行责任散落导致的架构歧义。",
            "让 Session、InvocationContext 和事件链的职责边界更容易讲清楚。",
            "为后续验证、观测和回归检查提供单一主锚点。",
        ],
        "boundary": "当前先聚焦普通请求主链与结果收口，不把不同协议层或发布层一次性并入改造范围。",
        "next_steps": [
            "把 Runner 主链职责整理成内部架构说明和接口约束。",
            "围绕 Session 创建、事件 append、结果回传补一轮回归检查点。",
            "将相关洞察串成执行主链蓝图，支撑后续产品化表达。",
        ],
    },
    "state_management": {
        "primary_use_case": "把长期状态、调用控制面和节点局部视图拆清，避免多层上下文混写。",
        "user_problem": "状态长期宿主、调用期控制面和节点局部视图经常被混成一层，导致调试困难、迁移风险高。",
        "product_claim": "将 Session、InvocationContext 和 Context 作为三层正式状态寄宿面，形成可验证的状态边界模型。",
        "value_points": [
            "降低状态写入位置不清导致的回归风险。",
            "帮助团队在重构和迁移时保持状态语义稳定。",
            "让状态变化和事件附着关系更容易被解释与复盘。",
        ],
        "boundary": "当前先把状态边界讲清，不延伸到完整状态平台或多租户治理设计。",
        "next_steps": [
            "把状态宿主和局部视图的职责写成开发约束。",
            "补充状态变更与事件附着关系的最小验证样例。",
            "用状态边界模型反查现有执行路径中的歧义点。",
        ],
    },
    "communication_pattern": {
        "primary_use_case": "把结果事件、状态变化和动作执行收进一条统一可解释的事件收口链。",
        "user_problem": "当事件只被当成消息载体而不是正式收口链时，结果回传、状态附着和动作执行容易分裂。",
        "product_claim": "将 Event 与 EventActions 抽象为统一的收口机制，使结果、状态和动作都能沿同一链路落地。",
        "value_points": [
            "提高输出回传、状态收口和动作执行之间的一致性。",
            "减少跨节点协作时的隐式耦合。",
            "为后续监控、审计和最小验证提供统一证据面。",
        ],
        "boundary": "当前先围绕单条事件收口链治理，不扩展到完整消息平台或多通道编排系统。",
        "next_steps": [
            "识别当前事件对象中必须稳定的最小字段集合。",
            "补充 append、yield 和 state_delta 之间的主链说明。",
            "把事件收口链转成对外可讲的能力模块与验收项。",
        ],
    },
    "protocol_layering": {
        "primary_use_case": "在多入口形态下维持同一条执行主链和一致的状态语义。",
        "user_problem": "当不同入口被误解成多套运行时，团队会重复设计状态模型和执行逻辑，导致维护成本上升。",
        "product_claim": "把 /run、/run_sse、/run_live 解释为入口分层问题，而不是三套割裂运行时，并围绕共享主链治理接口差异。",
        "value_points": [
            "减少入口扩展时的重复实现与重复维护。",
            "帮助团队在协议层演进时保持底层运行时模型稳定。",
            "让不同入口的边界说明更容易形成统一口径。",
        ],
        "boundary": "当前先统一入口分层口径，不同时推进多协议网关或前端交互层全面改造。",
        "next_steps": [
            "补入口分层说明，固定共享主链与差异点。",
            "为普通路径和 live 路径分别补最小验证样例。",
            "把协议差异映射到文档和验收清单，而不是运行时分叉。",
        ],
    },
}

def load_insight(insight_id: str) -> Optional[Dict[str, Any]]:
    """加载指定ID的洞察"""
    insights_dir = resolve_insights_dir()
    if not insights_dir.exists():
        return None

    for framework_dir in insights_dir.iterdir():
        if framework_dir.is_dir():
            insight_file = framework_dir / f"{insight_id}.json"
            if insight_file.exists():
                with open(insight_file, 'r', encoding='utf-8') as f:
                    return build_insight_formal_entry_record(json.load(f))

    return None

def load_framework(framework_id: str) -> Optional[Dict[str, Any]]:
    """加载框架元数据"""
    framework_file = resolve_frameworks_dir() / framework_id / "metadata.json"
    if framework_file.exists():
        with open(framework_file, 'r', encoding='utf-8') as f:
            return build_framework_metadata_formal_entry_record(json.load(f))
    return None


def format_evidence_summary(evidence: Dict[str, Any]) -> Optional[str]:
    """把不同证据类型转成可直接展示的摘要。"""
    evidence_type = evidence.get("type", "unknown")

    if evidence_type == "code_reference" and evidence.get("file"):
        section = evidence.get("source_section")
        if section:
            return f"- 代码位置: `{evidence['file']}` | 章节 `{section}`"
        return f"- 代码位置: `{evidence['file']}`"

    if evidence_type == "call_chain":
        entry_point = evidence.get("entry_point")
        chain = evidence.get("chain", [])
        chain_summary = " -> ".join(chain) if chain else "N/A"
        parts = ["- 调用链"]
        if entry_point:
            parts.append(f"起点 `{entry_point}`")
        parts.append(f"链路 `{chain_summary}`")
        source_section = evidence.get("source_section")
        if source_section:
            parts.append(f"章节 `{source_section}`")
        return " | ".join(parts)

    if evidence_type == "validation_result":
        return f"- 验证结果: {evidence.get('result', 'N/A')}"

    source_file = evidence.get("source_file")
    source_section = evidence.get("source_section")
    quote = evidence.get("quote")

    if source_file or source_section or quote:
        parts = [f"- 证据来源: {evidence_type}"]
        if source_file:
            parts.append(f"文件 `{source_file}`")
        if source_section:
            parts.append(f"章节 `{source_section}`")
        if quote:
            parts.append(f"摘录: {quote}")
        return " | ".join(parts)

    return None


def format_impact_label(level: str) -> str:
    return IMPACT_LABELS.get(level, level or "unknown")


def ensure_sentence_ending(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        return normalized
    if normalized.endswith(SENTENCE_ENDINGS):
        return normalized
    return f"{normalized}。"


def format_tag_summary(tags: list[str]) -> str:
    if not tags:
        return "暂无显式标签"
    return "、".join(tag.replace("_", " ") for tag in tags)


def resolve_related_insight_title(insight_id: str) -> str:
    related_insight = load_insight(insight_id)
    if related_insight:
        return related_insight["title"]
    return insight_id


def build_product_brief_context(
    insight: Dict[str, Any],
    framework: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a structured, scenario-driven context for a product brief."""
    playbook = CATEGORY_BRIEF_PLAYBOOK.get(
        insight.get("category", ""),
        {
            "primary_use_case": "把当前洞察沉淀成可复用的产品化表达和执行约束。",
            "user_problem": "团队需要把已有技术洞察转成可解释、可执行、可复用的产品化表达。",
            "product_claim": "围绕该洞察建立一份可直接复用的产品简报，并明确适用场景、价值和边界。",
            "value_points": [
                "让洞察不只停留在技术说明，而是能直接支撑方案沟通。",
                "减少从分析结论到产品表达之间的二次转换成本。",
                "为后续验证和推广提供统一的文字锚点。",
            ],
            "boundary": "当前只做单洞察、单简报的最小闭环，不扩展到多模板、多受众或发布流程。",
            "next_steps": [
                "把该洞察转成更明确的执行约束。",
                "围绕输出内容补充验证样例。",
                "根据真实使用反馈继续迭代模板。",
            ],
        },
    )

    evidence_points = []
    for evidence in insight.get("evidence", [])[:3]:
        summary_line = format_evidence_summary(evidence)
        if summary_line:
            evidence_points.append(summary_line)
    if not evidence_points:
        evidence_points.append("- 当前无可直接渲染的证据摘要，但该洞察已存在于正式结构化对象中。")

    related_points = []
    for connection in insight.get("connections", [])[:3]:
        related_title = resolve_related_insight_title(connection["insight_id"])
        related_description = connection.get("description") or f"{related_title} 与当前洞察存在 {connection['type']} 关系。"
        related_points.append(
            f"- {related_title}: {related_description}"
        )
    if not related_points:
        related_points.append("- 当前未声明直接相关洞察。")

    confidence_pct = insight["confidence"] * 100
    impact_summary = (
        f"架构影响 {format_impact_label(insight['impact']['architectural'])}"
        f" / 迁移影响 {format_impact_label(insight['impact']['migration'])}"
        f" / 产品影响 {format_impact_label(insight['impact']['product'])}"
    )
    tag_summary = format_tag_summary(insight.get("tags", []))
    executive_summary = (
        f"{ensure_sentence_ending(insight['description'])} 这意味着我们可以把“{insight['title']}”"
        f"从技术判断进一步沉淀为面向真实团队协作的产品化能力表达。"
    )
    target_users = [
        "架构负责人：需要把技术主链讲清并转成团队共识。",
        "技术负责人：需要把洞察转成可执行的系统设计或迁移动作。",
        "产品负责人：需要理解该技术能力会怎样影响交付边界与价值主张。",
    ]

    return {
        "title": insight["title"],
        "framework_name": framework["name"],
        "framework_version": framework["version"],
        "insight_id": insight["id"],
        "category": insight["category"],
        "tag_summary": tag_summary,
        "confidence_pct": confidence_pct,
        "impact_summary": impact_summary,
        "executive_summary": executive_summary,
        "primary_use_case": playbook["primary_use_case"],
        "user_problem": playbook["user_problem"],
        "product_claim": playbook["product_claim"],
        "value_points": playbook["value_points"],
        "boundary": playbook["boundary"],
        "next_steps": playbook["next_steps"],
        "target_users": target_users,
        "evidence_points": evidence_points,
        "related_points": related_points,
        "recommended_action": playbook["next_steps"][0],
    }

def generate_article_from_insight(insight: Dict[str, Any], 
                                 framework: Dict[str, Any]) -> str:
    """从洞察生成文章"""
    
    # 提取证据摘要
    evidence_summary = []
    for evidence in insight.get("evidence", []):
        summary_line = format_evidence_summary(evidence)
        if summary_line:
            evidence_summary.append(summary_line)
    
    # 提取相关洞察
    related_insights = []
    for connection in insight.get("connections", []):
        related_insight = load_insight(connection["insight_id"])
        if related_insight:
            related_insights.append(f"- {related_insight['title']} ({connection['type']})")
    
    # 生成文章内容
    article = f"""# {insight['title']}

## 框架背景
- **框架**: {framework['name']} {framework['version']}
- **分析深度**: {framework['metadata']['analysis_depth']}
- **置信度**: {insight['confidence'] * 100:.0f}%

## 洞察摘要
{insight['description']}

## 架构影响
- **架构重要性**: {insight['impact']['architectural']}
- **迁移影响**: {insight['impact']['migration']}
- **产品影响**: {insight['impact']['product']}

## 证据支撑
{chr(10).join(evidence_summary) if evidence_summary else "暂无可直接渲染的证据摘要"}

## 相关洞察
{chr(10).join(related_insights) if related_insights else "暂无相关洞察"}

## 标签
{', '.join(insight['tags'])}

## 产品化建议

### 1. 直接应用
基于此洞察，可以：

1. **设计类似架构**: 在自有项目中采用相似的{insight['category']}模式
2. **优化现有系统**: 检查现有系统是否缺少类似的{insight['category']}机制
3. **评估迁移成本**: 估算从其他方案迁移到此模式的工作量

### 2. 风险提示
需要注意：

1. **实现复杂度**: {insight['category']}模式可能引入额外的协调开销
2. **学习曲线**: 团队需要时间理解此模式的运作机制
3. **维护成本**: 确保有足够的文档和测试覆盖

### 3. 下一步行动
建议：

1. **创建验证样本**: 编写最小可运行代码验证此模式
2. **设计迁移路径**: 如果适用，规划从当前方案到此模式的迁移步骤
3. **监控实施效果**: 在实际应用中收集性能和使用反馈

## 技术细节

### 代码示例
```python
# 基于{insight['title']}的简化实现示例
# 注意: 这是概念性代码，非实际ADK代码

class Simplified{insight['category'].title().replace('_', '')}:
    def __init__(self):
        self.state = {{}}
        self.events = []
    
    def coordinate(self, task):
        \"\"\"协调执行流程\"\"\"
        # 实现{insight['title']}的核心逻辑
        pass
    
    def update_state(self, key, value):
        \"\"\"状态更新\"\"\"
        self.state[key] = value
    
    def add_event(self, event):
        \"\"\"事件处理\"\"\"
        self.events.append(event)
```

### 验证方法
1. **单元测试**: 验证核心协调逻辑
2. **集成测试**: 验证与其他组件的交互
3. **性能测试**: 验证在高负载下的表现
4. **回归测试**: 确保修改不影响现有功能

## 总结
{insight['title']}是{framework['name']}架构中的关键模式，具有{insight['impact']['architectural']}的架构重要性。建议在理解其实现细节和潜在风险的基础上，谨慎评估在自有项目中的应用价值。

---
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*  
*数据来源: cognition-engine/data/insights/{insight['framework_id']}/{insight['id']}.json*  
*框架信息: {framework['name']} {framework['version']}*
"""
    
    return article

def generate_product_brief(insight: Dict[str, Any],
                          framework: Dict[str, Any]) -> str:
    """从洞察生成产品简报"""

    context = build_product_brief_context(insight, framework)
    brief = f"""# 产品简报: {context['title']}

## 一页结论
{context['executive_summary']}

- **推荐落点**: {context['product_claim']}
- **主要适用场景**: {context['primary_use_case']}
- **影响判断**: {context['impact_summary']}
- **标签**: {context['tag_summary']}

## 适用场景
- 适用于正在梳理 {context['framework_name']} 相关架构主链、迁移路径或产品能力边界的团队。
- 适用于需要把单条技术洞察直接转成内部简报、设计说明或最小决策材料的场景。
- 当前最适合从单洞察、单能力切入，而不是一次性拉起多闭环产品面。

## 目标使用者
1. {context['target_users'][0]}
2. {context['target_users'][1]}
3. {context['target_users'][2]}

## 用户问题
{context['user_problem']}

## 产品主张
1. {context['value_points'][0]}
2. {context['value_points'][1]}
3. {context['value_points'][2]}

## 上线边界
{context['boundary']}

## 证据与可信度
- **框架**: {context['framework_name']} {context['framework_version']}
- **洞察来源**: {context['insight_id']}
- **置信度**: {context['confidence_pct']:.0f}%
- **证据摘要**:
{chr(10).join(context['evidence_points'])}

## 相关洞察
{chr(10).join(context['related_points'])}

## 下一步行动
1. {context['next_steps'][0]}
2. {context['next_steps'][1]}
3. {context['next_steps'][2]}

---
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*  
*洞察来源: {context['insight_id']}*  
*置信度: {context['confidence_pct']:.0f}%*
"""

    return brief


def generate_decision_pack(insight: Dict[str, Any],
                           framework: Dict[str, Any]) -> str:
    """从单条洞察生成最小 decision-pack Markdown。"""

    context = build_product_brief_context(insight, framework)
    decision_pack = f"""# 决策包: {context['title']}

## 一页结论
{context['executive_summary']}

- **待决问题**: 是否应围绕“{context['title']}”形成明确的执行取舍。
- **推荐方案**: {context['product_claim']}
- **建议下一步**: {context['recommended_action']}

## 决策问题
团队是否应将该洞察从技术判断推进为可执行的产品化或架构治理动作。

## 背景与证据
- **框架**: {context['framework_name']} {context['framework_version']}
- **洞察来源**: {context['insight_id']}
- **置信度**: {context['confidence_pct']:.0f}%
- **影响判断**: {context['impact_summary']}
- **证据摘要**:
{chr(10).join(context['evidence_points'])}

## 可选方案
1. 暂缓处理：仅保留该洞察为结构化记录，不进入执行规划。
2. 轻量推进：围绕该洞察形成最小说明、边界和验证动作。
3. 正式推进：将该洞察纳入正式产品化或架构治理路线。

## 推荐方案
建议采用轻量推进。

## 取舍理由
1. 当前洞察已经具备明确来源和可信度，可支撑最小决策材料。
2. 轻量推进可以避免直接放大为完整项目，降低误判和过度承诺风险。
3. 该方式保留后续升级为正式闭环的空间。

## 风险与边界
{context['boundary']}

当前不把该决策包写成正式签发、发布承诺或多洞察综合决策。

## 下一步行动
1. {context['next_steps'][0]}
2. {context['next_steps'][1]}
3. {context['next_steps'][2]}

---
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*  
*洞察来源: {context['insight_id']}*  
*置信度: {context['confidence_pct']:.0f}%*
"""

    return decision_pack

def save_output_record(
    content: str,
    output_slug: str,
    insight_id: str,
    framework_id: str,
    format: str = "md",
    metadata_type: Optional[str] = None,
) -> Dict[str, Any]:
    """保存产出文件并返回文件与元数据记录。"""

    # 创建输出目录
    output_dir = NEW_PROJECT_PATH / "outputs" / output_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    filename = f"{output_slug}-{framework_id}-{insight_id}-{timestamp}.{format}"
    output_file = output_dir / filename

    # 保存文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

    # 记录产出元数据
    output_metadata = {
        "id": f"output-{timestamp}",
        "type": metadata_type or output_slug,
        "title": content.split('\n')[0].replace('# ', ''),
        "insight_id": insight_id,
        "framework_id": framework_id,
        "file_path": str(output_file.relative_to(NEW_PROJECT_PATH)),
        "generated_at": datetime.now().isoformat(),
        "format": format,
        "size_bytes": len(content.encode('utf-8'))
    }

    # 保存元数据
    metadata_dir = NEW_PROJECT_PATH / "outputs" / ".metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = metadata_dir / f"{output_metadata['id']}.json"

    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(output_metadata, f, ensure_ascii=False, indent=2)

    return {
        "output_file": output_file,
        "metadata_file": metadata_file,
        "metadata": output_metadata,
    }


def save_output(
    content: str,
    output_slug: str,
    insight_id: str,
    framework_id: str,
    format: str = "md",
    metadata_type: Optional[str] = None,
) -> Path:
    """保存产出文件。"""
    return save_output_record(
        content,
        output_slug,
        insight_id,
        framework_id,
        format,
        metadata_type=metadata_type,
    )["output_file"]

def main():
    """主生成流程"""
    import argparse
    
    parser = argparse.ArgumentParser(description="从洞察生成价值产出")
    parser.add_argument("--insight", required=True, help="洞察ID")
    parser.add_argument("--type", choices=["article", "product-brief", "decision-pack", "both"], 
                       default="article", help="产出类型")
    parser.add_argument("--output-dir", help="自定义输出目录")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("产出生成器")
    print("=" * 60)
    
    # 1. 加载洞察
    insight = load_insight(args.insight)
    if not insight:
        print(f"错误: 未找到洞察 {args.insight}")
        return
    
    print(f"加载洞察: {insight['title']}")
    
    # 2. 加载框架
    framework = load_framework(insight["framework_id"])
    if not framework:
        print(f"错误: 未找到框架 {insight['framework_id']}")
        return
    
    print(f"关联框架: {framework['name']} {framework['version']}")
    
    # 3. 生成产出
    outputs = []
    
    if args.type in ["article", "both"]:
        print("生成文章...")
        article = generate_article_from_insight(insight, framework)
        article_file = save_output(
            article,
            "articles",
            args.insight,
            insight["framework_id"],
            metadata_type="article",
        )
        outputs.append(("文章", article_file))

    if args.type in ["product-brief", "both"]:
        print("生成产品简报...")
        brief = generate_product_brief(insight, framework)
        brief_file = save_output(
            brief,
            "product-briefs",
            args.insight,
            insight["framework_id"],
            metadata_type="product-brief",
        )
        outputs.append(("产品简报", brief_file))

    if args.type in ["decision-pack", "both"]:
        print("生成决策包...")
        decision_pack = generate_decision_pack(insight, framework)
        decision_pack_file = save_output(
            decision_pack,
            "decision-packs",
            args.insight,
            insight["framework_id"],
            metadata_type="decision-pack",
        )
        outputs.append(("决策包", decision_pack_file))
    
    # 4. 显示结果
    print("\n" + "=" * 60)
    print("生成完成!")
    
    for output_type, output_file in outputs:
        rel_path = output_file.relative_to(NEW_PROJECT_PATH)
        print(f"{output_type}: {rel_path}")
    
    print("=" * 60)
    
    # 5. 显示下一步建议
    print("\n下一步建议:")
    print("1. 审查产出内容，确保准确性和实用性")
    print("2. 根据需要调整格式和深度")
    print("3. 考虑发布到适当平台（博客、GitHub、内部Wiki等）")
    print("4. 收集反馈并更新原始洞察")

if __name__ == "__main__":
    main()
