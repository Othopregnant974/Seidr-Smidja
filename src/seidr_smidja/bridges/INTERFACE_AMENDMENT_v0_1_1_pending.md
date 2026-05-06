# Bridges — Interface Amendment v0.1.1 (pending)
**Amendment date:** 2026-05-06
**Amends:** `INTERFACE.md` (same directory)
**Reason:** H-022 (seidr list-assets CLI command implementation) + H-023 (seidr bootstrap-hoard documentation gap).
**Status:** PENDING — awaiting Phase C Auditor verification. Scribe will fold into canonical INTERFACE.md on ratification.
**Author:** Eldra Járnsdóttir (Forge Worker), Hardening Phase B.

---

## New Command: `seidr list-assets` (H-022)

This command was documented in `INTERFACE.md` but was not implemented in the CLI.
It is now implemented in `bridges/runstafr/cli.py` as `cmd_list_assets`.

### Contract

```
seidr list-assets [OPTIONS]
```

**Purpose:** List available base assets in the Hoard catalog. Equivalent to `GET /v1/assets` on the Straumur REST bridge.

**Options:**
| Option | Type | Default | Description |
|---|---|---|---|
| `--type <type>` | string | None | Filter by asset_type (e.g. `vrm_base`) |
| `--tag <tag>` | string | None | Filter by tag (e.g. `feminine`) |
| `--json` | flag | False | Output results as JSON array |
| `--config <path>` | string | None | Path to override config YAML |

**Exit codes:**
| Code | Meaning |
|---|---|
| 0 | Success — assets listed (may be empty list) |
| 1 | Error — catalog could not be read or other failure |

**JSON output shape (per asset):**
```json
{
  "asset_id": "vroid/sample_a",
  "display_name": "VRM Sample Avatar A",
  "asset_type": "vrm_base",
  "tags": ["feminine", "sample"],
  "vrm_version": "0.0",
  "file_size_bytes": 1234567,
  "cached": true
}
```

**Human-readable output shape:**
```
Hoard assets (2 found):
  vroid/sample_a  (VRM Sample Avatar A)  VRM 0.0  [cached]  tags: feminine, sample
  vroid/sample_b  (VRM Sample Avatar B)  VRM 0.0  [not cached]  tags: masculine, sample
```

**Side effects:** None. `list-assets` is a pure read operation on the catalog.

**Implementation file:** `src/seidr_smidja/bridges/runstafr/cli.py` — `cmd_list_assets`

---

## Documented Command: `seidr bootstrap-hoard` (H-023)

This command was implemented but undocumented in `INTERFACE.md`. Contract is hereby established.

### Contract

```
seidr bootstrap-hoard [OPTIONS]
```

**Purpose:** Download seed VRM base assets into the Hoard (`data/hoard/bases/`).
Updates `data/hoard/catalog.yaml` with sha256 hashes and `cached: true` flags.

**Seed assets downloaded:**
- `vroid/sample_a` — VRM Sample Avatar A (CC0-1.0, VRM Consortium)
- `vroid/sample_b` — VRM Sample Avatar B (CC0-1.0, VRM Consortium)

**Options:**
| Option | Type | Default | Description |
|---|---|---|---|
| `--force` | flag | False | Re-download even if file already exists in bases/ |
| `--config <path>` | string | None | Path to override config YAML |

**Exit codes:**
| Code | Meaning |
|---|---|
| 0 | All assets successfully cached |
| 1 | One or more assets failed to download |

**Side effects:**
- Creates `data/hoard/bases/` if it does not exist.
- Downloads VRM files from GitHub CDN URLs (requires internet access).
- Writes/updates `data/hoard/catalog.yaml` with sha256 + cached=true entries.
- Logs warnings for any assets with no expected_sha256 pinned value.
- If `expected_sha256` is set in `_BOOTSTRAP_ASSETS` and download hash mismatches, the downloaded file is deleted and the asset is marked as failed.

**Implementation file:** `src/seidr_smidja/bridges/runstafr/cli.py` — `cmd_bootstrap_hoard`
**Logic file:** `src/seidr_smidja/hoard/bootstrap.py` — `run_bootstrap()`

---

## H-004: `POST /v1/inspect` Path Validation

The Straumur REST endpoint `POST /v1/inspect` now validates the `vrm_path` field before
attempting to open it. Contract update:

**Validation rules (additive to prior contract):**
1. `vrm_path` must end in `.vrm` (case-insensitive). Returns HTTP 400 if not.
2. Resolved path must be inside an allow-listed directory tree:
   - `<project_root>/<output.root>/` (default: `output/`)
   - `<project_root>/<hoard.bases_dir>/` (default: `data/hoard/bases/`)
   - Any additional paths in `config.straumur.inspect_roots` (list)
3. Returns HTTP 400 with structured error body if path fails either check.

**HTTP 400 error body shape:**
```json
{
  "error": "vrm_path_not_allowed",
  "message": "vrm_path must be inside the configured output or hoard directories."
}
```

---

## H-005: Straumur Default Bind Address

The Straumur REST bridge `__main__` block now defaults to `127.0.0.1` (localhost only).

**Operator configuration:**
- `SEIDR_STRAUMUR_HOST` env var: override bind host
- `SEIDR_STRAUMUR_PORT` env var: override bind port (default: 8765)
- `straumur.allow_remote_bind: true` in `config/user.yaml`: required to permit non-localhost binding

If `SEIDR_STRAUMUR_HOST` is set to a non-localhost value AND `allow_remote_bind` is not `true`,
the server refuses to start with a clear error message.

---

*This amendment is additive. The existing `INTERFACE.md` is not modified.*
*The existing `INTERFACE_AMENDMENT_2026-05-06.md` is not modified.*
*Scribe should fold all amendments into the next INTERFACE.md revision when scheduled.*
