# Gate — Interface Contract
**Last updated:** 2026-05-06
**Domain:** Gate — the Compliance Gate
**Keeper:** Rúnhild Svartdóttir (Architect)

---

## Purpose

The Gate is the compliance validation layer. Every `.vrm` output passes through it before delivery. The Gate validates against VRChat and VTube Studio requirements, producing a structured `ComplianceReport`. Failures are data, not exceptions — a failing report is a meaningful result, not a crash.

---

## Public Signatures

### `check(vrm_path: Path, targets: list[ComplianceTarget] | None = None) -> ComplianceReport`

Validates the given `.vrm` file against the specified compliance targets.

- **Input:**
  - `vrm_path` — absolute path to the `.vrm` file. Must exist.
  - `targets` — optional list of `ComplianceTarget` values. If `None`, all available targets are checked (`VRCHAT`, `VTUBE_STUDIO`).
- **Output:** `ComplianceReport` dataclass (see below).
- **Errors:**
  - `GateError` — raised only on internal failure: file not found, corrupt VRM that cannot be parsed, or rule file missing. Validation failures (polygon count over budget, missing visemes, etc.) are NOT exceptions — they appear as violations in the `ComplianceReport`.

---

### `list_rules(target: ComplianceTarget) -> list[ComplianceRule]`

Returns the list of compliance rules defined for a given target (for tooling and diagnostics).

- **Input:** `target` — a `ComplianceTarget` enum value.
- **Output:** `list[ComplianceRule]` — each rule carries: `rule_id`, `display_name`, `severity`, `description`.
- **Errors:**
  - `GateError` — if the rule file for the target cannot be read.

---

## Key Data Structures

### `ComplianceTarget` (enum)

```
VRCHAT
VTUBE_STUDIO
```

### `ComplianceReport` (dataclass)

```
vrm_path: Path
targets_checked: list[ComplianceTarget]
passed: bool                          # True only if ALL checked targets pass
results: dict[str, TargetResult]      # keyed by ComplianceTarget.value string
    TargetResult:
        target: ComplianceTarget
        passed: bool
        violations: list[Violation]
            Violation:
                rule_id: str
                severity: ViolationSeverity   # ERROR | WARNING
                field_path: str               # e.g. "mesh.polycount"
                description: str
                actual_value: Any | None
                limit_value: Any | None
elapsed_seconds: float
```

### `GateError` (exception)

```
message: str
cause: Exception | None
```

---

## Invariants

1. A `ComplianceReport` with `passed=False` is never silently converted to a passing result.
2. The Gate can be invoked independently of the full forge pipeline (standalone compliance check).
3. All compliance rules are loaded from YAML data files at runtime — none are hardcoded in Python.
4. The Gate does not call into Forge, Oracle Eye, Loom, Hoard, or any Bridge.

---

## Dependencies

- `seidr_smidja.annall.port` — compliance event logging

---

*Rúnhild Svartdóttir, Architect — 2026-05-06*
