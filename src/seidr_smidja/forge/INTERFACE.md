# Forge — Interface Contract
**Last updated:** 2026-05-06
**Domain:** Forge — the Smiðja
**Keeper:** Rúnhild Svartdóttir (Architect)

---

## Purpose

The Forge is the headless Blender execution layer. It translates a validated `AvatarSpec` and a resolved base asset path into a `.vrm` output file by launching Blender as a subprocess, injecting the build script, and collecting the result. This is where specification becomes mesh, weight, bone, and material.

---

## Public Signatures

### `build(spec: AvatarSpec, base_asset: Path, output_dir: Path) -> ForgeResult`

Launches a headless Blender subprocess, applies the parametric spec to the base asset, and exports a `.vrm` file to the output directory.

- **Input:**
  - `spec` — a validated `AvatarSpec` from the Loom.
  - `base_asset` — an absolute path to the base `.vrm` file, resolved by the Hoard.
  - `output_dir` — a `pathlib.Path` to the directory where the output `.vrm` will be written. Directory must exist before this call.
- **Output:** `ForgeResult` dataclass (see below).
- **Errors:**
  - `ForgeBuildError` — raised only on non-recoverable internal failure (e.g., Blender executable not found, output directory not writable). A Blender subprocess failure (non-zero exit code) is expressed as a `ForgeResult` with `success=False`, not as a raised exception.

---

### `resolve_blender_executable() -> Path`

Resolves the path to the Blender executable using the priority chain: `BLENDER_PATH` env var → `config/user.yaml` → `config/defaults.yaml` → platform well-known locations.

- **Input:** None.
- **Output:** `Path` — the resolved executable path.
- **Errors:**
  - `BlenderNotFoundError` — raised if no executable can be found. Includes a diagnostic listing all locations checked.

---

## Key Data Structures

### `ForgeResult` (dataclass)

```
success: bool
vrm_path: Path | None        # Path to the output .vrm file; None if success=False
exit_code: int               # Blender subprocess exit code
stderr_capture: str          # Full captured stderr from the Blender process
stdout_capture: str          # Full captured stdout from the Blender process
blender_script_path: Path    # The script injected into Blender (for diagnostics)
elapsed_seconds: float
```

### `ForgeBuildError` (exception)

```
message: str
cause: Exception | None
```

### `BlenderNotFoundError` (exception)

```
message: str
locations_checked: list[str]
```

---

## Invariants

1. Blender is always invoked as a subprocess — never in-process. Isolation is non-negotiable.
2. The Blender executable path is always resolved through the configuration priority chain, never hardcoded.
3. Every Blender subprocess invocation is logged to Annáll with its full argument list, exit code, and captured output.
4. A `ForgeResult` is always returned for any Blender invocation — success or failure. The only time `ForgeBuildError` is raised is when the invocation itself cannot begin (executable missing, output dir unwritable).
5. The spec is passed to the Blender subprocess as a temporary JSON file — never as inline arguments.
6. The Forge does not call into Oracle Eye, Gate, or any Bridge.

---

## Dependencies

- `seidr_smidja.loom` — consumes `AvatarSpec`
- `seidr_smidja.annall.port` — build event logging

---

*Rúnhild Svartdóttir, Architect — 2026-05-06*
