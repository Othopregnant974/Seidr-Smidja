# Forge — the Smiðja
**Domain:** `src/seidr_smidja/forge/`
**Layer:** 2 — Domain Core
**Keeper:** Rúnhild Svartdóttir (Architect)

---

> *"Intention made solid."*

---

## True Name and Meaning

The **Forge** — *Smiðja* in Old Norse — is the place of transformation. In the ancient world, the smith held a role apart from other craftspeople: she worked with materials at the threshold of chaos (liquid metal, extreme heat) and imposed form upon them through will, precision, and deep craft knowledge. What entered as ore or ingot left as blade, shield, or ornament.

In this system, the Forge is that act of transformation. A validated `AvatarSpec` and a base `.vrm` file enter. A new `.vrm` — shaped precisely to the spec's parametric description — leaves. The Forge achieves this by opening Blender in headless mode as a subprocess, injecting the build script, and collecting the result. It does not create the spec (that is the Loom), fetch the base (that is the Hoard), or render images (that is the Oracle Eye). It transforms.

---

## One-Sentence Purpose

The Forge owns all headless Blender subprocess orchestration for the avatar build step — launching Blender, injecting the build script with the spec and base asset, capturing the result, and returning a `ForgeResult` to the caller.

---

## What Lives Here

- `INTERFACE.md` — the public contract (read this before touching any code here).
- `build(spec, base_asset, output_dir) -> ForgeResult` — the primary entry point.
- `resolve_blender_executable() -> Path` — the priority-chain resolver.
- `scripts/build_script.py` — the Blender Python script injected into the headless Blender subprocess. Reads spec from a temp JSON file via `argv`, applies transformations via `bpy`, exports `.vrm` via the VRM Add-on for Blender.
- Error classes: `ForgeBuildError`, `BlenderNotFoundError`.

## What Does NOT Live Here

- The shared Blender subprocess runner — that lives at `src/seidr_smidja/_internal/blender_runner.py` (Decision D-003). The Forge *uses* the runner but does not own it.
- Avatar spec parsing — that is the Loom. The Forge receives a fully validated `AvatarSpec`.
- Asset catalog resolution — that is the Hoard. The Forge receives an already-resolved `Path`.
- Render camera setup and PNG production — that is the Oracle Eye. The Forge only exports a `.vrm`.
- Compliance validation — that is the Gate.
- Agent protocol handling — that is the Bridges.

---

## Public Interface Entry Points

The full contract is defined in [`INTERFACE.md`](INTERFACE.md). Key signatures:

- `build(spec: AvatarSpec, base_asset: Path, output_dir: Path) -> ForgeResult`
- `resolve_blender_executable() -> Path`

Errors: `ForgeBuildError` (non-recoverable — executable missing, output dir unwritable), `BlenderNotFoundError`. Blender subprocess failures return `ForgeResult(success=False)` — they are not raised as exceptions.

---

## Dependency Direction

**The Forge depends on the Loom (consumes `AvatarSpec`) and on `_internal/blender_runner.py` (shared subprocess runner). It logs to Annáll.**

```
[Bridge Core] --> [Forge] --> [_internal/blender_runner.py] --> [Blender subprocess]
                 [Forge] --> (logs to) [Annáll]
```

The Forge must never import from: Oracle Eye, Gate, or Bridges. It does not call into Hoard — it receives the resolved path from the caller.

---

## Blender Subprocess Pattern

The Forge serializes the `AvatarSpec` to a temporary JSON file, then calls:

```
blender --background --python scripts/build_script.py -- --spec <tmp.json> --base <base.vrm> --output <dir>
```

Blender exits with code 0 on success or non-zero on failure. The Forge captures stdout/stderr and always returns a `ForgeResult` — it never lets a subprocess exception propagate upward. See [docs/ARCHITECTURE.md §V](../../../docs/ARCHITECTURE.md) for the full subprocess pattern.

The Blender executable is resolved through the priority chain: `BLENDER_PATH` env var → `config/user.yaml` → `config/defaults.yaml` → platform well-known locations. Never hardcoded. See [docs/DECISIONS/D-007-blender-subprocess-pattern-v0_1.md](../../../docs/DECISIONS/D-007-blender-subprocess-pattern-v0_1.md).

---

## Cross-References

- **Philosophy relevance:** [docs/PHILOSOPHY.md §III Sacred Law I](../../../docs/PHILOSOPHY.md) — No Hardcoded Wyrd. All settings (Blender path, output paths) through config. [Law VIII](../../../docs/PHILOSOPHY.md) — No Silent Failures. Every Blender invocation logged.
- **Data flow relevance:** [docs/DATA_FLOW.md §I Step 5](../../../docs/DATA_FLOW.md) — the Forge step in the Primary Rite. Failure C is the Blender crash failure path.
- **Architecture relevance:** [docs/ARCHITECTURE.md §V](../../../docs/ARCHITECTURE.md) — full Forge Isolation documentation.
- **Decisions:** [D-003](../../../docs/DECISIONS/D-003-shared-blender-runner-location.md), [D-007](../../../docs/DECISIONS/D-007-blender-subprocess-pattern-v0_1.md)
- **Domain Map:** [docs/DOMAIN_MAP.md — Forge](../../../docs/DOMAIN_MAP.md)

---

*Written by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
