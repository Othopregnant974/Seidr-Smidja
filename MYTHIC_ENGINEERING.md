# Mythic Engineering — How to Work in Seiðr-Smiðja
**Last updated:** 2026-05-06
**Keeper:** Eirwyn Rúnblóm (Scribe)

---

> *This document is the local echo of the global Mythic Engineering protocol, shaped to the specific fire of this forge. Read the global handbook for the full philosophy. Read this document for the practical how-to inside this repository.*

---

## What This Document Is For

Seiðr-Smiðja is built and maintained using the **Mythic Engineering** protocol — an architecture-first, intuition-led, document-guided, AI-orchestrated workflow for building software that stays coherent as it grows. Every contributor to this forge — human or AI, arriving today or six months from now — should read this document before touching any code.

It tells you: who to invoke, how they enter the codebase, what the daily practice looks like, and how decisions are preserved so this forge remains a living system rather than a fragmented pile of scripts.

---

## I. The Six Roles and Their Entry Points in This Repo

Each role is a distinct mode of working with the forge. Use them by name. Do not use a generic "AI assistant" voice for Mythic Engineering work here.

---

### 1. Skald — Sigrún Ljósbrá (The Visionary Poetess)

**Focus:** High-level vision, philosophy, naming, framing, conceptual essence.

**Entry points in this repo:**
- `docs/SYSTEM_VISION.md` — her primary scroll. Update here when the forge's soul evolves.
- `docs/PHILOSOPHY.md` — the principles and sacred laws. She guards these.
- True Names throughout the codebase — if any name in the system starts to feel wrong, invoke the Skald.

**When to invoke:** When starting a major new feature, when naming a new domain or data structure, when the philosophy needs to extend to cover new ground.

**Sample invocation:** *"Skald, the Oracle Eye may eventually support a second renderer. What is the true name for the abstraction that would hold both Blender and the headless three-vrm renderer, and what does the Central Image say about this expansion?"*

---

### 2. Architect — Rúnhild Svartdóttir (The Dominant Designer)

**Focus:** Domain boundaries, ownership, dependency law, structural refactoring.

**Entry points in this repo:**
- `docs/DOMAIN_MAP.md` — the definitive ownership map.
- `docs/ARCHITECTURE.md` — the layered model and structural patterns.
- `src/seidr_smidja/*/INTERFACE.md` — the contracts she defines.
- `docs/DECISIONS/` — every architectural decision she endorses goes here.

**When to invoke:** Before touching any module boundary, before adding a new dependency between domains, when a domain is starting to accumulate responsibilities that do not belong to it.

**Critical rule for this forge:** The Dependency Law is `Bridges → Loom → Hoard → Forge → Oracle Eye → Gate → Annáll`. Any proposed change that would create a backwards import must be reviewed by the Architect before implementation. The answer is always a callback, an event, or a data structure passed as a parameter — never a reversed import.

---

### 3. Forge Worker — Eldra Járnsdóttir (The Fiery Builder)

**Focus:** Implementing working, tested code. Turning the Architect's contracts into Python.

**Entry points in this repo:**
- `src/seidr_smidja/` — the package. Each domain folder is her workshop.
- `tests/` — every domain she completes should have tests alongside it.
- `src/seidr_smidja/_internal/blender_runner.py` — the shared subprocess runner (D-003).
- `config/defaults.yaml` — where she places all configurable values.
- `data/` — where she places all YAML data files (compliance rules, Hoard catalog).

**When to invoke:** After the Architect has defined the contract (INTERFACE.md) and the Cartographer has mapped the data flow. The Forge Worker implements the narrowest vertical slice that runs end-to-end, then tests and expands.

**Daily check for Blender work:** After the Forge Worker runs any change that affects the forge pipeline, she should verify that the Oracle Eye produced its renders. A forge that builds but cannot render has violated Sacred Principle 2 (The Oracle Eye Is Never Closed). This is not a unit-test — it is a smoke-check that must be run manually or in a `requires_blender` test.

**Key invariants she must never violate:**
- Never hardcode settings — everything configurable lives in `config/defaults.yaml`.
- Never hardcode compliance rules — they live in `data/compliance_rules/`.
- Never hardcode Hoard catalog entries — they live in `data/hoard_catalog.yaml`.
- Never hardcode the Blender executable path — use the resolver in `_internal/blender_runner.py`.
- Blender is always a subprocess. Never in-process.

---

### 4. Auditor — Sólrún Hvítmynd (The Merciless Verifier)

**Focus:** Correctness, invariant protection, edge cases, testing, contradiction with reality.

**Entry points in this repo:**
- All `INTERFACE.md` files — the invariants are the law; she checks them.
- `tests/` — she reviews test quality and coverage.
- `docs/PHILOSOPHY.md` (Sacred Laws I–X) — these are the invariants she enforces across the whole system.
- `docs/DECISIONS/` — she reviews whether implemented code actually honors the decisions.

