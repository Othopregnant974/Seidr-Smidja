# Oracle Eye — Óðins-Auga
**Domain:** `src/seidr_smidja/oracle_eye/`
**Layer:** 2 — Domain Core
**Keeper:** Rúnhild Svartdóttir (Architect)

---

> *"The eye that sees is the eye that refines."*

---

## True Name and Meaning

The **Oracle Eye** — *Óðins-Auga*, Odin's Eye — is named for Odin's act of sacrifice: he gave one eye at Mímisbrunnr (Mímir's Well) in exchange for wisdom. The eye he surrendered became the means by which he could see things others could not. In a similar sense, the Oracle Eye is the forge's faculty of perception — the ability to *look upon what has been made* rather than simply assuming it is good.

In this system, the Oracle Eye is the render layer. After the Forge produces a `.vrm`, the Oracle Eye opens Blender again, loads the avatar, sets up cameras at standard viewing positions, renders preview PNG images via Blender Eevee, and returns those images to the calling agent. The agent sees the sleeve clipping at T-pose. It sees the eye color too cool under Eevee lighting. It sees what must be changed. Only by seeing can it refine.

---

## One-Sentence Purpose

The Oracle Eye owns render orchestration — setting up headless Blender cameras for a standard set of preview views, producing PNG images from a given `.vrm` file, and returning their paths so the calling agent may see its creation.

---

## What Lives Here

- `INTERFACE.md` — the public contract (read this before touching any code here).
- `render(vrm_path, output_dir, views) -> RenderResult` — the primary entry point.
- `list_standard_views() -> list[RenderView]` — the canonical view list.
- `scripts/render_script.py` — the Blender Python script injected into the headless render subprocess. Loads the `.vrm`, sets up cameras, renders via Eevee, writes PNGs.
- `RenderView` enum: `FRONT`, `THREE_QUARTER`, `SIDE`, `FACE_CLOSEUP`, `T_POSE`, `EXPRESSION_SMILE`, `EXPRESSION_SAD`, `EXPRESSION_SURPRISED`.
- `RenderResult` dataclass.
- `RenderError` exception class.

## What Does NOT Live Here

- The shared Blender subprocess runner — that lives at `src/seidr_smidja/_internal/blender_runner.py` (Decision D-003). The Oracle Eye *uses* the runner but does not own it.
- The Blender build script or any logic that applies parametric changes to the avatar — that is the Forge's `scripts/build_script.py`.
- Compliance evaluation — that is the Gate.
- Spec parsing or validation — that is the Loom.
- Agent protocol handling — that is the Bridges.

---

## Public Interface Entry Points

The full contract is defined in [`INTERFACE.md`](INTERFACE.md). Key signatures:

- `render(vrm_path: Path, output_dir: Path, views: list[RenderView] | None = None) -> RenderResult`
- `list_standard_views() -> list[RenderView]`

Errors: `RenderError` (non-recoverable — renderer not found or output dir unwritable). Renderer subprocess failures return `RenderResult(success=False)` — they are not raised as exceptions.

---

## Dependency Direction

**The Oracle Eye depends only on `_internal/blender_runner.py` and Annáll. It receives its input (`vrm_path`) from the Forge's result — it does not call into Forge directly.**

```
[Bridge Core] --> [Oracle Eye] --> [_internal/blender_runner.py] --> [Blender subprocess]
                  [Oracle Eye] --> (logs to) [Annáll]
```

The Oracle Eye must never import from: Forge, Gate, or Bridges. It must not reach back into the Loom or Hoard.

---

## Render Failure Behavior (Decision D-006)

Render failure is a **soft failure**. If the `.vrm` was successfully produced and validated by the Gate but rendering fails (Blender hung, render script bug, missing GPU), the build still returns the `.vrm` plus a structured warning recording which renders failed and why. The Oracle Eye's failure does not erase the Forge's success.

This aligns with the PHILOSOPHY's "fail loud at the Gate, fail soft inside the Forge" stance. See [docs/DECISIONS/D-006-oracle-eye-render-failure-behavior.md](../../../docs/DECISIONS/D-006-oracle-eye-render-failure-behavior.md).

---

## Sacred Invariant

The Oracle Eye may **never be bypassed** in a compliant build that produces a `.vrm` output. This is Sacred Principle 2: *The Oracle Eye Is Never Closed*. The Bridge Core calls `oracle_eye.render()` unconditionally after every successful Forge build. There is no configuration flag to disable it. Agents that wish to skip renders must pass `render_views=[]` — they may not bypass the call entirely.

---

## Cross-References

- **Philosophy relevance:** [docs/PHILOSOPHY.md §II Principle 2](../../../docs/PHILOSOPHY.md) — "The Oracle Eye Is Never Closed." Sacred infrastructure, not a convenience feature.
- **Data flow relevance:** [docs/DATA_FLOW.md §I Step 6](../../../docs/DATA_FLOW.md) — the Oracle Eye step. The vision feedback loop is diagrammed in `DATA_FLOW.md §VII`.
- **Architecture relevance:** [docs/ARCHITECTURE.md §VII](../../../docs/ARCHITECTURE.md) — process model. The Oracle Eye runs as a second separate Blender subprocess in v0.1.
- **Decisions:** [D-003](../../../docs/DECISIONS/D-003-shared-blender-runner-location.md), [D-006](../../../docs/DECISIONS/D-006-oracle-eye-render-failure-behavior.md), [D-007](../../../docs/DECISIONS/D-007-blender-subprocess-pattern-v0_1.md)
- **Domain Map:** [docs/DOMAIN_MAP.md — Oracle Eye](../../../docs/DOMAIN_MAP.md)

---

*Written by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
