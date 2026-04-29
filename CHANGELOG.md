# Changelog

## v0.4.0 - Pending Release

Release type: core skeleton formalization.

This release prepares `cognition-engine` for a v0.4.0 public-facing release decision. It aligns the package metadata, public entry documentation, release drafts, and build verification surface around the Google ADK-based cognition engine skeleton.

### Added

- ADK-aligned skeleton modules for artifacts, invocation, events, runtime, sessions, workflows, and control-plane records.
- Control-plane records covering Context Record, Run Record, Event Trace, Artifact Manifest, and Control Plane Bundle.
- Release draft materials under `docs/项目/认知引擎 v0.4.0 版本建设项目/release/`.

### Changed

- Public README, English README, and quickstart now use the v0.4.0 release-preparation positioning.
- Package metadata target is `0.4.0`.
- `uv` is the preferred dependency, test, and build path in public instructions.

### Verification

- Focused unit tests: pending execution in task 035 result evidence.
- Build dry-run: pending execution in task 035 result evidence.
- GitHub Release: pending final release decision.
- Git tag: pending final release decision.
- PyPI: pending final release decision.

Release note draft:

```text
docs/项目/认知引擎 v0.4.0 版本建设项目/release/001-v0.4.0-release-note草稿-v1.zh-CN.md
```

## Earlier Versions

Earlier repository history contains private project iterations and public-surface repairs. The v0.4.0 entry is the current public-release preparation baseline.
