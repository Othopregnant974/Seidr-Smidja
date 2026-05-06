# Hoard — Interface Contract
**Last updated:** 2026-05-06
**Domain:** Hoard — the Asset Hoard
**Keeper:** Rúnhild Svartdóttir (Architect)

---

## Purpose

The Hoard is the read-only asset library. It owns catalog management, asset resolution, and fetch/cache behavior for VRoid base templates, hair meshes, outfit meshes, and texture sets. It lends assets to the Forge; it never modifies them.

---

## Public Signatures

### `resolve(asset_id: str) -> Path`

Resolves an asset identifier to an absolute (runtime-resolved) filesystem path, fetching and caching if the asset is not locally present.

- **Input:** `asset_id` — a catalog key string (e.g., `"vroid/tall_feminine_v1"`).
- **Output:** `Path` — absolute path to the asset file on the local filesystem. The file is guaranteed to exist when returned.
- **Errors:**
  - `AssetNotFoundError` — raised if the asset_id is not in the catalog and cannot be fetched. Always includes the `asset_id` and a diagnostic message. Never returns `None`.
  - `AssetFetchError` — raised if the asset is cataloged but the remote fetch fails (network error, checksum mismatch). Includes the `asset_id` and the underlying cause.

---

### `list_assets(filter: AssetFilter | None = None) -> list[AssetMeta]`

Returns the list of assets available in the Hoard, optionally filtered.

- **Input:** `filter` — optional `AssetFilter` dataclass with fields: `asset_type: str | None`, `tags: list[str] | None`. If `None`, all assets are returned.
- **Output:** `list[AssetMeta]` — each entry carries: `asset_id`, `display_name`, `asset_type`, `tags`, `vrm_version`, `cached: bool`.
- **Errors:**
  - `HoardError` — raised on catalog read failure.

---

### `catalog_path() -> Path`

Returns the path to the Hoard's catalog YAML file (for tooling and diagnostics).

- **Input:** None.
- **Output:** `Path`.
- **Errors:** None.

---

## Key Data Structures

### `AssetFilter` (dataclass)

```
asset_type: str | None       # e.g. "vrm_base", "hair_mesh", "outfit_mesh"
tags: list[str] | None       # e.g. ["feminine", "tall", "vroid_default"]
```

### `AssetMeta` (dataclass)

```
asset_id: str
display_name: str
asset_type: str
tags: list[str]
vrm_version: str             # "0.x" or "1.0"
file_size_bytes: int | None
cached: bool                 # True if locally present, False if remote-only
```

### `AssetNotFoundError` (exception)

```
asset_id: str
message: str
```

---

## Invariants

1. `resolve()` never returns a path to a file that does not exist on the filesystem at the moment of return.
2. `resolve()` never modifies any file it returns a path to. The Hoard is read-only during a build.
3. All paths within the Hoard are relative to a configurable `hoard_root` — never hardcoded.
4. Missing assets raise `AssetNotFoundError` immediately — `None` is never returned.

---

## Dependencies

- `seidr_smidja.annall.port` — for cache/fetch event logging

---

*Rúnhild Svartdóttir, Architect — 2026-05-06*
