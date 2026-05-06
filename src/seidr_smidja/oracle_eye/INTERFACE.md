# Oracle Eye — Interface Contract
**Last updated:** 2026-05-06
**Domain:** Oracle Eye — Óðins-Auga
**Keeper:** Rúnhild Svartdóttir (Architect)

---

## Purpose

The Oracle Eye is the render and vision feedback layer. Given a `.vrm` file, it produces a standard set of preview PNG images through a headless renderer (Blender Eevee in v0.1, extensible to others). These images are returned to the calling agent so it may see what it has made.

The Oracle Eye is never disabled in a compliant build — this is Sacred Principle 2.

---

## Public Signatures

### `render(vrm_path: Path, output_dir: Path, views: list[RenderView] | None = None) -> RenderResult`

Renders one or more standard preview views of the given `.vrm` file.

- **Input:**
  - `vrm_path` — absolute path to the `.vrm` file to render. Must exist.
  - `output_dir` — directory where rendered PNGs will be written. Must exist.
  - `views` — optional list of `RenderView` values. If `None`, the full standard set is rendered (front, three_quarter, side, face_closeup, t_pose, expression_smile, expression_sad, expression_surprised).
- **Output:** `RenderResult` dataclass (see below).
- **Errors:**
  - `RenderError` — raised only on non-recoverable internal failure (renderer executable not found, output directory not writable). A renderer subprocess failure is expressed as a `RenderResult` with `success=False`.

---

### `list_standard_views() -> list[RenderView]`

Returns the canonical list of standard render views in their standard order.

- **Input:** None.
- **Output:** `list[RenderView]`.
- **Errors:** None.

---

## Key Data Structures

### `RenderView` (enum)

```
FRONT
THREE_QUARTER
SIDE
FACE_CLOSEUP
T_POSE
EXPRESSION_SMILE
EXPRESSION_SAD
EXPRESSION_SURPRISED
```

The enum is open to extension (future expression targets) without breaking existing callers.

### `RenderResult` (dataclass)

```
success: bool
render_paths: dict[str, Path]    # {view_name_string: path_to_png}; empty on failure
renderer_used: str               # e.g. "blender_eevee", "three_vrm" (future)
resolution: tuple[int, int]      # (width, height) in pixels
elapsed_seconds: float
errors: list[str]                # Human-readable error messages if success=False
```

### `RenderError` (exception)

```
message: str
cause: Exception | None
```

---

## Invariants

1. The Oracle Eye may never be bypassed in a compliant build that produces a `.vrm` (Sacred Principle 2). The Bridge Core calls `oracle_eye.render()` unconditionally after every successful Forge build.
2. All rendered PNGs are written to `output_dir` — never to any hardcoded path.
3. The `RenderView` enum and `RenderResult.render_paths` keys do not embed renderer-specific names. A future second renderer uses the same view names.
4. A `RenderResult` is always returned for any render attempt — the only exception raised is when the renderer itself cannot be found or started.

---

## Dependencies

- `seidr_smidja.annall.port` — render event logging

---

*Rúnhild Svartdóttir, Architect — 2026-05-06*
