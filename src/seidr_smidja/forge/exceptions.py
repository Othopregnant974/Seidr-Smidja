"""seidr_smidja.forge.exceptions — Forge-domain exception types."""
from __future__ import annotations


class ForgeBuildError(RuntimeError):
    """Raised only on non-recoverable Forge failure.

    This is NOT raised for Blender subprocess failure (non-zero exit code).
    Blender failure → ForgeResult(success=False).
    This is raised when the invocation itself cannot begin:
        - Blender executable not found
        - Output directory not writable
        - Spec JSON serialization failure

    Attributes:
        message: Human-readable description.
        cause:   The underlying exception if any.
    """

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause
