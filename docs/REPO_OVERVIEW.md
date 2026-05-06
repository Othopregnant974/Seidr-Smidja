# Seiðr-Smiðja — Repository Overview
**Last updated:** 2026-05-06
**Scope:** Top-level living map of the project terrain — for any agent or human arriving cold.
**Author:** Védis Eikleið (Cartographer)

---

> *Before you walk the paths, let the terrain show itself to you. This document is the map you read before touching anything else.*

---

## The One-Sentence Soul

**Seiðr-Smiðja** is an agent-only VRM avatar smithy — a headless, programmatic forge where AI agents weave a parametric avatar specification on the Loom, strike it into form on the Anvil, look upon it through the Oracle Eye, judge it at the Gate, and deliver a fully VRChat-ready and VTube-Studio-ready `.vrm` file.

No human GUI exists. Every operation is invocable by code, through a documented, stable interface.

---

## Current Folder Tree

```
Seiðr-Smiðja/
│
├── README.md                          ← Front door. Project identity, install, quickstart.
├── TASK_seidr_smidja_genesis.md       ← Session-resumption file. Phase inventory and progress tracker.
├── pyproject.toml                     ← Package definition. Entry points, dependencies, pytest markers.
├── .gitignore
│
├── docs/                              ← All project-level documentation.
│   ├── SYSTEM_VISION.md               ← [Skald] Vision scroll: Primary Rite, Unbreakable Vows, True Names.
│   ├── PHILOSOPHY.md                  ← [Skald] Soul, Five Sacred Principles, Ten Sacred Laws.
│   ├── DOMAIN_MAP.md                  ← [Architect] All domains, ownership, one-sentence contracts, dependency law.
│   ├── ARCHITECTURE.md                ← [Architect] Layered model, Shared Anvil, subprocess pattern, config.
│   ├── DATA_FLOW.md                   ← [Cartographer] Primary Rite walkthrough, sequence diagrams, failure flows. ← YOU ARE HERE
│   └── REPO_OVERVIEW.md               ← [Cartographer] This file. Terrain map and navigation guide.
│   (forthcoming in Phase 4 — Scribe)
│   ├── DEVLOG.md
│   └── DECISIONS/
│
├── config/                            ← (forthcoming) YAML configuration files. Never edit defaults.yaml directly.
│   ├── defaults.yaml                  ← Shipped defaults. Source of truth for all config keys.
│   └── user.yaml                      ← User/operator overrides. Gitignored. Created on first run.
│
├── src/
│   └── seidr_smidja/                  ← The package root.
│       ├── __init__.py
│       │
│       ├── loom/                      ← Loom — the Norn-Loom. Spec schema, validation, serialization.
│       │   ├── __init__.py
│       │   └── INTERFACE.md           ← Public contract: load_and_validate(), AvatarSpec, LoomValidationError.
│       │
│       ├── hoard/                     ← Hoard — the Asset Hoard. Base .vrm catalog and resolution.
│       │   ├── __init__.py
│       │   └── INTERFACE.md           ← Public contract: resolve(), list_assets(), AssetNotFoundError.
│       │
│       ├── forge/                     ← Forge — the Smiðja. Headless Blender build subprocess.
│       │   ├── __init__.py
│       │   └── INTERFACE.md           ← Public contract: build(), resolve_blender_executable(), ForgeResult.
│       │
│       ├── oracle_eye/                ← Oracle Eye — Óðins-Auga. Blender render subprocess and vision feedback.
│       │   ├── __init__.py
│       │   └── INTERFACE.md           ← Public contract: render(), RenderView, RenderResult.
│       │
│       ├── gate/                      ← Gate — the Compliance Gate. VRChat + VTube Studio validators.
│       │   ├── __init__.py
│       │   └── INTERFACE.md           ← Public contract: check(), ComplianceReport, ComplianceTarget.
│       │
│       ├── annall/                    ← Annáll — the Record. Session tracking and event logging.
│       │   ├── __init__.py
│       │   ├── INTERFACE.md           ← Public contract: AnnallPort (5 methods), AnnallEvent, SessionID.
│       │   └── adapters/
│       │       └── __init__.py        ← SQLiteAnnallAdapter lives here. Never imported directly by callers.
│       │
│       └── bridges/                   ← Bridges — the Bifröst Bridges. Agent-facing entry points.
│           ├── __init__.py
│           ├── INTERFACE.md           ← All four entry points: Mjöll (MCP), Rúnstafr (CLI), Straumur (REST), Skills.
│           ├── core/
│           │   ├── __init__.py
│           │   └── INTERFACE.md       ← Shared Anvil: dispatch(BuildRequest, annall) → BuildResponse.
│           ├── mjoll/                 ← Mjöll — MCP Bridge. Speaks the Model Context Protocol.
│           │   └── __init__.py
│           ├── runstafr/              ← Rúnstafr — CLI Bridge. `seidr` console script.
│           │   └── __init__.py
│           ├── straumur/              ← Straumur — REST Bridge. FastAPI HTTP server.
│           │   └── __init__.py
│           └── skills/                ← Skill Bridges — YAML manifests for Hermes, OpenClaw, Claude Code.
│               └── __init__.py
│
├── tests/                             ← (forthcoming in Phase 5) Pytest test suite.
│   └── (requires_blender tests marked and excluded from default CI run)
│
├── examples/                          ← (forthcoming in Phase 5) Example spec files.
│   └── spec_minimal.yaml
│
└── data/                              ← (forthcoming) Compliance rule YAML files, Hoard catalog.
    ├── compliance_rules/
    │   ├── vrchat.yaml
    │   └── vtube_studio.yaml
    └── hoard_catalog.yaml
```

