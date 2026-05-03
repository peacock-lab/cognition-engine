"""Internal observability-hub errors."""


class ObservabilityHubError(Exception):
    """Base error for observability-hub failures."""


class ObservabilityHubInputError(ObservabilityHubError):
    """Raised when the intake input is not RuntimeResult-compatible."""
