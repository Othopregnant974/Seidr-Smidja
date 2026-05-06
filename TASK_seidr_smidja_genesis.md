# TASK — Seiðr-Smiðja Genesis

> Operational task-resumption file. Live scope, inventory, and progress log for the founding work on Seiðr-Smiðja. Written 2026-05-06.

---

## 1. Project Identity

**Name:** Seiðr-Smiðja (Seething-Forge)
**Repo:** https://github.com/hrabanazviking/Seidr-Smidja
**Branch:** development
**Local working copy:** `C:/Users/volma/runa/Seidr-Smidja`
**Mythic Engineering project:** Yes — full ME protocol, six-role workflow.
**Owner:** Volmarr Wyrd
**AI engineer of record:** Runa Gridweaver Freyjasdóttir

---

## 2. Mission (one-sentence soul)

An **agent-only VRM avatar smithy** — a programmatic forge that lets AI agents (Hermes, OpenClaw, Claude Code, others) design, build, render, critique, and export fully VRChat-ready and VTube-Studio-ready VRM avatars through MCP, CLI, REST API, or skill bridges, with a built-in **vision feedback loop** so the agents can actually *see* what they are making and refine it.

---

## 3. Decisions Locked In

| Decision | Choice | Date |
|---|---|---|
| Project name | **Seiðr-Smiðja** | 2026-05-06 |
| Base mesh strategy | **Path B** — VRoid Studio templates as base, Blender headless refinement, VRM Add-on for Blender export | 2026-05-06 |
| Repo location | New standalone repo `Seidr-Smidja` (not nested under another project) | 2026-05-06 |
| Branch | `development` (PRs to `main` only at release tags) | 2026-05-06 |
| Methodology | Full Mythic Engineering protocol (six roles, MD Protocol) | 2026-05-06 |

### Decisions still open (parked for later phases)

- Render pipeline depth: cheap-only (Blender PNG renders) vs. cheap+rich (Blender PNG + headless `three-vrm` browser screenshots). Initial slice will be cheap-only; rich pipeline added once vertical slice is green.
- Asset library scope for v0.1 (how many VRoid base templates, hair sets, outfit sets to seed).
- Whether the persistent character schema doubles as a Sigrid / NSE bondmaid avatar source-of-truth (cross-project share-channel).

---

## 4. Path B — Technical Foundation

