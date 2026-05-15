"""Product gateway contracts for Cognition System product entry boundaries."""

from product_gateway.cognition_run import (
    CognitionRunCompatibilityProjection,
    CognitionRunGatewayInput,
    build_cognition_run_compatibility_projection,
    build_cognition_run_gateway_request,
    run_cognition_run_gateway_request,
)
from product_gateway.controlled_live import (
    ControlledLiveCompatibilityProjection,
    ControlledLiveGatewayInput,
    build_controlled_live_compatibility_projection,
    build_controlled_live_gateway_request,
    run_controlled_live_gateway_request,
)
from product_gateway.agent_shell import (
    AgentShellCompatibilityProjection,
    AgentShellGatewayInput,
    build_agent_shell_compatibility_projection,
    build_agent_shell_gateway_request,
    run_agent_shell_gateway_request,
)
from product_gateway.tool_smoke import (
    ToolSmokeCompatibilityProjection,
    ToolSmokeGatewayInput,
    build_tool_smoke_compatibility_projection,
    build_tool_smoke_gateway_request,
    run_tool_smoke_gateway_request,
)
from product_gateway.memory_projection import (
    ProductGatewayMemoryDeletionRequestCandidate,
    ProductGatewayMemoryProjectionViewCandidate,
    ProductGatewayMemoryTombstoneViewCandidate,
    build_product_gateway_memory_deletion_request,
    build_product_gateway_memory_projection_view,
    build_product_gateway_memory_tombstone_view,
)
from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayInputRefs,
    ProductGatewayLiveOptions,
    ProductGatewayOperatorApprovalRef,
    ProductGatewayOutputRefs,
    ProductGatewayRef,
    ProductGatewayRequest,
    ProductGatewayResponse,
    ProductGatewayStatus,
)

__all__ = [
    "CognitionRunCompatibilityProjection",
    "CognitionRunGatewayInput",
    "AgentShellCompatibilityProjection",
    "AgentShellGatewayInput",
    "ControlledLiveCompatibilityProjection",
    "ControlledLiveGatewayInput",
    "ProductGatewayEntryKind",
    "ProductGatewayExecutionMode",
    "ProductGatewayInputRefs",
    "ProductGatewayLiveOptions",
    "ProductGatewayMemoryDeletionRequestCandidate",
    "ProductGatewayMemoryProjectionViewCandidate",
    "ProductGatewayMemoryTombstoneViewCandidate",
    "ProductGatewayOperatorApprovalRef",
    "ProductGatewayOutputRefs",
    "ProductGatewayRef",
    "ProductGatewayRequest",
    "ProductGatewayResponse",
    "ProductGatewayStatus",
    "ToolSmokeCompatibilityProjection",
    "ToolSmokeGatewayInput",
    "build_agent_shell_compatibility_projection",
    "build_agent_shell_gateway_request",
    "build_cognition_run_compatibility_projection",
    "build_cognition_run_gateway_request",
    "build_controlled_live_compatibility_projection",
    "build_controlled_live_gateway_request",
    "build_product_gateway_memory_deletion_request",
    "build_product_gateway_memory_projection_view",
    "build_product_gateway_memory_tombstone_view",
    "build_tool_smoke_compatibility_projection",
    "build_tool_smoke_gateway_request",
    "run_agent_shell_gateway_request",
    "run_cognition_run_gateway_request",
    "run_controlled_live_gateway_request",
    "run_tool_smoke_gateway_request",
]
