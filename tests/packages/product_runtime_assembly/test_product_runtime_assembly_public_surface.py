from __future__ import annotations


def test_product_runtime_assembly_root_public_surface_is_minimal() -> None:
    import product_runtime_assembly

    assert product_runtime_assembly.__all__ == (
        "PRODUCT_RUNTIME_ASSEMBLY_PACKAGE",
        "PRODUCT_RUNTIME_ASSEMBLY_STATUS",
    )
    assert (
        product_runtime_assembly.PRODUCT_RUNTIME_ASSEMBLY_PACKAGE
        == "product_runtime_assembly"
    )
    assert product_runtime_assembly.PRODUCT_RUNTIME_ASSEMBLY_STATUS == "skeleton"


def test_product_runtime_assembly_root_does_not_export_future_entrypoints() -> None:
    import product_runtime_assembly

    future_names = (
        "execute_cognition_run",
        "execute_cognition_run_with_default_runtime",
        "run_controlled_live_with_default_runtime",
        "execute_cli_twf_workflow",
        "build_default_llm_invocation_service_factory",
        "build_twf_default_llm_invocation_service_factory",
        "build_external_readonly_answer_default_llm_invocation_service_factory",
        "run_controlled_execution_service",
        "build_runtime_container_llm_invocation_service_factory",
        "main",
    )

    for name in future_names:
        assert name not in product_runtime_assembly.__all__
        assert not hasattr(product_runtime_assembly, name)
