# Bridge Core — Interface Contract
**Last updated:** 2026-05-06
**Domain:** Bridge Core — the Shared Anvil
**Keeper:** Rúnhild Svartdóttir (Architect)

---

## Purpose

The Bridge Core (the Shared Anvil) is the single canonical orchestration path shared by all four Bridge sub-forms. It receives a normalized `BuildRequest`, runs the fixed pipeline (Loom → Hoard → Forge → Oracle Eye → Gate), assembles a `BuildResponse`, and returns it. The Core has no awareness of which Bridge called it.

---

## Public Signatures

### `dispatch(request: BuildRequest, annall: AnnallPort) -> BuildResponse`

Executes the full forge pipeline for one build request.

- **Input:**
  - `request` — a `BuildRequest` dataclass (see below).
  - `annall` — a conforming `AnnallPort` instance (injected; never imported as a global).
- **Output:** `BuildResponse` dataclass (see below). Always returned — success or failure. Never raises an unhandled exception to the caller.
- **Errors:** None propagated. All domain-level exceptions are caught, recorded in `BuildResponse.errors`, and the response is returned with `success=False`.

---

## Key Data Structures

### `BuildRequest` (dataclass)

```
spec_source: Path | dict          # YAML file path or raw spec dict
base_asset_id: str                # Hoard catalog key
output_dir: Path                  # Where .vrm and renders are written
render_views: list[str] | None    # None = full standard set
compliance_targets: list[str] | None  # None = all targets
session_metadata: dict            # Agent identity, invocation source, etc.
request_id: str                   # UUID, assigned by the calling Bridge sub-module
```

### `BuildResponse` (dataclass)

```
request_id: str
success: bool
vrm_path: Path | None             # None if Forge did not complete
render_paths: dict[str, Path]     # {view_name: path}; empty on render failure
compliance_report: ComplianceReport | None
annall_session_id: str
elapsed_seconds: float
errors: list[BuildError]          # Structured error list; empty on full success
```

### `BuildError` (dataclass)

```
stage: str           # "loom" | "hoard" | "forge" | "oracle_eye" | "gate" | "core"
error_type: str      # Exception class name
message: str
detail: dict         # Stage-specific diagnostic data
```

---

## Pipeline Contract

The pipeline is executed in this fixed order. No step may be skipped or reordered:

```
1. Loom.load_and_validate(request.spec_source)
2. Hoard.resolve(request.base_asset_id)
3. Forge.build(spec, base_path, request.output_dir)
4. OracleEye.render(forge_result.vrm_path, request.output_dir, request.render_views)
5. Gate.check(forge_result.vrm_path, request.compliance_targets)
```

A failure at any step:
- Is logged to Annáll with the stage name and exception detail.
- Populates `BuildResponse.errors` with a `BuildError` for that stage.
- Sets `BuildResponse.success = False`.
- Does not prevent subsequent steps from running if they can safely proceed (e.g., a render failure does not skip the Gate check if the `.vrm` was produced).

---

## Invariants

1. `dispatch()` always returns a `BuildResponse` — it never propagates an exception to the calling Bridge sub-module.
2. The pipeline order is fixed: Loom → Hoard → Forge → Oracle Eye → Gate. This order encodes the Sacred Principle that the Oracle Eye is never bypassed and compliance is always checked.
3. The Core has zero protocol awareness — it never inspects `request.session_metadata` for protocol-specific values.
4. The `AnnallPort` instance is always passed as a parameter — never imported as a module-level global.

---

## Dependencies

- `seidr_smidja.loom` — spec validation
- `seidr_smidja.hoard` — asset resolution
- `seidr_smidja.forge` — Blender execution
- `seidr_smidja.oracle_eye` — render
- `seidr_smidja.gate` — compliance check
- `seidr_smidja.annall.port` — session and event logging

---

*Rúnhild Svartdóttir, Architect — 2026-05-06*
