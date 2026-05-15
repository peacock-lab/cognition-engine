"""Product gateway response summary contract facade.

This module only re-exports public summary schemas and behavior guards. It does
not import product, agent, governance, runtime, config, or provider packages.
"""

from behavior_contracts.product_gateway_response_summary import (
    DEFAULT_PRODUCT_GATEWAY_RESPONSE_SUMMARY_GUARDS,
    ProductGatewayResponseBlockedRequiresReasonGuard,
    ProductGatewayResponseNoExecutionGuard,
    ProductGatewayResponseNoRawPayloadGuard,
    ProductGatewayResponseNoRuntimeObjectLeakageGuard,
    ProductGatewayResponseRefsOnlyGuard,
    ProductGatewayResponseSummaryHeaderGuard,
    ProductGatewayResponseSummaryOnlyGuard,
    validate_product_gateway_response_summary_guards,
)
from schemas.product_gateway_response_summary import (
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_ENTRY_KINDS,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_PAYLOAD_TYPE,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_PRODUCT,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_STATUSES,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION,
    ProductGatewayResponseSummaryEntryKind,
    ProductGatewayResponseSummaryRefSchema,
    ProductGatewayResponseSummarySchema,
    ProductGatewayResponseSummaryStatus,
    validate_product_gateway_response_summary,
)

__all__ = [
    "DEFAULT_PRODUCT_GATEWAY_RESPONSE_SUMMARY_GUARDS",
    "PRODUCT_GATEWAY_RESPONSE_SUMMARY_ENTRY_KINDS",
    "PRODUCT_GATEWAY_RESPONSE_SUMMARY_PAYLOAD_TYPE",
    "PRODUCT_GATEWAY_RESPONSE_SUMMARY_PRODUCT",
    "PRODUCT_GATEWAY_RESPONSE_SUMMARY_STATUSES",
    "PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION",
    "ProductGatewayResponseBlockedRequiresReasonGuard",
    "ProductGatewayResponseNoExecutionGuard",
    "ProductGatewayResponseNoRawPayloadGuard",
    "ProductGatewayResponseNoRuntimeObjectLeakageGuard",
    "ProductGatewayResponseRefsOnlyGuard",
    "ProductGatewayResponseSummaryEntryKind",
    "ProductGatewayResponseSummaryHeaderGuard",
    "ProductGatewayResponseSummaryOnlyGuard",
    "ProductGatewayResponseSummaryRefSchema",
    "ProductGatewayResponseSummarySchema",
    "ProductGatewayResponseSummaryStatus",
    "validate_product_gateway_response_summary",
    "validate_product_gateway_response_summary_guards",
]