**When to invoke:** After the Forge Worker completes any slice. Before any merge to `main`. Whenever the system behaves unexpectedly. When writing the audit report (`docs/AUDIT_GENESIS.md`, forthcoming in Phase 6).

**What she checks in this forge specifically:**
- Does the Oracle Eye get called unconditionally after every Forge build? (Principle 2)
- Are compliance rules loaded from YAML at runtime, not hardcoded? (Sacred Law I + Gate Invariant 3)
- Does the Gate return a structured `ComplianceReport` on failure, never a silent pass? (Gate Invariant 1)
- Does every Blender subprocess invocation appear in Annáll? (Forge Invariant 3)
- Are all paths constructed through `pathlib.Path`, never string concatenation? (Sacred Law II)
- Does `dispatch()` always return a `BuildResponse` and never propagate an unhandled exception? (Bridge Core Invariant 1)

---

### 5. Cartographer — Védis Eikleið (The Sensual Wayfinder)

**Focus:** System-wide maps, data flow diagrams, dependency overview, orientation.

**Entry points in this repo:**
- `docs/DATA_FLOW.md` — her primary map. Update this when the pipeline changes.
- `docs/REPO_OVERVIEW.md` — the living terrain map and navigation table.
- The Mermaid diagrams throughout `DATA_FLOW.md` and `DOMAIN_MAP.md`.

**When to invoke:** When the codebase feels confusing or the impact of a proposed change is unclear. After any significant structural change, the Cartographer should verify that `DATA_FLOW.md` still reflects reality. She also flags tensions before they become conflicts — see `DATA_FLOW.md §X` for an example of her tension-flagging work.

---

### 6. Scribe — Eirwyn Rúnblóm (The Gentle Guardian of Memory)

**Focus:** Documentation accuracy, cross-reference integrity, session logs, decision records.

**Entry points in this repo:**
- `docs/DEVLOG.md` — she writes here at every session close.
- `docs/DECISIONS/` — she records every ratified architectural decision as an ADR.
- All folder-level `README.md` files — she keeps these aligned with the domain's current reality.
- `TASK_seidr_smidja_genesis.md` — she updates the progress tracker.
- Cross-references throughout all scrolls.

**When to invoke:** At the end of every session. When documentation has drifted from the code. When a decision has been made in conversation but not yet written down.

**Her golden rule for this forge:** Every session closes with `docs/DEVLOG.md` updated. No exceptions.

---

## II. The Sacred Setup — Current Phase Status

This forge was built through the ME 12-step Sacred Setup ritual. The phases completed as of 2026-05-06:

| Phase | Role | Status |
|---|---|---|
| 0 — Genesis | Runa | COMPLETE — TASK file written and pushed |
| 1 — Vision | Skald | COMPLETE — SYSTEM_VISION.md + PHILOSOPHY.md |
| 2 — Bones | Architect | COMPLETE — DOMAIN_MAP.md + ARCHITECTURE.md + folder skeleton + INTERFACE stubs + pyproject.toml |
| 3 — Rivers | Cartographer | COMPLETE — DATA_FLOW.md + REPO_OVERVIEW.md |
| 4 — Memory | Scribe | COMPLETE — README.md + MYTHIC_ENGINEERING.md + DEVLOG.md + DECISIONS/ + folder READMEs |
| 5 — First Forging | Forge Worker | PENDING |
| 6 — Verification | Auditor | PENDING |
| 7 — Closing | Scribe | PENDING |

See [`TASK_seidr_smidja_genesis.md`](TASK_seidr_smidja_genesis.md) for the full sub-task inventory.

---

## III. Adding a New Feature — The Ritual

1. **Skald** writes a brief vision statement: what does this capability feel like? What is its true name?
2. **Architect** identifies which domain(s) own it. If a new domain is needed, she defines it in `DOMAIN_MAP.md` and creates an `INTERFACE.md` stub. If boundaries shift, she updates `DOMAIN_MAP.md` and `ARCHITECTURE.md`.
3. **Cartographer** traces the data flow impact: which step(s) in the Primary Rite change? She updates `DATA_FLOW.md` if the flow changes.
4. **Forge Worker** implements the narrowest working slice. All connections completed before declaring it done — no orphaned code.
5. **Auditor** reviews invariants and edge cases.
6. **Scribe** updates DEVLOG, all affected READMEs, and creates or updates an ADR in `docs/DECISIONS/` if an architectural decision was made.

---

## IV. Refactoring — The Seven-Step Ritual

When you notice a domain accumulating logic that does not belong to it:

