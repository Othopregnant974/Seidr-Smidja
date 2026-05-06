# D-007 — Blender Subprocess Pattern v0.1
**Status:** Accepted
**Date:** 2026-05-06
**Deciders:** Volmarr Wyrd, Runa Gridweaver Freyjasdóttir
**Phase:** Genesis (pre–vertical-slice)

---

## Context

Forge and Oracle Eye both need to invoke Blender headlessly. There are two approaches to structuring these invocations:

**Two subprocess invocations:** Forge launches one `blender --background` process for the build (load base mesh, apply spec, export `.vrm`). Oracle Eye launches a second, separate `blender --background` process for rendering (load the exported `.vrm`, set up cameras, render PNGs). Simpler: each invocation has a clear, single purpose. Safer: a crash in one process does not affect the other.

**Single Blender session:** One Blender process is launched, completes the build (exports `.vrm`), and continues to perform the renders without restarting. Faster: saves the startup overhead of launching a second Blender process (which can take several seconds). More complex: the render script must be designed to work within the same Blender session as the build script; any crash in either phase takes down the whole session.

The Cartographer flagged this as Tension T5 in `DATA_FLOW.md §X`. `ARCHITECTURE.md §VII` noted "second invocation, or same session if feasible" as an open question.

---

## Decision

**Forge and Oracle Eye launch separate Blender subprocesses for v0.1 — one for the build/export, one for rendering.**

A future optimization (single-session) is noted and parked; it is not pursued in v0.1.

---

## Consequences

**Two separate subprocesses makes possible:**
- Clean isolation between build failure and render failure. A Blender crash during rendering does not corrupt or complicate the build output.
- Simpler scripts: `build_script.py` (in `forge/scripts/`) does only mesh transformation and VRM export; `render_script.py` (in `oracle_eye/scripts/`) does only camera setup and Eevee rendering. Neither script needs to handle the combined state.
- The shared runner (`_internal/blender_runner.py`) has a simple, consistent interface: it launches one Blender process for one script with one set of arguments. No session management.
- Testing is cleaner: the Forge can be tested in isolation without the render path executing.

**Two separate subprocesses constrains:**
- Two Blender startup overheads per build cycle. On a typical machine this adds 5–15 seconds per full build (total for both subprocesses). Acceptable for a v0.1 agent tool where build quality matters more than raw throughput.
- The build must complete and produce a `.vrm` file on disk before the render subprocess can start. This is already the design (Oracle Eye receives `vrm_path` from `ForgeResult`).

**Single-session optimization (parked for a future phase):**
- When throughput becomes a priority, a single Blender session could load the base, apply the spec, export the `.vrm`, then set up cameras and render without restarting. This requires a combined script or a Blender operator that sequences both phases.
- This optimization should only be pursued after the two-subprocess v0.1 is proven correct. The Oracle Eye's `render()` interface is already abstract enough to host either approach — callers will not change.

---

## References

- [`docs/ARCHITECTURE.md §VII`](../ARCHITECTURE.md) — Process and Threading Model, showing two subprocess invocations.
- [`docs/DATA_FLOW.md §V`](../DATA_FLOW.md) — Blender Subprocess Shared Runner diagram.
- [`docs/DATA_FLOW.md §X Tension T5`](../DATA_FLOW.md) — original tension statement.
- [`docs/DECISIONS/D-003-shared-blender-runner-location.md`](D-003-shared-blender-runner-location.md) — the shared runner that both invocations use.
- [`src/seidr_smidja/forge/INTERFACE.md`](../../src/seidr_smidja/forge/INTERFACE.md)
- [`src/seidr_smidja/oracle_eye/INTERFACE.md`](../../src/seidr_smidja/oracle_eye/INTERFACE.md)

---

*Recorded by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