---

## "Where Do I Look For…?" — Navigation Table

| Question | Go to |
|---|---|
| What does this project do? | [docs/SYSTEM_VISION.md](./SYSTEM_VISION.md) — Primary Rite, Unbreakable Vows, Central Image |
| What are the rules I must not break? | [docs/PHILOSOPHY.md](./PHILOSOPHY.md) — Sacred Laws I–X |
| Who owns what responsibility? | [docs/DOMAIN_MAP.md](./DOMAIN_MAP.md) — all seven domains and the Dependency Law |
| How is the code structured in layers? | [docs/ARCHITECTURE.md](./ARCHITECTURE.md) — the four-layer model and the Shared Anvil pattern |
| How does a build request flow end-to-end? | [docs/DATA_FLOW.md](./DATA_FLOW.md) — the 9-step Primary Rite walkthrough |
| How do I invoke the forge from an agent? | [src/seidr_smidja/bridges/INTERFACE.md](../src/seidr_smidja/bridges/INTERFACE.md) — all four entry points |
| What does `dispatch()` do exactly? | [src/seidr_smidja/bridges/core/INTERFACE.md](../src/seidr_smidja/bridges/core/INTERFACE.md) |
| How does spec validation work? | [src/seidr_smidja/loom/INTERFACE.md](../src/seidr_smidja/loom/INTERFACE.md) |
| How does the Hoard find a base mesh? | [src/seidr_smidja/hoard/INTERFACE.md](../src/seidr_smidja/hoard/INTERFACE.md) |
| How does Blender get invoked for building? | [src/seidr_smidja/forge/INTERFACE.md](../src/seidr_smidja/forge/INTERFACE.md) + [ARCHITECTURE.md §V](./ARCHITECTURE.md) |
| How do renders get produced? | [src/seidr_smidja/oracle_eye/INTERFACE.md](../src/seidr_smidja/oracle_eye/INTERFACE.md) |
| How does compliance checking work? | [src/seidr_smidja/gate/INTERFACE.md](../src/seidr_smidja/gate/INTERFACE.md) |
| How does logging and session history work? | [src/seidr_smidja/annall/INTERFACE.md](../src/seidr_smidja/annall/INTERFACE.md) |
| What does success look like in the response? | [src/seidr_smidja/bridges/core/INTERFACE.md](../src/seidr_smidja/bridges/core/INTERFACE.md) — `BuildResponse` |
| What happens when Blender crashes? | [docs/DATA_FLOW.md §VIII Failure C](./DATA_FLOW.md) |
| What happens when compliance fails? | [docs/DATA_FLOW.md §VIII Failure D](./DATA_FLOW.md) |
| How does the feedback loop work? | [docs/DATA_FLOW.md §VII Vision Feedback Loop](./DATA_FLOW.md) |
| Where does the CLI entry point live? | `pyproject.toml` → `seidr_smidja.bridges.runstafr.cli:main` |
| How does config layering work? | [docs/ARCHITECTURE.md §VIII](./ARCHITECTURE.md) — `defaults.yaml` / `user.yaml` / `SEIDR_` env vars |
| What can be tested without Blender? | [docs/ARCHITECTURE.md §IX](./ARCHITECTURE.md) — Loom, Hoard, Gate, Annáll, Bridge Core |
| How do I extend the spec schema for another project? | [docs/ARCHITECTURE.md §IV](./ARCHITECTURE.md) — the `extensions` field |
| What was decided at founding and why? | [docs/DECISIONS/](./DECISIONS/) (forthcoming — Phase 4) |
| Where is the daily log? | [docs/DEVLOG.md](./DEVLOG.md) (forthcoming — Phase 4) |
| Where is the phase progress tracker? | [TASK_seidr_smidja_genesis.md](../TASK_seidr_smidja_genesis.md) — Section 5 |
| What open decisions must the Forge Worker make? | [docs/DATA_FLOW.md §X](./DATA_FLOW.md) — five flagged tensions |