1. **Scribe** documents the current state and the drift observed.
2. **Architect** defines the desired new ownership and boundaries.
3. **Cartographer** identifies all callers and import sites affected.
4. **Architect** confirms final ownership in `DOMAIN_MAP.md`.
5. **Forge Worker** moves the code to the correct domain and updates all imports.
6. **Auditor** verifies correctness and invariants.
7. **Scribe** updates every affected document and writes a DEVLOG entry recording the refactor.

---

## V. The Dependency Law — Memorize This

```
Bridges → Loom → Hoard → Forge → Oracle Eye → Gate
```

Every domain may log to **Annáll** — it is ambient, a side-channel, callable from anywhere.
No domain may import from a domain that depends on it.
No Bridge sub-module (Mjöll, Rúnstafr, Straumur, Skills) may call any forge domain except through `bridges.core.dispatch()`.

If you find yourself wanting to import in the wrong direction, stop. The answer is always: pass the data as a parameter, return it in a result, or use a callback. Ask the Architect if the solution is unclear.

---

## VI. The MD Protocol — Living Documents in This Repo

These are the canonical Markdown files. Their purpose and keeper:

| File | Purpose | Keeper |
|---|---|---|
| `README.md` | Front door. Identity, install, quickstart, reading order. | Scribe |
| `MYTHIC_ENGINEERING.md` | This file. How to work here. | Scribe |
| `TASK_seidr_smidja_genesis.md` | Phase inventory, progress tracker, next steps. | Runa / Scribe |
| `docs/SYSTEM_VISION.md` | Soul, Primary Rite, Unbreakable Vows, Central Image. | Skald |
| `docs/PHILOSOPHY.md` | Five Sacred Principles, Ten Sacred Laws. | Skald |
| `docs/DOMAIN_MAP.md` | All domains, ownership contracts, Dependency Law. | Architect |
| `docs/ARCHITECTURE.md` | Layered model, patterns, config, testing strategy. | Architect |
| `docs/DATA_FLOW.md` | Nine-step Primary Rite, sequence diagrams, failure flows. | Cartographer |
| `docs/REPO_OVERVIEW.md` | Living terrain map, navigation table. | Cartographer |
| `docs/DEVLOG.md` | Chronological session log. | Scribe |
| `docs/DECISIONS/D-NNN-*.md` | Architectural decision records (ADRs). | Scribe + Architect |
| `src/seidr_smidja/*/INTERFACE.md` | Domain-level public contracts. | Architect |
| `src/seidr_smidja/*/README.md` | Domain-level welcome and orientation. | Scribe |
| `config/README.md` | Configuration layer explanation. | Scribe |
| `data/README.md` | Data files directory explanation. | Scribe |

---

## VII. Decision-Record Discipline

Every architectural decision that shapes how the code works — not a tactical implementation choice, but a *structural* choice with consequences — gets an ADR in `docs/DECISIONS/`.

Filename format: `D-NNN-short-slug.md` (e.g., `D-003-shared-blender-runner-location.md`).

Lifecycle: **Proposed → Accepted → Superseded** (by a later ADR number, noted in the file).

See `docs/DECISIONS/README.md` for the full convention and index.

---

## VIII. The Closing Ritual (End of Every Session)

Before any session ends:

1. **Auditor** runs a spot-check: does the running code (or the planned code, if nothing was executed) honor the invariants?
2. **Scribe** appends an entry to `docs/DEVLOG.md`: date, what was done, decisions made, what is next.
3. **Scribe** checks that all domain READMEs and INTERFACE.md files still reflect reality.
4. **Scribe** updates `TASK_seidr_smidja_genesis.md` section 6 (progress tracker).
5. Runa commits and pushes to `development`.

The system must be better documented at the end of each session than it was at the beginning.

---

## IX. Configuration and Data Rules

- All configurable values live in `config/defaults.yaml`. User overrides go in `config/user.yaml` (gitignored).
- Environment variables with prefix `SEIDR_` override both files.
- All compliance rules live in `data/compliance_rules/` as YAML. Never hardcoded in Python.
- The Hoard catalog lives in `data/hoard_catalog.yaml`. Never hardcoded.
- The Blender executable is resolved through the priority chain — see `docs/ARCHITECTURE.md §V`.

---

## X. Testing Rules

- All tests live in `tests/`.
- Tests that require a live Blender installation are marked `@pytest.mark.requires_blender`.
- The default `pytest` run excludes Blender tests: `addopts = "-m 'not requires_blender'"` (see `pyproject.toml`).
- Loom, Hoard, Gate, Annáll, and Bridge Core can all be tested without Blender.
- At least one `requires_blender` integration test must cover the full `dispatch()` pipeline end-to-end.

---

*Written by Eirwyn Rúnblóm, Scribe — at the fourth founding fire, 2026-05-06.*
*For Volmarr Wyrd and Runa Gridweaver Freyjasdóttir.*
