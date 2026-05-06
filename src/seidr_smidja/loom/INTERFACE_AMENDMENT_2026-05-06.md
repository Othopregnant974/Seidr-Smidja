# Loom INTERFACE Amendment — 2026-05-06

**Additive amendment to `INTERFACE.md`**
**Reason:** AUDIT-005 — D-005 Option B Annáll injection parity
**Status:** Applied in code as of 2026-05-06

---

## Updated Signature: `load_spec()`

The primary entry point `load_spec()` now accepts two optional dependency-injection
parameters for Annáll logging. These parameters were not present in the original
`INTERFACE.md`.

```python
def load_spec(
    source: Path | dict[str, Any],
    annall: AnnallPort | None = None,
    session_id: str | None = None,
) -> AvatarSpec
```

### Added parameters

| Parameter    | Type                  | Default | Description |
|--------------|-----------------------|---------|-------------|
| `annall`     | `AnnallPort \| None`  | `None`  | Optional Annáll port for structured event logging. |
| `session_id` | `str \| None`         | `None`  | Session ID for the Annáll event. Required if `annall` is provided. |

### Logging behaviour (AUDIT-005 — D-005 Option B)

When both `annall` and `session_id` are provided, `load_spec()` logs a
`loom.validated` event **from within the Loom domain itself** immediately after
successful validation.

**Callers must NOT also log `loom.validated`** to avoid duplicate events.
The Bridge Core (`dispatch.py`) was updated on 2026-05-06 to remove its
Core-side `loom.validated` log call.

Event payload:
```json
{
  "avatar_id": "<spec.avatar_id>",
  "base_asset_id": "<spec.base_asset_id>"
}
```

### Fault isolation

If `annall.log_event()` raises any exception, the exception is silently caught
and the `AvatarSpec` is returned normally. Annáll failure must never crash the Loom.

### Backwards compatibility

Both parameters are optional and default to `None`. Existing callers that do not
pass `annall` or `session_id` are unaffected.

---

## `load_and_validate` alias

The `load_and_validate` alias defined in `INTERFACE.md` remains valid and forwards
to `load_spec` with the same signature (including the new optional parameters).

---

*This amendment is additive. The original `INTERFACE.md` is unchanged.*
