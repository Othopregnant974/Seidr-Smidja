# Gate — the Compliance Gate
**Domain:** `src/seidr_smidja/gate/`
**Layer:** 2 — Domain Core
**Keeper:** Rúnhild Svartdóttir (Architect)

---

> *"A blade that cannot cut has not been made."*

---

## True Name and Meaning

The **Gate** is the threshold between what was forged and what may leave the forge. In Norse tradition, every great hall had a gate-keeper — a figure whose authority was to decide what passed and what did not, regardless of pressure or persuasion. The Gate did not negotiate. It held the standard.

In this system, the Gate holds the VRChat and VTube Studio compliance standards. Every `.vrm` that reaches it must be measured against the rules — polygon budgets, bone structure, viseme coverage, material limits, blendshape requirements, lookat configuration. A `.vrm` that fails any rule does not leave the forge as a success. The Gate's verdict is always expressed as a `ComplianceReport` — a structured account of what passed, what failed, and why — so the agent can understand exactly what must change on the next iteration.

---

## One-Sentence Purpose

The Gate owns all compliance validation logic — VRChat rules and VTube Studio rules — and produces a structured `ComplianceReport` for every `.vrm` it examines, with failures expressed as data rather than exceptions.

---

## What Lives Here

- `INTERFACE.md` — the public contract (read this before touching any code here).
- `check(vrm_path, targets) -> ComplianceReport` — the primary entry point.
- `list_rules(target) -> list[ComplianceRule]` — for tooling and diagnostics.
- Rule-loading logic: reads `data/compliance_rules/vrchat.yaml` and `data/compliance_rules/vtube_studio.yaml` at runtime.
- `ComplianceTarget` enum, `ComplianceReport`, `TargetResult`, `Violation`, `ViolationSeverity` data structures.
- `GateError` exception class (internal failure only — corrupt VRM, missing rule file).

## What Does NOT Live Here

- Avatar transformation or rendering — that is the Forge and Oracle Eye.
- Spec validation — that is the Loom. The Gate evaluates the *built output*, not the input spec.
- Agent protocol handling — that is the Bridges.
- Logging beyond compliance events — that is Annáll's general scope.
- Compliance *rule definitions* — those live in `data/compliance_rules/` as YAML files. The Gate loads them; it does not contain them.

---

## Public Interface Entry Points

The full contract is defined in [`INTERFACE.md`](INTERFACE.md). Key signatures:

- `check(vrm_path: Path, targets: list[ComplianceTarget] | None = None) -> ComplianceReport`
- `list_rules(target: ComplianceTarget) -> list[ComplianceRule]`

Errors: `GateError` (internal failure only — corrupt VRM, unreadable rule file). Compliance failures appear as `ComplianceReport` data, never as exceptions.

---

## Dependency Direction

**The Gate depends on Annáll for event logging only. It receives only a `vrm_path` — it does not call into any other domain.**

```
[Bridge Core] --> [Gate] --> (logs to) [Annáll]
```

The Gate must never import from: Forge, Oracle Eye, Loom, Hoard, or Bridges. It is fully standalone and can be invoked independently of the full forge pipeline (standalone compliance check via the Rúnstafr CLI: `seidr check <file.vrm>`).

---

## Critical Invariants

1. A `ComplianceReport` with `passed=False` is **never silently converted to a passing result.** No error suppression. No tolerance mode that silently ignores errors.
2. All compliance rules are loaded from YAML files at runtime. **None are hardcoded in Python.** To add or modify a rule, edit `data/compliance_rules/` — not the Gate's Python source.
3. The Gate returns structured `Violation` objects with `rule_id`, `severity`, `field_path`, `actual_value`, and `limit_value`. Agents receive everything they need to understand what failed and why, enabling the feedback loop.

---

## Cross-References

- **Philosophy relevance:** [docs/PHILOSOPHY.md §II Principle 4](../../../docs/PHILOSOPHY.md) — "The Blade Must Pass the Gate." Compliance validators are not optional downstream steps; they are part of the forging itself.
- **Data flow relevance:** [docs/DATA_FLOW.md §I Step 7](../../../docs/DATA_FLOW.md) — the Gate step. Failure D (compliance rejection) is diagrammed in `DATA_FLOW.md §VIII`.
- **Architecture relevance:** [docs/ARCHITECTURE.md §X](../../../docs/ARCHITECTURE.md) — the error handling philosophy. "Fail loud at the Gate."
- **Domain Map:** [docs/DOMAIN_MAP.md — Gate](../../../docs/DOMAIN_MAP.md)

---

*Written by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