---

## Reading Order for New Arrivals

*Walk this path in order. Each scroll opens the next one.*

1. **[docs/SYSTEM_VISION.md](./SYSTEM_VISION.md)** — Read the Central Image first (the Hermes völva story). Then read the Unbreakable Vows. This tells you what the forge promises. Five minutes here saves hours of misunderstanding.

2. **[docs/PHILOSOPHY.md](./PHILOSOPHY.md)** — Read the Five Sacred Principles and the Ten Sacred Laws. These are not guidelines — they are structural invariants. If something you plan to do violates one of these, stop and ask Volmarr before proceeding.

3. **[docs/DOMAIN_MAP.md](./DOMAIN_MAP.md)** — Read the Dependency Law first, then each domain entry. Understand what each domain owns and, equally important, what it does not own.

4. **[docs/ARCHITECTURE.md](./ARCHITECTURE.md)** — Skim the four-layer diagram. Read Section II (Shared Anvil) carefully. Read Section V (Forge Subprocess Pattern) — this is the most technically unusual part of the system.

5. **[docs/DATA_FLOW.md](./DATA_FLOW.md)** — Read the nine-step Primary Rite walkthrough. Then read the Hoard branch, the Blender runner diagram, and the failure flows. This is the living map of how the code runs.

6. **The relevant INTERFACE.md** — Whichever domain you are working in: read its `INTERFACE.md` before touching its code. The public contract is the law of that domain.

7. **[TASK_seidr_smidja_genesis.md](../TASK_seidr_smidja_genesis.md)** — Check the Phase progress tracker (Section 5) to understand where the project is right now and what work is pending.

---

## Session-Resumption Pointer

If you arrive at this repository after a break — whether as a human, an AI agent, or a new Runa session — your first move is:

**Read `TASK_seidr_smidja_genesis.md`** at the project root.

This file holds:
- The full scope of the founding work
- A phase-by-phase inventory of what is done vs. pending
- The exact next step for each pending phase
- The locked decisions (Path B, VRoid base mesh strategy, repo structure)
- The open decisions still to be made

After reading the task file, read whichever phase documents already exist, in reading order above. Do not add to any phase's work without absorbing what the previous phases established.

