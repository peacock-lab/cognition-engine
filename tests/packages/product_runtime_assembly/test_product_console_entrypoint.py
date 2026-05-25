from __future__ import annotations

import json

from product_runtime_assembly.entrypoints import cognition_console


def test_cognition_console_entrypoint_delegates_to_product_console(capsys) -> None:
    exit_code = cognition_console.main(["--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["command"] == "cognition-console"
    assert payload["product_console"] is True
    assert payload["display"]["runtime_backed"] is False
    assert payload["display"]["products"][0]["product_id"] == (
        "reviewable-evidence-answer-pack"
    )
