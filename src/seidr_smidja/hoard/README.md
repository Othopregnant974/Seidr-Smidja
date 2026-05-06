# Hoard — the Asset Hoard
**Domain:** `src/seidr_smidja/hoard/`
**Layer:** 2 — Domain Core
**Keeper:** Rúnhild Svartdóttir (Architect)

---

> *"What the Hoard gives, the Forge transforms."*

---

## True Name and Meaning

The **Hoard** is the dragon's treasury of base materials — the collection of assets the forge draws upon but never alters. In Norse legend, a hoard is accumulated with patience and protected fiercely; it is lent only to those who have earned the trust to use it well. The Forge earns that trust by returning every base asset untouched.

In this system, the Hoard is the library of VRoid Studio template `.vrm` files, hair meshes, outfit meshes, and texture sets. It resolves asset identifiers into filesystem paths and guarantees those files exist at the moment of return. It does not build, transform, or render — it gives. The Forge takes from the Hoard and transforms what it receives.

---

## One-Sentence Purpose

The Hoard owns the catalog and retrieval of static base assets — VRoid template files, hair meshes, outfit meshes, and texture sets — providing a stable `resolve()` interface that returns a guaranteed-present filesystem path, with optional fetch-and-cache for remote assets.

---

## What Lives Here

- `INTERFACE.md` — the public contract (read this before touching any code here).
- Catalog loading logic: reads `data/hoard_catalog.yaml` to build the asset index.
- `resolve(asset_id: str) -> Path` — the primary entry point.
- `list_assets(filter) -> list[AssetMeta]` — for spec-authoring tooling.
- `catalog_path() -> Path` — for diagnostics.
- v0.1 local-only resolution (Decision D-004): checks the configured `hoard_root` directory; raises `AssetNotFoundError` if not present.
- Exception classes: `AssetNotFoundError`, `AssetFetchError` (for future fetch paths), `HoardError`.

## What Does NOT Live Here

- Any modification, transformation, or rendering of assets — the Hoard only lends; it never alters.
- Avatar spec parsing or validation — that is the Loom.
- Blender invocation — that is the Forge.
- Network fetch logic in v0.1 — local-only per Decision D-004. The `resolve()` interface is shaped for a future fetch adapter but v0.1 raises `AssetNotFoundError` for any asset not already present locally.

---

## Public Interface Entry Points

The full contract is defined in [`INTERFACE.md`](INTERFACE.md). Key signatures:

- `resolve(asset_id: str) -> Path` — returns an absolute path to the asset file; file guaranteed to exist.
- `list_assets(filter: AssetFilter | None = None) -> list[AssetMeta]`
- `catalog_path() -> Path`

Errors: `AssetNotFoundError` (asset not in catalog or not locally present), `AssetFetchError` (future), `HoardError` (catalog read failure).

---

## Dependency Direction

**The Hoard depends on Annáll for event logging only.** It has no other dependencies within the forge domain.

```
[Bridge Core] --> [Hoard] --> (logs to) [Annáll]
```

The Hoard must never import from: Loom, Forge, Oracle Eye, Gate, or Bridges.

---

## v0.1 Notes (Decision D-004)

For v0.1, the Hoard is local-only. Assets must be present under `hoard_root` (configured in `config/defaults.yaml`) before a build can proceed. The v0.1 bootstrap script (or manual placement) seeds the directory with the bundled VRoid base templates. The `resolve()` method's shape is already designed to accommodate a future fetch adapter — see [docs/DECISIONS/D-004-hoard-v0_1-local-only.md](../../../docs/DECISIONS/D-004-hoard-v0_1-local-only.md).

---

## Cross-References

- **Philosophy relevance:** [docs/PHILOSOPHY.md §II Principle 3](../../../docs/PHILOSOPHY.md) — "The Loom Before the Hammer." The Hoard is accessed *after* the Loom has validated the spec and identified which `base_asset_id` is required.
- **Data flow relevance:** [docs/DATA_FLOW.md §I Step 4](../../../docs/DATA_FLOW.md) — Hoard resolution is the second step in `dispatch()`. The Hoard branch decision is diagrammed in `DATA_FLOW.md §IV`.
- **Architecture relevance:** [docs/ARCHITECTURE.md §XI point 3](../../../docs/ARCHITECTURE.md) — the future `HoardFetcher` adapter parked for a later phase.
- **Decision:** [docs/DECISIONS/D-004-hoard-v0_1-local-only.md](../../../docs/DECISIONS/D-004-hoard-v0_1-local-only.md)
- **Domain Map:** [docs/DOMAIN_MAP.md — Hoard](../../../docs/DOMAIN_MAP.md)

---

*Written by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