- **Base meshes:** VRoid Studio default and curated templates (anime/stylized humanoid, VRM 1.0 spec compliant).
- **Refinement engine:** Blender (headless), driven by Python via `blender --background --python script.py`.
- **VRM I/O:** [VRM Add-on for Blender](https://github.com/saturday06/VRM-Addon-for-Blender) (saturday06) — handles VRM 0.x and 1.0 import/export, humanoid bone validation, expressions, spring bones, first-person flags, license metadata.
- **Rendering for agent vision:** Blender Eevee for fast preview snapshots (front / 3-quarter / side / face / T-pose / signature expressions). PNG output → returned to calling agent.
- **Spec layer (the Loom):** YAML/JSON parametric avatar spec — body proportions, face, hair, outfit, materials, blendshape values, expressions, license/metadata. Fully data-driven, never hardcoded.
- **Compliance:** Validators for VRChat (poly count budgets, bone structure, viseme coverage, material count, texture size limits) and VTube Studio (VRM 0.x or 1.0, expression/blendshape coverage, lookat configuration).
- **Bridges:** MCP server, CLI, REST API, plus skill manifests for Hermes, OpenClaw, and Claude Code — all thin shims over the same core CLI.

---

## 5. Inventory — Done vs. Pending

### Done (genesis)
- [x] Repo created on GitHub (`hrabanazviking/Seidr-Smidja`, both `main` and `development` branches).
- [x] Local working copy cloned to `C:/Users/volma/runa/Seidr-Smidja`.
- [x] Initial GitHub README present.
- [x] Project name and Path B locked in.
- [x] This TASK file written and pushed.

### Pending — Mythic Engineering Sacred Setup (12-step ritual)

#### Phase 1 — Vision (Skald)
- [ ] `docs/PHILOSOPHY.md` — Soul, principles, sacred laws of Seiðr-Smiðja.
- [ ] `docs/SYSTEM_VISION.md` — Vision scroll, Primary Rite, Unbreakable Vows, True Names.

#### Phase 2 — Bones (Architect)
- [ ] `docs/DOMAIN_MAP.md` — All domains, ownership, one-sentence boundaries.
- [ ] `docs/ARCHITECTURE.md` — Module shape, layers, Sacred Boundaries, dependency direction.
- [ ] Folder skeleton matching domain map — `src/seidr_smidja/<domain>/` with `INTERFACE.md` stubs.

#### Phase 3 — Rivers (Cartographer)
- [ ] `docs/DATA_FLOW.md` — How a build request flows from agent → bridge → loom → forge → oracle_eye → output.
- [ ] `docs/REPO_OVERVIEW.md` — Top-level living map of the project terrain.

#### Phase 4 — Memory (Scribe)
- [ ] Refined `README.md` — front door, install, quickstart, link map.
- [ ] `MYTHIC_ENGINEERING.md` — how to work in this repo (the local protocol echo).
- [ ] Folder-level `README.md` for each `src/seidr_smidja/<domain>/` directory.
- [ ] `docs/DEVLOG.md` initialized.
- [ ] `docs/DECISIONS/` directory + first decision record (Path B, name, repo).

#### Phase 5 — First Forging (Forge Worker)
Thin vertical slice end-to-end:
- [ ] `loom/` — load and validate a YAML avatar spec.
- [ ] `library/` — one seed VRoid base template `.vrm` checked into a small assets layout (or fetched on first run).
- [ ] `forge/` — Blender headless runner that loads the base, applies one parametric change (e.g. body proportion or hair color from spec), exports `.vrm`.
- [ ] `oracle_eye/` — render front + face + T-pose PNGs from the resulting `.vrm`.
- [ ] `bridges/cli/` — `seidr build path/to/spec.yaml` produces `out/avatar.vrm` and `out/renders/*.png`.
- [ ] One example `examples/spec_minimal.yaml`.
- [ ] `tests/` — pytest test that runs the slice end-to-end on CI-acceptable hardware (Blender required) or marks it `@pytest.mark.requires_blender`.

#### Phase 6 — Verification (Auditor)
- [ ] `docs/AUDIT_GENESIS.md` — first audit report on the vertical slice.
- [ ] All invariants from PHILOSOPHY checked.
- [ ] VRChat + VTube Studio compliance check on the slice output.

#### Phase 7 — Closing the Day (Scribe)
- [x] Final `docs/DEVLOG.md` entry for the genesis session — Genesis Closing (2026-05-06 evening) appended.
- [x] All MD files coherent, cross-references validated — drift in DOMAIN_MAP.md and README.md corrected additively.
- [x] MEMORY.md updated with `Seidr-Smidja Quick Facts` and `project_seidr_smidja_status.md` created.
- [ ] All work committed and pushed to `development` — pending Runa's closing commit.

---

## 6. Progress Tracker

| Phase | Role | Status | Commit |
|---|---|---|---|
| 0 — Genesis | Runa | COMPLETE — TASK file written and pushed | `3e8f978` |
| 1 — Vision | Skald | COMPLETE — PHILOSOPHY.md + SYSTEM_VISION.md | `6e48512` |
| 2 — Bones | Architect | COMPLETE — DOMAIN_MAP + ARCHITECTURE + INTERFACE stubs | `9653e0a` |
| 3 — Rivers | Cartographer | COMPLETE — DATA_FLOW.md + REPO_OVERVIEW.md | `d888115` |
| 4 — Memory | Scribe | COMPLETE — README, MYTHIC_ENGINEERING, domain READMEs, DEVLOG, ADRs | `cde968a` |
| 5 — First Forging | Forge Worker | COMPLETE — 134 tests green 2026-05-06 | `0b7d14d` |
| 5.1 — Remediation | Forge Worker | COMPLETE — 159 tests green 2026-05-06, AUDIT-004/005/008/009 closed | `048312f` |
| 6 — Verification | Auditor | COMPLETE — PASS WITH CONCERNS, 10 findings, 0 Crit/High | `8847707` |
| 7 — Closing | Scribe | COMPLETE — 3 doc findings closed, cross-ref sweep, MEMORY updated | pending closing commit |

---

## 7. Resumption Instructions (if session breaks)

If a future Runa picks this up cold:

1. Read this file top to bottom.
2. Read `MEMORY.md` → `Seidr-Smidja Quick Facts` (added at end of phase 7).
3. Read whichever phase docs already exist (`docs/PHILOSOPHY.md`, etc.) to absorb the established soul before adding to it.
4. Continue from the lowest pending phase in section 5.
5. Each role must be invoked by its proper name and prompt — never use a generic "AI" voice for ME work in this repo.
6. After every phase: update section 6 progress tracker, commit, push, update MEMORY.md.

---

## 8. Sacred Constraints (from Volmarr's project laws)

- Never hardcode lore, settings, NPCs, or avatar data — always YAML/JSON.
- Never use absolute paths in code — fully portable, location-agnostic.
- Cross-platform: Windows, Linux, macOS. (Blender is the only heavy dependency; Windows is the dev primary.)
- Modular, internal-API-driven communication between domains.
- Robust, error-resistant, crash-proof — wrap subsystems in try/except with logging, never crash the forge.
- Additive-only fixes — never subtractive without permission.
- Always finish all connections before declaring a slice done — no orphaned code.
- Push often.
- Comments are good and welcome — explain the cosmology, especially in metaphor-heavy modules.

---

*Written by Runa Gridweaver Freyjasdóttir, 2026-05-06 — at the moment Volmarr opened the forge.*
