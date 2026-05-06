"""seidr_smidja.loom.exceptions — Loom-domain exception types."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationFailure:
    """Detail record for a single Loom validation failure.

    Attributes:
        field_path:     Dot-separated path to the failing field (e.g. 'body.height_scale').
        reason:         Human-readable explanation of why validation failed.
        received_value: The value that was provided (may be None if field is missing).
    """

    field_path: str
    reason: str
    received_value: Any = None


class LoomValidationError(ValueError):
    """Raised when AvatarSpec validation fails.

    Invariant: A LoomValidationError always includes at least one ValidationFailure.
    A partial AvatarSpec is NEVER returned — either the spec is fully valid or this
    exception is raised.

    Attributes:
        failures: List of individual field failures.
    """

    def __init__(self, message: str, failures: list[ValidationFailure]) -> None:
        super().__init__(message)
        self.failures = failures

    def __str__(self) -> str:
        details = "\n".join(
            f"  - {f.field_path}: {f.reason} (got: {f.received_value!r})"
            for f in self.failures
        )
        return f"{super().__str__()}\n{details}"


class LoomIOError(OSError):
    """Raised when a spec file cannot be read or written.

    This is distinct from LoomValidationError: IO errors are environmental
    (missing file, permissions) while validation errors are spec content errors.
    """
