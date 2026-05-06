# Bridge Core — Interface Amendment
**Amendment date:** 2026-05-06
**Amends:** `INTERFACE.md` (same directory)
**Reason:** Auditor finding AUDIT-002 — implementation signature has two undocumented optional parameters.
**Author:** Sólrún Hvítmynd (Auditor), for Eirwyn Rúnblóm (Scribe) to ratify in Phase 7.

---

## Addendum: Actual `dispatch()` Signature

The implementation signature (confirmed at runtime) is:

```python
def dispatch(
    request: BuildRequest,
    annall: AnnallPort,
    hoard: Any | None = None,
    config: dict[str, Any] | None = None,
) -> BuildResponse:
```

The two additional optional parameters are not present in `INTERFACE.md`. They are:

### `hoard: Any | None = None`
An optional HoardPort instance. If `None`, dispatch constructs a `LocalHoardAdapter` from the `config` dict (or from package defaults if `config` is also `None`).

**Purpose:** Dependency injection for testing. Test suites inject a mock or fixture Hoard to avoid needing a real catalog file. Production callers typically omit this parameter and let dispatch construct the default adapter.

**Type contract:** Must implement the Hoard port protocol — specifically `resolve(asset_id: str) -> Path` and (optionally) `list_assets(...)`.

### `config: dict[str, Any] | None = None`
An optional config dict (as produced by `seidr_smidja.config.load_config()`). Used to:
- Locate the Hoard catalog and bases directory (when `hoard` is `None`).
- Configure the Gate rules directory and VRChat tier target.
- Pass Blender executable path and timeout to the subprocess runner.

If `None`, dispatch resolves configuration from `config/defaults.yaml` and environment variables.

---

## Updated Contract Note

> The INTERFACE.md contract (`dispatch(request, annall)`) describes the *minimum viable* call. Any caller that supplies only `request` and `annall` will receive correct behavior with default configuration and a default LocalHoardAdapter. Callers that need to inject a different Hoard or pass an explicit config should use the full signature.

---

*This amendment is additive. The existing `INTERFACE.md` is not modified.*
*Scribe should fold this into the next INTERFACE.md revision when one is made.*
