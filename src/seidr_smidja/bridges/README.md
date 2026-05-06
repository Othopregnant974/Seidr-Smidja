# Bridges — the Bifröst Bridges
**Domain:** `src/seidr_smidja/bridges/`
**Layer:** 4 — Bridge Layer
**Keeper:** Rúnhild Svartdóttir (Architect)

---

> *"Many doors, one forge."*

---

## True Name and Meaning

The **Bridges** take their name from Bifröst — the shimmering rainbow bridge of Norse cosmology that connects the nine worlds. Bifröst is not a single path but a passage: any being who approaches the forge does so through its own kind of door, speaking its own dialect, carrying its own way of framing a request. The Bridges translate those dialects into the forge's native tongue.

In this system, the Bridges layer is the collection of thin protocol-translation shims that allow any agent to enter the forge through its preferred door. Mjöll speaks MCP. Rúnstafr speaks shell commands. Straumur speaks HTTP. The Skill Bridges speak Hermes, OpenClaw, and Claude Code's native invocation formats. Every Bridge translates its incoming request into a normalized `BuildRequest` and calls `bridges.core.dispatch()`. Every Bridge translates the `BuildResponse` back into its protocol's native output.

None of the Bridges contain forge logic. A Bridge that holds forge logic has fallen into the fire.

---

## One-Sentence Purpose

The Bridges layer owns all agent-facing protocol translation — receiving a build request in whatever form it arrives, constructing a normalized `BuildRequest`, calling the Shared Anvil (`bridges.core.dispatch()`), and translating the `BuildResponse` back into the protocol's native form.

---

## Sub-Modules

This folder contains four Bridge sub-modules and one Bridge Core:

| Sub-Module | True Name | Protocol | Entry Point |
|---|---|---|---|
| `bridges/core/` | Shared Anvil | (internal orchestration) | `dispatch(request, annall)` |
| `bridges/mjoll/` | Mjöll | MCP | `seidr_build` MCP tool |
| `bridges/runstafr/` | Rúnstafr | CLI | `seidr` console script |
| `bridges/straumur/` | Straumur | REST/HTTP | FastAPI `app` |
| `bridges/skills/` | Skill Bridges | Hermes / OpenClaw / Claude Code | YAML manifests + adapters |

Each sub-module has its own `README.md` (forthcoming — Forge Worker will write these when implementing the slice).

---

## What Lives Here (Top Level)

- `INTERFACE.md` — the public contract for all four entry points (read this before touching any code here).
- `__init__.py` — package root.
- Sub-module directories for each Bridge.

## What Does NOT Live Here

- Any forge logic whatsoever. No Blender invocation, no VRM parsing, no compliance logic, no spec schema validation (except as a pre-flight before calling `dispatch()`). A Bridge that contains forge logic is a structural failure.
- Cross-Bridge shared logic — that belongs in `bridges/core/` (the Shared Anvil), not scattered across sub-modules.

---

## Public Interface Entry Points

The full contract for all four Bridges is in [`INTERFACE.md`](INTERFACE.md). The Shared Anvil contract is in [`core/INTERFACE.md`](core/INTERFACE.md).

**The one call that matters:**
```python
from seidr_smidja.bridges.core import dispatch
response = dispatch(request, annall)
```

Every Bridge sub-module calls this and only this to enter the forge. No Bridge calls Loom, Hoard, Forge, Oracle Eye, Gate, or Annáll directly (except Loom for pre-flight spec validation if needed before constructing a `BuildRequest`).

---

## Dependency Direction

The Bridges sit at **Layer 4** — the outermost layer. They call inward into Layer 3 (Bridge Core) and may also call Loom for spec pre-validation. They log to Annáll.

```
[Agent] --> [Bridge sub-module] --> [bridges.core.dispatch()] --> [Layer 2 domains]
            [Bridge sub-module] --> (logs to) [Annáll]
```

No domain below the Bridges may import from the Bridges.

---

## Cross-References

- **Philosophy relevance:** [docs/PHILOSOPHY.md §II Principle 1](../../../docs/PHILOSOPHY.md) — "The Agent Is the Smith." The Bridges are the forge's only face to the outside world. [Sacred Law IX](../../../docs/PHILOSOPHY.md) — "No Human Door." All access is programmatic, through these documented interfaces.
- **Data flow relevance:** [docs/DATA_FLOW.md §I Steps 1 and 9](../../../docs/DATA_FLOW.md) — the Bridges handle request ingestion and response delivery.
- **Architecture relevance:** [docs/ARCHITECTURE.md §I Layer 4](../../../docs/ARCHITECTURE.md) and [§II The Shared Anvil Pattern](../../../docs/ARCHITECTURE.md).
- **Decisions:** [D-002](../../../docs/DECISIONS/D-002-repo-and-branch.md), [D-005](../../../docs/DECISIONS/D-005-annall-port-injection-pattern.md)
- **Domain Map:** [docs/DOMAIN_MAP.md — Bridges](../../../docs/DOMAIN_MAP.md)

---

*Written by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
