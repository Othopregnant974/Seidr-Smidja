# Loom — the Norn-Loom
**Domain:** `src/seidr_smidja/loom/`
**Layer:** 2 — Domain Core
**Keeper:** Rúnhild Svartdóttir (Architect)

---

> *"The wyrd is woven before the iron is struck."*

---

## True Name and Meaning

The **Loom** takes its name from the Norn-Loom of Norse mythology — the instrument through which the three Norns (Urðr, Verðandi, Skuld) weave the fate of all living things. Before the iron is struck, before the Blender subprocess opens, before a single vertex moves — the avatar's entire existence is first laid down as a weaving of intent.

The Loom is that act of intention made legible. It receives the agent's vision in YAML or JSON and transforms it into a fully validated, typed `AvatarSpec` — the avatar's *wyrd*, written precisely enough that the Forge can execute it without guessing.

---

## One-Sentence Purpose

The Loom owns the avatar specification schema, its validation logic, and its serialization to and from YAML/JSON — it is the sole authority on what constitutes a valid avatar description.

---

## What Lives Here

- `INTERFACE.md` — the public contract (read this before touching any code here).
- Schema definition for `AvatarSpec` and all its sub-structures (`BodySpec`, `FaceSpec`, `HairSpec`, `OutfitSpec`, `ExpressionSpec`, `AvatarMetadata`).
- Validation logic that raises `LoomValidationError` for any spec that fails requirements — no partial objects, ever.
- Serialization: `AvatarSpec.to_yaml()`, `AvatarSpec.to_json()`, `AvatarSpec.to_file()`.
- The `extensions` dict — an opaque, faithfully round-tripped field for cross-project integration (NSE, VGSK, future consumers).
- `LoomValidationError` and `LoomIOError` exception classes.

## What Does NOT Live Here

- Anything that touches Blender, file system writes to output paths, or render logic — that is the Forge and Oracle Eye.
- Compliance rule evaluation — that is the Gate.
- Asset catalog resolution — that is the Hoard.
- Agent protocol parsing (MCP/CLI/REST) — that is the Bridges.
- Business logic about *which spec values are good aesthetics* — the Loom validates structure and type, not artistic merit.

---

## Public Interface Entry Points

The full contract is defined in [`INTERFACE.md`](INTERFACE.md). Key signatures:

- `load_and_validate(source: Path | dict) -> AvatarSpec` — the primary entry point.
- `AvatarSpec.to_yaml() -> str`
- `AvatarSpec.to_json() -> str`
- `AvatarSpec.to_file(path: Path) -> None`

Errors: `LoomValidationError` (bad spec data), `LoomIOError` (file I/O failure).

---

## Dependency Direction

**The Loom depends on nothing within the forge domain.** It may depend on `pydantic` and `pyyaml` as third-party libraries. It may write to Annáll via `seidr_smidja.annall.port` for validation event logging.

```
[Bridge Core] --> [Loom] --> (logs to) [Annáll]
```

The Loom must never import from: Forge, Oracle Eye, Gate, Bridges, or Hoard.

---

## Cross-References

- **Philosophy relevance:** [docs/PHILOSOPHY.md §II Principle 3](../../../docs/PHILOSOPHY.md) — "The Loom Before the Hammer." Every avatar begins as a parametric specification. No avatar is constructed from ad-hoc code decisions.
- **Data flow relevance:** [docs/DATA_FLOW.md §I Step 3](../../../docs/DATA_FLOW.md) — Loom validation is the first step inside `dispatch()`. A failed `LoomValidationError` stops the pipeline immediately.
- **Architecture relevance:** [docs/ARCHITECTURE.md §IV](../../../docs/ARCHITECTURE.md) — The `extensions` field design and the forward-hatch for cross-project integration.
- **Domain Map:** [docs/DOMAIN_MAP.md — Loom](../../../docs/DOMAIN_MAP.md)

---

*Written by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