---

## True Names — A Brief Legend

The forge uses a precise vocabulary. These names carry architectural meaning — they are not decorative.

| True Name | What It Is | Folder |
|---|---|---|
| **Loom** (the Norn-Loom) | Avatar spec schema, validation, serialization | `src/seidr_smidja/loom/` |
| **Hoard** (the Asset Hoard) | Base `.vrm` catalog, resolution, fetch/cache | `src/seidr_smidja/hoard/` |
| **Forge** (the Smiðja) | Headless Blender build subprocess orchestration | `src/seidr_smidja/forge/` |
| **Oracle Eye** (Óðins-Auga) | Headless Blender render subprocess; vision feedback | `src/seidr_smidja/oracle_eye/` |
| **Gate** (the Compliance Gate) | VRChat + VTube Studio compliance validation | `src/seidr_smidja/gate/` |
| **Annáll** (the Record) | Session tracking, event logging, build history | `src/seidr_smidja/annall/` |
| **Bridges** (the Bifröst Bridges) | Agent-facing entry points (all four) | `src/seidr_smidja/bridges/` |
| **Mjöll** | MCP Bridge — speaks Model Context Protocol | `src/seidr_smidja/bridges/mjoll/` |
| **Rúnstafr** | CLI Bridge — the `seidr` console script | `src/seidr_smidja/bridges/runstafr/` |
| **Straumur** | REST Bridge — FastAPI HTTP server | `src/seidr_smidja/bridges/straumur/` |
| **Shared Anvil** | Bridge Core — `dispatch(request, annall)` — the single orchestration path | `src/seidr_smidja/bridges/core/` |
| **AnnallPort** | The abstract interface all Annáll callers use. Never import the adapter directly. | `src/seidr_smidja/annall/port.py` (forthcoming) |
| **AvatarSpec** | The validated, typed avatar description produced by the Loom | data model in `loom/` |
| **BuildRequest** | Normalized build instruction passed to the Shared Anvil | data model in `bridges/core/` |
| **BuildResponse** | The forge's answer — `.vrm` path + renders + compliance report | data model in `bridges/core/` |
| **The Primary Rite** | The complete forge cycle: spec → validate → resolve → build → render → comply → return | [DATA_FLOW.md](./DATA_FLOW.md) |
| **Dependency Law** | Bridges → Loom → Hoard → Forge → Oracle Eye → Gate; Annáll is ambient | [DOMAIN_MAP.md](./DOMAIN_MAP.md) |
| **Path B** | The founding technical decision: VRoid Studio templates + headless Blender + VRM Add-on | [TASK_seidr_smidja_genesis.md](../TASK_seidr_smidja_genesis.md) §3 |

---

## A Note on the Mythic Engineering Roles

This repository was built using the Mythic Engineering protocol. Six named roles each own a piece of the work:

| Role | Name | What They Built Here |
|---|---|---|
| Skald | Sigrún Ljósbrá | SYSTEM_VISION.md, PHILOSOPHY.md |
| Architect | Rúnhild Svartdóttir | DOMAIN_MAP.md, ARCHITECTURE.md, all INTERFACE.md files |
| Cartographer | Védis Eikleið | DATA_FLOW.md, REPO_OVERVIEW.md (this file) |
| Scribe | Eirwyn Rúnblóm | README.md refinement, DEVLOG.md, DECISIONS/ (Phase 4) |
| Forge Worker | Eldra Járnsdóttir | Vertical slice implementation (Phase 5) |
| Auditor | Sólrún Hvítmynd | AUDIT_GENESIS.md, invariant verification (Phase 6) |

If a document here feels wrong or inconsistent, raise it to the appropriate role — or to Volmarr directly. The documentation is not cosmetic. It is the shape of the system written in living language.

---

*Drawn at the third founding fire, 2026-05-06.*
*Védis Eikleið, Cartographer — for Volmarr Wyrd.*
