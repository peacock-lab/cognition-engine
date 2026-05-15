"""CLI adapters for product gateway entries."""

from product_gateway.cli.cognition_run import run_cognition_run_cli
from product_gateway.cli.presenter import (
    product_gateway_response_to_json_text,
    product_gateway_response_to_text,
)

__all__ = [
    "product_gateway_response_to_json_text",
    "product_gateway_response_to_text",
    "run_cognition_run_cli",
]
