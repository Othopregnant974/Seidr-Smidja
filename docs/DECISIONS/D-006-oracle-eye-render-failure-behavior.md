# D-006 — Oracle Eye Render-Failure Behavior
**Status:** Accepted
**Date:** 2026-05-06
**Deciders:** Volmarr Wyrd, Runa Gridweaver Freyjasdóttir
**Phase:** Genesis (pre–vertical-slice)

---

## Context

The Oracle Eye renders preview PNGs after the Forge completes. But rendering can fail for reasons unrelated to the avatar's validity: Blender hung, the render script had a bug, GPU drivers are missing, the headless render environment lacks display support. In such cases, the `.vrm` file itself may be perfectly valid and compliance-ready.

The question is: if rendering fails but the `.vrm` was successfully produced and passes the Gate, what does `dispatch()` return?

**Option A — Hard failure:** If rendering fails, the build is considered failed. The `.vrm` is withheld. `BuildResponse.success = False`, `vrm_path = None`. The agent receives no deliverable.

**Option B — Soft failure:** If rendering fails, the `.vrm` is still returned. `BuildResponse.success = False` (the build is incomplete), but `vrm_path` is populated. `render_paths` is empty or partial. A structured warning records which renders failed and why.

The Cartographer flagged this as Tension T4 in `DATA_FLOW.md §X`, noting that the Data Flow document assumed Option B but explicitly asked the Forge Worker to confirm.

---

## Decision

**Render failure is a soft failure.** If the `.vrm` was successfully produced and validated by the Gate, but rendering fails, the build returns:
- `BuildResponse.success = False` (the build is not fully successful — renders are missing)
- `BuildResponse.vrm_path` = the path to the produced `.vrm`
- `BuildResponse.render_paths` = empty or partial (whichever renders succeeded, if any)
- `BuildResponse.compliance_report` = the Gate result (Gate is still called when `.vrm` is present)
- `BuildResponse.errors` = a `BuildError(stage="oracle_eye", ...)` with structured detail about why rendering failed

**Aligns with:** PHILOSOPHY.md's "fail loud at the Gate, fail soft inside the Forge." The Gate is the quality gate for avatar correctness. Rendering is a feedback convenience — its failure should not prevent delivery of a valid `.vrm` that the agent may still want to use, inspect, or debug.

---

## Consequences

**Soft failure makes possible:**
- The feedback loop continues even when the render environment is degraded. An agent receiving a compliant `.vrm` without renders can still use it (import into VRChat manually, for example) and investigate the render failure separately.
- The agent receives enough information to understand what failed: the compliance report confirms the avatar quality; the render error detail explains why images are missing.
- CI environments without GPU access can validate the full Forge + Gate pipeline; render failures are expected and non-blocking for compliance testing.

**Soft failure constrains:**
- `BuildResponse.success = False` whenever renders are missing, even when the `.vrm` is valid. Callers must inspect `BuildResponse.errors` to distinguish "Forge failed" from "renders failed" from "compliance failed."
- The agent cannot assume that `success = True` implies renders exist. It must check `render_paths` independently. The INTERFACE must document this clearly.

**What Hard Failure (Option A) would have caused:**
- An agent attempting to use the forge in an environment without GPU support would receive no `.vrm` at all, even if the avatar is perfectly valid. This would break the feedback loop entirely in degraded render environments.
- The forge's utility would be unnecessarily fragile — a render infrastructure problem would make the forge appear entirely broken.

---

## References

- [`docs/DATA_FLOW.md §VIII Failure C`](../DATA_FLOW.md) — Oracle Eye subprocess failure path.
- [`docs/DATA_FLOW.md §X Tension T4`](../DATA_FLOW.md) — original tension statement.
- [`docs/PHILOSOPHY.md §X Error Handling`](../PHILOSOPHY.md) — "fail loud at the Gate, fail soft inside the Forge."
- [`docs/ARCHITECTURE.md §X Error Handling Philosophy`](../ARCHITECTURE.md) — Oracle Eye row in the error handling table.
- [`src/seidr_smidja/oracle_eye/INTERFACE.md`](../../src/seidr_smidja/oracle_eye/INTERFACE.md)
- [`src/seidr_smidja/bridges/core/INTERFACE.md`](../../src/seidr_smidja/bridges/core/INTERFACE.md) — `BuildResponse` and `BuildError` definitions.

---

*Recorded by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
