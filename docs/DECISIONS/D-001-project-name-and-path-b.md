# D-001 — Project Name and Path B
**Status:** Accepted
**Date:** 2026-05-06
**Deciders:** Volmarr Wyrd, Runa Gridweaver Freyjasdóttir
**Phase:** Genesis (pre–vertical-slice)

---

## Context

At the project's founding, two foundational choices needed to be recorded before any architecture could be drawn: what is this thing called, and how does it produce VRM avatars? Both choices had been discussed informally but had not been ratified as locked decisions. Without locking them, every subsequent document would be hedged and every implementation choice would carry implicit uncertainty.

The name question was straightforward: the project needed a name that carried its soul. The base mesh strategy question was more substantial: there were three viable approaches to producing VRM avatars headlessly, each with different tradeoffs.

**Path A** — Build meshes from scratch using Blender's scripting API and `bpy`. Full control, maximum effort. Requires implementing human body mesh generation from parametric inputs — months of work before any avatar is possible.

**Path B** — Use VRoid Studio templates as base meshes, Blender headlessly as the refinement engine, and the VRM Add-on for Blender (saturday06) as the import/export layer. The base mesh problem is solved by an existing ecosystem; the forge's work is parametric refinement, compliance, and delivery.

**Path C** — Use VRoid Studio's own export pipeline directly (via automation or API). Dependent on VRoid Studio's stability and API availability; headless operation is uncertain.

---

## Decision

**The project is named Seiðr-Smiðja (Seething-Forge).**

**Path B is the chosen base mesh strategy:** VRoid Studio templates as base meshes, Blender headless as the refinement engine, the VRM Add-on for Blender (saturday06) as the I/O layer.

Specifically:
- Base meshes: VRoid Studio default and curated templates (anime/stylized humanoid, VRM 1.0 spec compliant).
- Refinement: Blender invoked in headless mode via `blender --background --python script.py`.
- VRM I/O: VRM Add-on for Blender (https://github.com/saturday06/VRM-Addon-for-Blender), which handles VRM 0.x and 1.0 import/export, humanoid bone validation, expressions, spring bones, first-person flags, and license metadata.

---

## Consequences

**Path B makes possible:**
- Starting with fully rigged, compliant VRM meshes instead of building rig from scratch.
- Reusing the extensive VRoid Studio ecosystem of base templates, hair presets, and outfit presets.
- Focusing the forge's implementation effort on parametric refinement and compliance logic rather than mesh generation.
- The oracle eye's render pipeline works immediately on VRM-compliant meshes with Eevee.

**Path B constrains:**
- Every base mesh in the Hoard must be a VRoid Studio template (or compatible VRM file). Non-VRM meshes cannot be used as base assets in v0.1.
- The saturday06 VRM Add-on must be installed in the Blender environment. This is a dependency that must be present before any Forge build can succeed.
- The system is inherently anime/stylized-humanoid focused (VRoid's aesthetic). Non-anime humanoid styles are harder to achieve from these bases.

**What must be revisited later:**
- The saturday06 Add-on's compatibility must be checked when Blender major versions are upgraded.
- If a non-VRoid-style base mesh is required in a future phase, the Hoard catalog and Forge scripts must be extended accordingly.

---

## References

- [`docs/SYSTEM_VISION.md`](../SYSTEM_VISION.md) — The Primary Rite and Central Image, which assume Path B.
- [`TASK_seidr_smidja_genesis.md`](../../TASK_seidr_smidja_genesis.md) §4 — Path B technical foundation.
- [`docs/ARCHITECTURE.md §V`](../ARCHITECTURE.md) — Forge Isolation and the Blender subprocess pattern.
- VRM Add-on for Blender: https://github.com/saturday06/VRM-Addon-for-Blender

---

*Recorded by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
