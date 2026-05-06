# D-003 — Shared Blender Runner Location
**Status:** Accepted
**Date:** 2026-05-06
**Deciders:** Volmarr Wyrd, Runa Gridweaver Freyjasdóttir
**Phase:** Genesis (pre–vertical-slice)

---

## Context

Both the Forge and the Oracle Eye launch Blender headlessly as subprocesses. The mechanics of launching a Blender subprocess — resolving the executable path, constructing the argument list, capturing stdout/stderr, checking the exit code, handling timeout — are identical in both domains. They differ only in which Python script is injected into the subprocess.

Without a shared runner, this launch mechanic would be duplicated across `forge/` and `oracle_eye/`. Duplication of infrastructure code creates two points of failure: if the executable resolver has a bug, it must be fixed in two places. More subtly, the two implementations might silently diverge over time — one handling timeouts differently, one logging arguments while the other does not.

The Architect identified this tension and proposed two candidate locations:

**Option A:** `forge/runner.py` — the runner lives inside the Forge domain. Oracle Eye imports from Forge to use it.

**Option B:** `src/seidr_smidja/_internal/blender_runner.py` — the runner lives in an infrastructure layer (`_internal/`), below both Forge and Oracle Eye. Both import from `_internal`.

The Cartographer flagged this as Tension T1 in `DATA_FLOW.md §X`.

---

## Decision

**The shared low-level Blender subprocess runner lives at `src/seidr_smidja/_internal/blender_runner.py`.**

Both Forge and Oracle Eye import from `_internal.blender_runner`. Neither domain owns the runner.

This is consistent with `ARCHITECTURE.md §I` Layer 1 (Adapter / Infrastructure Layer), which already lists "Config loader · Blender subprocess runner" as Layer 1 concerns alongside Annáll.

---

## Consequences

**`_internal/blender_runner.py` makes possible:**
- Single point of maintenance for executable resolution, subprocess launch mechanics, timeout handling, and stdout/stderr capture.
- Forge and Oracle Eye remain cleanly separated — neither imports from the other.
- Future domains (if any) that need to launch Blender can use the same runner without reaching into Forge or Oracle Eye.

**`_internal/blender_runner.py` constrains:**
- The `_internal` directory is implicitly a "do not import from outside the package" namespace (Python convention for leading-underscore modules). External consumers of the package cannot rely on its API. This is intentional — the runner is a private infrastructure concern.
- The Forge Worker must create the `_internal/` directory as part of Phase 5 and ensure its `__init__.py` does not inadvertently export runner internals.

**What must be revisited later:**
- If the runner grows substantially (supporting multiple renderer types beyond Blender), it may deserve promotion to a named module rather than `_internal/`. The Architect should evaluate this when the Oracle Eye's rich render pipeline (three-vrm) is implemented.

**What Option A would have caused:**
- Oracle Eye importing from Forge would violate the spirit of the Dependency Law — not the letter (Oracle Eye → Forge is permitted), but the principle that domains should only depend on domains they actually orchestrate. Oracle Eye does not orchestrate Forge; they are peers that share infrastructure.

---

## References

- [`docs/ARCHITECTURE.md §I`](../ARCHITECTURE.md) — Layer 1 Infrastructure Layer placement.
- [`docs/DATA_FLOW.md §V`](../DATA_FLOW.md) — Blender Subprocess Shared Runner diagram (draws `_internal/blender_runner.py`).
- [`docs/DATA_FLOW.md §X Tension T1`](../DATA_FLOW.md) — original tension statement.
- [`src/seidr_smidja/forge/INTERFACE.md`](../../src/seidr_smidja/forge/INTERFACE.md) — Forge does not own the runner.
- [`src/seidr_smidja/oracle_eye/INTERFACE.md`](../../src/seidr_smidja/oracle_eye/INTERFACE.md) — Oracle Eye similarly does not own the runner.

---

*Recorded by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
