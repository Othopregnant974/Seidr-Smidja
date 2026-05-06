# D-005 — AnnallPort Injection Pattern
**Status:** Accepted
**Date:** 2026-05-06
**Deciders:** Volmarr Wyrd, Runa Gridweaver Freyjasdóttir
**Phase:** Genesis (pre–vertical-slice)

---

## Context

Every domain in the forge — Loom, Hoard, Forge, Oracle Eye, Gate — logs events to Annáll. There are two ways to make the `AnnallPort` instance reachable:

**Option A — Module-level singleton:** The `AnnallPort` instance is imported as a global from a central location. Every domain calls `from seidr_smidja import annall_instance` and logs events directly. Simple, requires no parameter threading.

**Option B — Dependency injection:** The `AnnallPort` instance is constructed once at process startup and passed as a parameter wherever it is needed. `dispatch(request, annall)` receives it explicitly. Domain functions accept `annall: AnnallPort | None = None` in their public signatures.

The Cartographer flagged this as Tension T3 in `DATA_FLOW.md §X`, noting that the INTERFACE.md files for all domains show the domain calling `annall.log_event()` directly — implying Option B.

---

## Decision

**The AnnallPort instance is constructed at process startup from configuration, passed to `bridges.core.dispatch(request, annall)`, and then explicitly threaded as a parameter (or constructor argument for adapter-shaped domains) into every domain function that needs telemetry.**

**Domain functions accept `annall: AnnallPort | None = None`.** When `annall` is `None`, logging is disabled. This keeps unit tests free of database setup — a test that does not care about logging simply passes `annall=None` and the domain function behaves normally without writing any records.

**No global state. No module-level singleton.**

---

## Consequences

**Option B (injection) makes possible:**
- Unit tests for Loom, Hoard, Forge, Oracle Eye, and Gate run without any database setup or Annáll infrastructure. Pass `annall=None` and test the domain logic in isolation.
- Multiple concurrent build pipelines (future) can use different `AnnallPort` instances (or the same one — SQLite with WAL handles concurrent writes) without shared mutable state.
- Swapping the Annáll adapter (SQLite → Postgres → flat-file) requires changing only the startup code, not any domain function.
- Clarity: every domain function that logs events declares this in its signature. There is no hidden ambient dependency.

**Option B constrains:**
- Every domain's public call signature must include `annall: AnnallPort | None = None`. This is a minor but real overhead in function signatures.
- The Forge Worker must thread the parameter consistently through `dispatch()` — it must not be forgotten at any call site.

**What Option A would have caused:**
- Module-level global state makes the logging dependency implicit and invisible in function signatures.
- Unit tests would need either a real SQLite database or a mock of the global singleton, adding setup overhead.
- Testing domains in isolation becomes harder as the system grows.

**What must be confirmed by the Forge Worker:**
- The precise threading pattern: does each domain call receive `annall` directly as a parameter, or does the Core log on domains' behalf (calling `annall.log_event()` at each step boundary)? The INTERFACE.md files show domains calling `annall.log_event()` directly, suggesting each domain receives the port. This pattern should be confirmed and implemented consistently across all five domains.

---

## References

- [`docs/DATA_FLOW.md §VI`](../DATA_FLOW.md) — AnnallPort wiring path diagram.
- [`docs/DATA_FLOW.md §X Tension T3`](../DATA_FLOW.md) — original tension statement.
- [`docs/ARCHITECTURE.md §III`](../ARCHITECTURE.md) — Port-and-Adapter pattern for Annáll.
- [`src/seidr_smidja/bridges/core/INTERFACE.md`](../../src/seidr_smidja/bridges/core/INTERFACE.md) — `dispatch(request, annall)` signature.
- [`src/seidr_smidja/annall/INTERFACE.md`](../../src/seidr_smidja/annall/INTERFACE.md) — Invariant 4: adapter injected at startup, never imported as a module-level global.

---

*Recorded by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
