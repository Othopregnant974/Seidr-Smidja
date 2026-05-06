# Hoard INTERFACE Amendment — 2026-05-06

**Additive amendment to `INTERFACE.md`**
**Reason:** AUDIT-005 — D-005 Option B Annáll injection parity
**Status:** Applied in code as of 2026-05-06

---

## Updated Signatures: `LocalHoardAdapter.resolve()` and `LocalHoardAdapter.list_assets()`

Both public methods of `LocalHoardAdapter` now accept two optional dependency-injection
parameters for Annáll logging. These parameters were not present in the original
`INTERFACE.md`.

---

### `resolve()`

```python
def resolve(
    self,
    asset_id: str,
    annall: AnnallPort | None = None,
    session_id: str | None = None,
) -> Path
```

#### Added parameters

| Parameter    | Type                  | Default | Description |
|--------------|-----------------------|---------|-------------|
| `annall`     | `AnnallPort \| None`  | `None`  | Optional Annáll port for structured event logging. |
| `session_id` | `str \| None`         | `None`  | Session ID for the Annáll event. Required if `annall` is provided. |

#### Logging behaviour (AUDIT-005 — D-005 Option B)

When both `annall` and `session_id` are provided, `resolve()` logs a
`hoard.resolved` event **from within the Hoard domain itself** immediately after
successfully resolving the asset path.

**Callers must NOT also log `hoard.resolved`** to avoid duplicate events.
The Bridge Core (`dispatch.py`) was updated on 2026-05-06 to remove its
Core-side `hoard.resolved` log call.

Event payload:
```json
{
  "asset_id": "<asset_id>",
  "path": "<resolved absolute path>"
}
```

---

### `list_assets()`

```python
def list_assets(
    self,
    filter: AssetFilter | None = None,
    annall: AnnallPort | None = None,
    session_id: str | None = None,
) -> list[AssetMeta]
```

#### Added parameters

Same `annall` and `session_id` optional parameters as `resolve()`.

When both are provided, `list_assets()` logs a `hoard.listed` event on completion.

Event payload:
```json
{
  "count": <number of assets returned>,
  "filter": "<str(filter)>"
}
```

---

## Fault isolation

If `annall.log_event()` raises any exception, the exception is silently caught and
the return value is returned normally. Annáll failure must never crash the Hoard.

## Backwards compatibility

All new parameters are optional and default to `None`. Existing callers are unaffected.

---

*This amendment is additive. The original `INTERFACE.md` is unchanged.*
