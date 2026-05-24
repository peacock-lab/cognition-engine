# cognition-system-evaluation

Evaluation contracts and helpers for the Cognition System.

This package evaluates answer quality, output constraints, product-facing
evidence-answer behavior, architecture boundaries, contract boundaries and
configuration boundaries. It does not make final governance decisions.

Current evaluation profiles:

- `evaluation-profile://evidence-summary-answer/requested-output-v1`
- `evaluation-profile://architecture-boundary/v1`
- `evaluation-profile://contract-boundary/v1`
- `evaluation-profile://configuration-boundary/v1`

Boundary:

- runtime runs
- observability records
- evaluation evaluates
- governance decides
- product_gateway exposes product entry summaries

Architecture / contract / configuration evaluation is a deterministic
development guardrail. It produces findings, warnings and summaries only. It
does not open ADK evaluation runtime, Task API runtime, Workflow Runtime,
Session, Event, Artifact, Memory, Tools, Skills, callbacks or plugins.
