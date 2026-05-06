"""seidr_smidja.gate.models — Gate compliance data structures.

All compliance results are structured data, not exceptions.
A failing ComplianceReport is a meaningful result — not a crash.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ComplianceTarget(str, Enum):
    """Named compliance validation targets."""

    VRCHAT = "VRCHAT"
    VTUBE_STUDIO = "VTUBE_STUDIO"


class ViolationSeverity(str, Enum):
    """Severity level for a compliance violation."""

    ERROR = "ERROR"      # Hard failure — avatar is not compliant
    WARNING = "WARNING"  # Advisory — avatar may still work but has issues


@dataclass
class Violation:
    """A single compliance rule violation.

    Attributes:
        rule_id:       Unique identifier for the rule (e.g., 'vrchat.polycount').
        severity:      ERROR or WARNING.
        field_path:    Dot-path to the field that failed (e.g., 'mesh.polycount').
        description:   Human-readable explanation of the violation.
        actual_value:  The value that was found in the VRM.
        limit_value:   The limit that was exceeded or not met.
    """

    rule_id: str
    severity: ViolationSeverity
    field_path: str
    description: str
    actual_value: Any = None
    limit_value: Any = None


@dataclass
class TargetResult:
    """Compliance result for a single target (VRChat or VTube Studio).

    Attributes:
        target:     The target that was checked.
        passed:     True only if there are no ERROR-severity violations.
        violations: All violations found (both ERROR and WARNING).
    """

    target: ComplianceTarget
    passed: bool
    violations: list[Violation] = field(default_factory=list)

    @property
    def errors(self) -> list[Violation]:
        """Return only ERROR-severity violations."""
        return [v for v in self.violations if v.severity == ViolationSeverity.ERROR]

    @property
    def warnings(self) -> list[Violation]:
        """Return only WARNING-severity violations."""
        return [v for v in self.violations if v.severity == ViolationSeverity.WARNING]


@dataclass
class ComplianceReport:
    """Full compliance report for a VRM file.

    Invariant: passed=True only if ALL checked targets pass.
    A non-passing report is never silently converted to a pass.

    Attributes:
        vrm_path:         The VRM file that was checked.
        targets_checked:  Which targets were evaluated.
        passed:           Overall pass verdict (AND of all target results).
        results:          Per-target results keyed by target value string.
        elapsed_seconds:  Time taken to run the compliance check.
    """

    vrm_path: Path
    targets_checked: list[ComplianceTarget]
    passed: bool
    results: dict[str, TargetResult]  # key = ComplianceTarget.value
    elapsed_seconds: float = 0.0

    def violations_for(self, target: ComplianceTarget) -> list[Violation]:
        """Return violations for a specific target (empty list if target not checked)."""
        result = self.results.get(target.value)
        return result.violations if result else []

    def all_violations(self) -> list[Violation]:
        """Return all violations across all targets."""
        all_v: list[Violation] = []
        for result in self.results.values():
            all_v.extend(result.violations)
        return all_v


class ComplianceRule:
    """A single compliance rule definition loaded from YAML."""

    def __init__(
        self,
        rule_id: str,
        display_name: str,
        severity: str,
        description: str,
        **kwargs: Any,
    ) -> None:
        self.rule_id = rule_id
        self.display_name = display_name
        self.severity = ViolationSeverity(severity.upper())
        self.description = description
        self.extra = kwargs  # All additional YAML fields (required_bones, thresholds, etc.)


class GateError(RuntimeError):
    """Raised on internal Gate failures (corrupt VRM, missing rule file, I/O error).

    NOT raised for compliance failures — those appear as a ComplianceReport with
    passed=False. GateError is reserved for infrastructure failures.
    """

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause
