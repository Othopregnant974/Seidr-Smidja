# D-004 — Hoard v0.1 Strategy: Local-Only
**Status:** Accepted
**Date:** 2026-05-06
**Deciders:** Volmarr Wyrd, Runa Gridweaver Freyjasdóttir
**Phase:** Genesis (pre–vertical-slice)

---

## Context

The Hoard must resolve a `base_asset_id` (e.g., `"vroid/tall_feminine_v1"`) into an actual filesystem path to a `.vrm` file. There are two viable strategies for v0.1:

**Local-only:** Assets must already be present in a configured `hoard_root` directory on the local filesystem. `hoard.resolve()` checks locally only; raises `AssetNotFoundError` if not present. No HTTP or network calls. Assets are either committed to the repo (small set), provided by a bootstrap script, or placed manually.

**Fetch-and-cache:** `hoard.resolve()` checks locally first; if absent, fetches from a URL or API (e.g., VRoid Hub) and caches locally. Enables first-run auto-download. Requires network access; adds the `AssetFetchError` path and network-related test complexity.

The Cartographer flagged this as Tension T2 in `DATA_FLOW.md §X`, noting that both paths were diagrammed and a clear decision point was drawn.

---

## Decision

**For v0.1, the Hoard is local-only.** Bundled VRoid base templates are committed (or provided by a small bootstrap script) into a known directory tree under `hoard_root`. No remote fetch is performed in v0.1.

**The `resolve()` method interface is designed to accommodate a future fetch-and-cache adapter without breaking callers.** The method signature `resolve(asset_id: str) -> Path` does not change when the fetch path is added — the fetch logic is added below `resolve()` as an internal adapter, invisible to callers.

---

## Consequences

**Local-only makes possible:**
- CI can run Hoard tests without network access. No flaky tests due to remote server availability.
- The vertical slice (Phase 5) can be developed and tested without needing a live external service.
- Deterministic behavior: the same `hoard_root` always produces the same result.

**Local-only constrains:**
- The initial set of base templates must be seeded before a build can proceed. The Forge Worker must create either a `scripts/bootstrap_hoard.py` script or a small committed set of template files.
- `hoard_root` must be configured and populated before the forge is usable in any environment.

**What must be revisited in a later phase:**
- A `HoardFetcher` adapter (HTTP fetch from VRoid Hub, checksum validation, local cache write) is parked as a future enhancement. When implemented, it slots in below `resolve()` without changing any caller. The `AssetFetchError` exception class is already defined in the INTERFACE for this reason.
- Repo size: if base templates are large, they must not be committed to the repo. The bootstrap script approach is preferred. The Forge Worker must make this call during Phase 5.

---

## References

- [`docs/DATA_FLOW.md §IV`](../DATA_FLOW.md) — The Hoard Branch diagram with decision diamond.
- [`docs/DATA_FLOW.md §X Tension T2`](../DATA_FLOW.md) — original tension statement.
- [`src/seidr_smidja/hoard/INTERFACE.md`](../../src/seidr_smidja/hoard/INTERFACE.md) — `resolve()` contract and `AssetFetchError`.
- [`docs/ARCHITECTURE.md §XI point 3`](../ARCHITECTURE.md) — future `HoardFetcher` adapter parked.

---

*Recorded by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
