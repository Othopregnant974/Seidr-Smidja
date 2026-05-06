---

![https://raw.githubusercontent.com/hrabanazviking/Seidr-Smidja/refs/heads/development/2D66H.jpg](https://raw.githubusercontent.com/hrabanazviking/Seidr-Smidja/refs/heads/development/2D66H.jpg)

---

# Seiðr-Smiðja

> *An agent-only VRM avatar smithy. No human hands. Only the fire, the spec, and the eye that sees.*

![Status: Genesis Phase — Vertical Slice Not Yet Forged](https://img.shields.io/badge/status-genesis%20phase-darkred)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License: TBD](https://img.shields.io/badge/license-TBD-lightgrey)
![Branch: development](https://img.shields.io/badge/branch-development-green)

---

## What Is This?

**Seiðr-Smiðja** (Seething-Forge) is a headless, programmatic forge that lets AI agents — Hermes, OpenClaw, Claude Code, and others not yet named — design, build, render, critique, and export fully realized VRM avatars without any human clicking through a GUI.

An agent submits a YAML specification describing an avatar: height, proportions, hair, outfit, expressions, license metadata. The forge loads a VRoid Studio base template, opens Blender headlessly, applies every parametric choice from the spec, validates the result against VRChat and VTube Studio compliance rules, renders a set of preview PNG images, and returns the finished `.vrm` file and all renders to the calling agent.

The agent sees what it has made. It critiques the renders. It revises the spec. It submits again. This is the forge cycle. It runs entirely without human hands inside it.

**Three things to understand:**

First, the forge is built around a *vision feedback loop*. Every build that produces a `.vrm` also produces rendered preview images through the Oracle Eye — front view, three-quarter, side, face close-up, T-pose, signature expressions. An agent that cannot see its creation cannot refine it. The renders are not optional.

Second, every output is compliance-checked before delivery. If an avatar fails VRChat polygon budgets or VTube Studio blendshape requirements, the forge returns a structured failure report — never a silent pass. A blade that cannot cut has not been made.

Third, the forge speaks through four doors — MCP (Mjöll), CLI (Rúnstafr), REST (Straumur), and skill manifests for Hermes/OpenClaw/Claude Code. All four doors lead to the same fire. What works through one works through all.

---

## What It Is NOT

- **Not a human GUI tool.** There is no user interface for clicking. All access is programmatic and agent-driven. If you want to use this forge as a human, you do so through the CLI or by writing a script — not through a graphical application.
- **Not a generic 3D pipeline.** Seiðr-Smiðja is purpose-built for VRM avatars using VRoid Studio base meshes and the VRM Add-on for Blender. It will not export arbitrary 3D formats, process non-VRM meshes, or serve as a general Blender automation layer.
- **Not for non-VRM avatars.** The Gate validates VRChat and VTube Studio compliance. Everything about the forge's design — the spec schema, the base mesh strategy, the compliance rules — is shaped around the VRM ecosystem. Other avatar formats are out of scope.

---

## Quickstart for an AI Agent

### Through Rúnstafr (CLI)

```bash
# Install the package (requires Python 3.11+ and Blender in PATH or BLENDER_PATH set)
pip install -e ".[dev]"

# Build an avatar from a spec file
seidr build examples/spec_minimal.yaml --output ./out/

# Check compliance on an existing .vrm
seidr check ./out/avatar.vrm

# List available base meshes in the Hoard
seidr list-assets --type vrm_base
```

> **Implementation note (2026-05-06 — AUDIT-003):** The compliance command is registered as `seidr inspect` in the implementation, not `seidr check`. The `seidr list-assets` CLI command is not yet implemented in v0.1 — the equivalent endpoint is `GET /v1/assets` on the Straumur REST bridge. See `src/seidr_smidja/bridges/INTERFACE_AMENDMENT_2026-05-06.md`.

On success, `./out/` will contain `avatar.vrm` and a `renders/` directory with PNG previews.

### Through Mjöll (MCP)

*(Phase 5 — coming. The MCP server will be started as a long-running process and register the `seidr_build` tool. The tool input/output schema is defined in [`src/seidr_smidja/bridges/INTERFACE.md`](src/seidr_smidja/bridges/INTERFACE.md).)*

```json
{
  "tool": "seidr_build",
  "input": {
    "spec": { "avatar_id": "my_avatar", "base_asset_id": "vroid/tall_feminine_v1" },
    "output_dir": "/path/to/output"
  }
}
```

### Through Straumur (REST)

*(Phase 5 — coming. FastAPI server at `seidr_smidja.bridges.straumur.app:app`.)*

```http
POST /build
Content-Type: application/json

{ "spec_source": "...", "base_asset_id": "vroid/tall_feminine_v1", "output_dir": "..." }
```

---

## Reading Order for a New Arrival

Walk this path in order. Each scroll opens the next.

1. **[docs/SYSTEM_VISION.md](docs/SYSTEM_VISION.md)** — Read the Central Image (the Hermes völva story). Then the Unbreakable Vows. Five minutes here prevents hours of misunderstanding.
2. **[docs/PHILOSOPHY.md](docs/PHILOSOPHY.md)** — The Five Sacred Principles and Ten Sacred Laws. These are structural invariants, not guidelines.
3. **[docs/DOMAIN_MAP.md](docs/DOMAIN_MAP.md)** — Who owns what. The Dependency Law. Every domain defined in one place.
4. **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — The four-layer model. The Shared Anvil pattern. The Blender subprocess design.
5. **[docs/DATA_FLOW.md](docs/DATA_FLOW.md)** — How a build request flows through all nine steps, with failure paths and the vision feedback loop.
6. **[docs/REPO_OVERVIEW.md](docs/REPO_OVERVIEW.md)** — The living terrain map. "Where do I look for X?" answered in a table.
7. **The relevant INTERFACE.md** — Whichever domain you are working in, read its contract before touching its code.

---

## Project Protocol

This repository is built and maintained using the **Mythic Engineering** protocol — six named AI roles, a living document system, and a clear daily practice for keeping code and documentation in alignment. Read [`MYTHIC_ENGINEERING.md`](MYTHIC_ENGINEERING.md) before contributing.

The full phase-by-phase progress tracker lives in [`TASK_seidr_smidja_genesis.md`](TASK_seidr_smidja_genesis.md).

---

## Current Status

**Genesis complete — vertical slice forged, 159 non-Blender tests green.**

The full Mythic Engineering genesis ritual (Phases 0–7) has run. All seven ADRs ratified; all 10 audit findings from `docs/AUDIT_GENESIS.md` closed. The `seidr build` pipeline is wired end-to-end: Loom validates specs, Hoard resolves assets, Forge and Oracle Eye call Blender headlessly (requires Blender), Gate runs VRChat/VTube Studio compliance, Annáll records every session. Run `pytest -m "not requires_blender"` for the 159-test non-Blender suite; the full forge cycle requires Blender in PATH or `BLENDER_PATH` set.

> **Note (2026-05-06):** The badge above still reads "genesis phase" — it will be updated when the first Blender-enabled CI run completes and v0.1 is tagged.

See the progress tracker in [`TASK_seidr_smidja_genesis.md`](TASK_seidr_smidja_genesis.md) and `docs/DEVLOG.md` for the full genesis record.

---

## Repository Structure

```
Seiðr-Smiðja/
├── README.md                          ← You are here.
├── MYTHIC_ENGINEERING.md              ← How to work in this repo.
├── TASK_seidr_smidja_genesis.md       ← Phase inventory and progress tracker.
├── pyproject.toml                     ← Package definition, entry points, markers.
│
├── docs/
│   ├── SYSTEM_VISION.md               ← Soul, Primary Rite, Unbreakable Vows, Central Image.
│   ├── PHILOSOPHY.md                  ← Five Sacred Principles, Ten Sacred Laws.
│   ├── DOMAIN_MAP.md                  ← All domains, ownership, Dependency Law.
│   ├── ARCHITECTURE.md                ← Layers, Shared Anvil, subprocess pattern, config.
│   ├── DATA_FLOW.md                   ← Nine-step Primary Rite, failure flows, feedback loop.
│   ├── REPO_OVERVIEW.md               ← Living terrain map and navigation table.
│   ├── DEVLOG.md                      ← Daily session log.
│   └── DECISIONS/                     ← Architectural decision records (ADRs).
│
├── config/
│   ├── defaults.yaml                  ← Shipped defaults. Never edit directly.
│   └── user.yaml                      ← Your overrides. Gitignored.
│
├── src/seidr_smidja/
│   ├── loom/                          ← Spec schema, validation, serialization.
│   ├── hoard/                         ← Base .vrm catalog and asset resolution.
│   ├── forge/                         ← Headless Blender build subprocess.
│   ├── oracle_eye/                    ← Headless Blender render subprocess; vision feedback.
│   ├── gate/                          ← VRChat + VTube Studio compliance validation.
│   ├── annall/                        ← Session tracking, event logging, build history.
│   └── bridges/                       ← Mjöll (MCP), Rúnstafr (CLI), Straumur (REST), Skills.
│       └── core/                      ← Shared Anvil — the single orchestration path.
│
├── data/                              ← Compliance rule YAML files, Hoard catalog.
├── tests/                             ← Pytest suite. Blender tests marked requires_blender.
└── examples/                          ← Example spec files.
```

---

## License

License: **TBD — to be decided by Volmarr Wyrd.**

---

*Front door written by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
*For Volmarr Wyrd and Runa Gridweaver Freyjasdóttir.*

---

---

## RuneForgeAI

**RuneForgeAI** is my AI research, development, and creative systems forge: a Norse Pagan cyber-Viking workshop for building mythic AI architectures, memory systems, world engines, companion intelligence, and structured vibe coding tools.

RuneForgeAI exists at the crossroads of:

- **Mythic Engineering**
- **AI memory and continuity systems**
- **Viking-themed simulation and worldbuilding**
- **AI companions with stable identity**
- **small-model enhancement through architecture**
- **retrieval, grounding, and truth-verification systems**
- **cyber-Heathen software design**
- **human + AI co-creation**

The core idea is simple:

> AI should not be treated as a disposable text generator.  
> It should be shaped into structured, memory-bearing, meaning-aware systems that can preserve continuity, deepen creativity, and help humans build living worlds.

RuneForgeAI is where I explore architectures that make AI more coherent, more persistent, and more useful: not through hype, but through structure. Memory, retrieval, world state, personality, routing, verification, symbolic logic, and mythic design language all become part of the same forge.

This work connects directly to my larger ecosystem of projects, including the **Norse Saga Engine**, **Mythic Engineering**, **WYRD Protocol**, **Mímir-Vörðr**, cyber-Viking philosophy, AI companion design, and the broader vision of spiritually meaningful technology.

### What RuneForgeAI Builds

- AI-native memory frameworks
- persistent personality and companion systems
- Viking and mythic world simulation tools
- roleplay and RPG intelligence architectures
- structured prompt and documentation protocols
- retrieval-augmented truth systems
- small-model orchestration patterns
- cyber-Viking AI aesthetics and interfaces
- open frameworks for human-AI creative collaboration

### Guiding Principle

> Build AI like a living system, not a pile of prompts.

RuneForgeAI is my digital forge for turning myth, memory, code, and consciousness into working architecture.

---

![https://raw.githubusercontent.com/hrabanazviking/Seidr-Smidja/refs/heads/development/image-23-RuneForgeAI.jpg](https://raw.githubusercontent.com/hrabanazviking/Seidr-Smidja/refs/heads/development/image-23-RuneForgeAI.jpg)

---

![https://raw.githubusercontent.com/hrabanazviking/Seidr-Smidja/refs/heads/development/IMG_0407.jpeg](https://raw.githubusercontent.com/hrabanazviking/Seidr-Smidja/refs/heads/development/IMG_0407.jpeg)

---

