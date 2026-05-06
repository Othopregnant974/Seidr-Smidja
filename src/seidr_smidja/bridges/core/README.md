# Bridge Core — the Shared Anvil
**Domain:** `src/seidr_smidja/bridges/core/`
**Layer:** 3 — Orchestration Layer
**Keeper:** Rúnhild Svartdóttir (Architect)

---

> *"Every hammer strikes the same surface. The Anvil does not move."*

---

## True Name and Meaning

The **Shared Anvil** is named for the anvil itself — the one immovable surface in the forge against which all hammers strike, regardless of which smith is swinging. Mjöll, Rúnstafr, Straumur, the Skills: each is a different smith's hammer. But they all strike the same surface. They all call the same `dispatch()`. They all receive the same `BuildResponse`.

Without the Shared Anvil, the four Bridges would silently diverge. Each would accumulate its own interpretation of what a build request means, its own step ordering, its own error shapes. Within weeks they would be four different forges wearing the same name. The Shared Anvil prevents that drift by being the single place where the pipeline is defined, executed, and controlled.

---

## One-Sentence Purpose

The Shared Anvil owns the single canonical orchestration path: receiving a normalized `BuildRequest`, executing the fixed pipeline (Loom → Hoard → Forge → Oracle Eye → Gate), and assembling a `BuildResponse` — all without any awareness of which Bridge called it.

---

## What Lives Here

- `INTERFACE.md` — the public contract (read this before touching any code here).
- `dispatch(request: BuildRequest, annall: AnnallPort) -> BuildResponse` — the only function any Bridge may call to enter the forge.
- `BuildRequest` dataclass definition.
- `BuildResponse` dataclass definition.
- `BuildError` dataclass definition.
- The pipeline logic that calls, in fixed order: Loom → Hoard → Forge → Oracle Eye → Gate.
- Error assembly: every domain exception is caught, turned into a `BuildError`, and placed in `BuildResponse.errors`.

## What Does NOT Live Here

- Protocol-specific logic — no MCP framing, no CLI argument parsing, no HTTP routing. That belongs entirely within each Bridge sub-module.
- Forge domain logic — the Core calls `forge.build()`, it does not contain build logic.
- Any awareness of which Bridge sub-module is calling. `dispatch()` is stateless with respect to the caller's identity.

---

## Public Interface Entry Points

The full contract is defined in [`INTERFACE.md`](INTERFACE.md). The single entry point:

- `dispatch(request: BuildRequest, annall: AnnallPort) -> BuildResponse`

The `AnnallPort` instance is passed as a parameter — never imported as a global. See [D-005](../../../docs/DECISIONS/D-005-annall-port-injection-pattern.md).

---

## Pipeline Contract

The pipeline executes in this exact, fixed, non-skippable order:

```
Step 1: Loom.load_and_validate(request.spec_source)
Step 2: Hoard.resolve(request.base_asset_id)
Step 3: Forge.build(spec, base_path, request.output_dir)
Step 4: OracleEye.render(forge_result.vrm_path, request.output_dir, request.render_views)
Step 5: Gate.check(forge_result.vrm_path, request.compliance_targets)
```

Steps may not be reordered. Steps 4 and 5 may still execute even if a prior step failed partially — if there is a `.vrm` to work with, the Oracle Eye renders and the Gate checks, even if the build itself returned a warning. A Bridge cannot bypass the Oracle Eye by omitting `render_views` — it must pass `render_views=[]` to request an empty render set (and even then, the call is made).

---

## Dependency Direction

**The Core sits at Layer 3 and calls into all Layer 2 domains.** It also calls Annáll (Layer 1).

```
[Bridge sub-module] --> [bridges.core.dispatch()] --> [Loom]
                                                  --> [Hoard]
                                                  --> [Forge]
                                                  --> [Oracle Eye]
                                                  --> [Gate]
                                                  --> (logs to) [Annáll]
```

The Core has zero awareness of which Bridge called it. It never imports from any Bridge sub-module.

---

## Cross-References

- **Philosophy relevance:** [docs/PHILOSOPHY.md §II Principle 5](../../../docs/PHILOSOPHY.md) — "Refinement Extends, Never Erases." The Core ensures every iteration of the feedback loop is a complete, independent forge cycle — it does not modify state across calls.
- **Data flow relevance:** [docs/DATA_FLOW.md §I Steps 2 and 8](../../../docs/DATA_FLOW.md) — session opening and response assembly. [DATA_FLOW.md §II](../../../docs/DATA_FLOW.md) — full sequence diagram showing the Core's role.
- **Architecture relevance:** [docs/ARCHITECTURE.md §II](../../../docs/ARCHITECTURE.md) — the Shared Anvil pattern, `BuildRequest`/`BuildResponse` model definitions, the pipeline pseudocode.
- **Decision:** [D-005](../../../docs/DECISIONS/D-005-annall-port-injection-pattern.md)
- **Domain Map:** [docs/DOMAIN_MAP.md — Bridge Core](../../../docs/DOMAIN_MAP.md)

---

*Written by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
