# config/ — Process-Level Configuration
**Keeper:** Forge Worker (Eldra Járnsdóttir) — `defaults.yaml` populated in Phase 5
**Layer:** Infrastructure (configuration loader is Layer 1)

---

## What This Directory Is

The `config/` directory holds YAML configuration files that control process-level behavior: where Blender lives, where the Annáll database is written, what the default output root is, logging levels. This is process configuration — not avatar data (that lives in `data/`) and not agent-facing API parameters (those live in `BuildRequest`).

---

## The Two Files

### `defaults.yaml` — Shipped defaults

The canonical source of truth for all configuration keys and their default values. This file is **shipped with the package** and must never be edited by users or operators. If you want to override a value, use `user.yaml` or an environment variable.

The Forge Worker populates this file in Phase 5. It will contain at minimum:

```yaml
forge:
  blender_path: blender           # Relies on PATH; use BLENDER_PATH env var to override.
  build_timeout_seconds: 300      # Max time to wait for a Blender build subprocess.
  render_timeout_seconds: 180     # Max time to wait for a Blender render subprocess.

annall:
  backend: sqlite
  sqlite:
    db_path: "{output_root}/annall.db"   # Portable; resolves relative to configured output_root.

hoard:
  hoard_root: "{package_root}/assets/hoard"  # Default local Hoard directory.

output:
  output_root: "./seidr_output"   # Default output root for .vrm files and renders.

logging:
  level: INFO
```

### `user.yaml` — User/operator overrides

This file is **gitignored** and created on first run (or manually by the user). It follows the same key structure as `defaults.yaml`. Any key present in `user.yaml` overrides the value in `defaults.yaml`.

Example `user.yaml`:

```yaml
forge:
  blender_path: "C:/Program Files/Blender Foundation/Blender 4.1/blender.exe"

annall:
  sqlite:
    db_path: "D:/seidr_data/annall.db"
```

---

## Layer Order (later layers override earlier)

1. `defaults.yaml` (package defaults — always present)
2. `user.yaml` (user overrides — gitignored, optional)
3. Environment variables with prefix `SEIDR_` (e.g., `SEIDR_BLENDER_PATH`, `SEIDR_OUTPUT_ROOT`)
4. Values passed directly in `BuildRequest.session_metadata` (per-request overrides)

---

## Rules for This Directory

1. **Never edit `defaults.yaml` for personal preferences.** Put overrides in `user.yaml` or use `SEIDR_` environment variables.
2. **Never commit `user.yaml`.** It is gitignored for a reason — it may contain machine-specific paths or secrets.
3. **All path values in config files use forward slashes.** `pathlib.Path` normalizes them on all platforms at parse time.
4. **No avatar data, compliance rules, or spec schemas live here.** Those belong in `data/`. This directory holds only process-level operational settings.

---

## Cross-References

- [`docs/ARCHITECTURE.md §VIII`](../docs/ARCHITECTURE.md) — Configuration Model (full layer order, key naming conventions, config loader location).
- [`docs/ARCHITECTURE.md §V`](../docs/ARCHITECTURE.md) — Blender path resolution priority chain.
- [`src/seidr_smidja/forge/INTERFACE.md`](../src/seidr_smidja/forge/INTERFACE.md) — `resolve_blender_executable()` uses the config layer.
- [`src/seidr_smidja/annall/INTERFACE.md`](../src/seidr_smidja/annall/INTERFACE.md) — Annáll database path comes from config, never hardcoded.

---

*Placeholder written by Eirwyn Rúnblóm, Scribe — 2026-05-06. Forge Worker populates `defaults.yaml` in Phase 5.*
