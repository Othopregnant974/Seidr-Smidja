# Loom — Interface Contract
**Last updated:** 2026-05-06
**Domain:** Loom — the Norn-Loom
**Keeper:** Rúnhild Svartdóttir (Architect)

---

## Purpose

The Loom is the parametric avatar specification layer. It owns schema definition, validation, and serialization of `AvatarSpec` objects. It is the sole authority on what constitutes a valid avatar description.

---

## Public Signatures

### `load_and_validate(source: Path | dict) -> AvatarSpec`

Loads an avatar spec from a YAML/JSON file path or a raw dict, validates it against the schema, and returns a typed `AvatarSpec`.

- **Input:** `source` — a `pathlib.Path` pointing to a `.yaml` or `.json` file, or a `dict` containing the spec data.
- **Output:** `AvatarSpec` — a fully validated, typed dataclass.
- **Errors:**
  - `LoomValidationError` — raised if any required field is missing, any field fails type or value constraints, or the `spec_version` is not supported. Always includes a list of `ValidationFailure` objects identifying each failing field and the reason.
  - `LoomIOError` — raised if `source` is a `Path` that cannot be read (file not found, permission error, parse error).

---

### `AvatarSpec.to_yaml() -> str`

Serializes the spec to a YAML string.

- **Input:** None (method on `AvatarSpec` instance).
- **Output:** `str` — valid YAML.
- **Errors:** None raised. Serialization of a validated spec is always possible.

---

### `AvatarSpec.to_json() -> str`

Serializes the spec to a JSON string.

- **Input:** None (method on `AvatarSpec` instance).
- **Output:** `str` — valid JSON.
- **Errors:** None raised.

---

### `AvatarSpec.to_file(path: Path) -> None`

Writes the spec to a file. Format determined by file extension (`.yaml` / `.yml` → YAML, `.json` → JSON).

- **Input:** `path` — a `pathlib.Path` to write to. Parent directory must exist.
- **Output:** None.
- **Errors:**
  - `LoomIOError` — raised on I/O failure (permission, disk full, unknown extension).

---

## Key Data Structures

### `AvatarSpec` (dataclass)

```
spec_version: str               # Semver string, e.g. "1.0"
avatar_id: str                  # Stable unique identifier (slug format)
display_name: str               # Human/agent-readable name
base_asset_id: str              # Key into the Hoard catalog
body: BodySpec                  # Height, proportions, skeletal parameters
face: FaceSpec                  # Eye shape, nose, mouth, bone scale
hair: HairSpec                  # Style, color, physics parameters
outfit: OutfitSpec              # Layers, materials, cloth physics flags
expressions: ExpressionSpec     # Named blendshape targets and values
metadata: AvatarMetadata        # Author, license, copyright, platform tags
extensions: dict[str, Any]      # Opaque — preserved faithfully, never inspected
```

### `LoomValidationError` (exception)

```
message: str
failures: list[ValidationFailure]
    # ValidationFailure has: field_path: str, reason: str, received_value: Any
```

---

## Invariants

1. A `LoomValidationError` is raised for any spec that fails schema validation. Partial `AvatarSpec` objects are never returned.
2. The `extensions` field is always preserved on round-trip serialization, regardless of its contents.
3. The `spec_version` field is always present and matches a supported version string. Unsupported versions raise `LoomValidationError` immediately.
4. No Loom module imports from Forge, Oracle Eye, Gate, Bridges, or Hoard.

---

## Dependencies

- `pydantic` — schema validation
- `pyyaml` — YAML parsing
- `seidr_smidja.annall.port` — for logging validation events (optional, degrades gracefully if Annáll is unavailable)

---

*Rúnhild Svartdóttir, Architect — 2026-05-06*
