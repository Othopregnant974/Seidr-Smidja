# Seiðr-Smiðja — Architecture
**Last updated:** 2026-05-06
**Scope:** System-level structural decomposition — layers, patterns, cross-cutting concerns, and design law.
**Keeper:** Rúnhild Svartdóttir (Architect)

---

> *A forge that holds its shape under heat is a forge built with honest bone. The bones of this system are documented here — not because they are fragile, but because every smith who enters should know what they are standing on.*

---

## I. Layered Model

The system is organized in four architectural layers. A layer may only call into layers below it; upward calls are structural failures.

```
┌─────────────────────────────────────────────────────┐
│  LAYER 4 — Bridge Layer                             │
│  Mjöll (MCP) · Rúnstafr (CLI) · Straumur (REST)    │
│  Skills (Hermes / OpenClaw / Claude Code)           │
│  Protocol translation only — no forge logic         │
├─────────────────────────────────────────────────────┤
│  LAYER 3 — Orchestration Layer                      │
│  Bridge Core (Shared Anvil)                         │
│  Owns the pipeline: Loom→Hoard→Forge→Eye→Gate       │
│  Normalizes BuildRequest / BuildResponse            │
├─────────────────────────────────────────────────────┤
│  LAYER 2 — Domain Core                              │
│  Loom · Hoard · Forge · Oracle Eye · Gate           │
│  Each domain owns one pure capability               │
├─────────────────────────────────────────────────────┤
│  LAYER 1 — Adapter / Infrastructure Layer           │
│  Annáll (AnnallPort + SQLiteAnnallAdapter)          │
│  Config loader · Blender subprocess runner          │
│  External storage, external processes               │
└─────────────────────────────────────────────────────┘
```

**The one rule that governs all layers:** A higher layer may call into a lower layer. A lower layer may never call into a higher layer. Layer 1 (Annáll, adapters) is callable by every layer above it.

---

## II. The Bridge Shared Core — Resolving Bridge Drift

### The Problem

Four Bridge sub-forms exist: Mjöll (MCP), Rúnstafr (CLI), Straumur (REST), and Skills (manifests). Without a shared seam, each sub-form will silently accumulate its own interpretation of what a build request means, its own ordering of steps, its own error shapes. Within weeks they will diverge until they are not four doors to the same forge — they are four different forges pretending to be one.

### The Pattern: The Shared Anvil

A single module, `bridges/core/`, owns the one canonical orchestration path. It is named **the Shared Anvil** — the surface every hammer strikes, regardless of which smith is swinging.

Every Bridge sub-module is a thin translation layer, nothing more:

```
[Protocol Input]
       │
       ▼
[Bridge Sub-Module]
  Parses protocol-native input
  Constructs BuildRequest
       │
       ▼
[bridges.core.dispatch(request)]   ← THE ONLY CALL A BRIDGE MAKES INTO THE FORGE
       │
       ▼
[BuildResponse]
       │
       ▼
[Bridge Sub-Module]
  Translates BuildResponse into protocol-native output
       │
       ▼
[Protocol Output]
```

### The `BuildRequest` Model

```python
@dataclass
class BuildRequest:
    spec_source: Path | dict          # YAML file path or raw dict
    base_asset_id: str                # Key into the Hoard catalog
    output_dir: Path                  # Where .vrm and renders go
    render_views: list[str] | None    # None = full standard set
    compliance_targets: list[str] | None  # None = all targets
    session_metadata: dict            # Agent identity, invocation source, etc.
    request_id: str                   # UUID, assigned by the Bridge sub-module
```

### The `BuildResponse` Model

```python
@dataclass
class BuildResponse:
    request_id: str
    success: bool
    vrm_path: Path | None             # None on failure before Forge completes
    render_paths: dict[str, Path]     # {view_name: path}, empty on render failure
    compliance_report: ComplianceReport | None
    annall_session_id: str
    elapsed_seconds: float
    errors: list[BuildError]          # Structured, never bare exceptions
```

### The Pipeline Inside the Core

```python
def dispatch(request: BuildRequest) -> BuildResponse:
    session = annall.open_session(request.session_metadata)
    try:
        spec = loom.load_and_validate(request.spec_source)           # Step 1
        base_path = hoard.resolve(request.base_asset_id)             # Step 2
        forge_result = forge.build(spec, base_path, request.output_dir)  # Step 3
        render_result = oracle_eye.render(                            # Step 4
            forge_result.vrm_path, request.output_dir, request.render_views
        )
        compliance = gate.check(                                      # Step 5
            forge_result.vrm_path, request.compliance_targets
        )
        return BuildResponse(success=compliance.passed, ...)
    except Exception as e:
        annall.log_event(session, AnnallEvent.error(e))
        return BuildResponse(success=False, errors=[BuildError.from_exception(e)], ...)
    finally:
        annall.close_session(session, outcome)
```

Steps 1–5 are fixed and non-skippable. A Bridge that wishes to "skip rendering" must do so by passing `render_views=[]` — it may not bypass the Oracle Eye call entirely, because the pipeline order is an invariant.

---

## III. The Annáll Repository Pattern — Resolving Annáll Calcification

### The Problem

If the SQLite implementation is written directly into the modules that call it, every caller knows the schema. The database tables become part of the public API by accident. Adding a second adapter (Postgres, flat files) requires touching every caller.

### The Pattern: Port and Adapter

The `AnnallPort` is a Python `Protocol` (structural interface) defined in `annall/__init__.py`. It carries exactly five methods (see `DOMAIN_MAP.md`). The `SQLiteAnnallAdapter` in `annall/adapters/sqlite.py` is the first concrete implementation.

```
annall/
├── __init__.py          ← defines AnnallPort (Protocol), AnnallEvent, SessionID, etc.
├── port.py              ← AnnallPort formal definition (importable by all callers)
└── adapters/
    └── sqlite.py        ← SQLiteAnnallAdapter — the only place that knows about SQLite
```

Every caller imports from `seidr_smidja.annall.port` — never from `annall.adapters.sqlite`. The active adapter is injected through the configuration layer at application startup.

### Adapter Selection

```yaml
# config/defaults.yaml
annall:
  backend: sqlite
  sqlite:
    db_path: "{output_root}/annall.db"   # portable, relative to configured output root
```

The `AnnallPort` instance is constructed once at startup and passed as a dependency into the `core.dispatch` function. It is never imported as a global.

---

## IV. The Loom Schema and the `extensions` Field — Resolving Loom Extension Hatch

### The Problem

The Loom spec will eventually serve as the canonical character description for Sigrid (VGSK) and NSE bondmaid avatars. If the schema has no forward-hatch, every cross-project integration will require a schema version bump and a migration.

### The Design

The `AvatarSpec` Pydantic model carries a top-level `extensions` field:

```python
@dataclass
class AvatarSpec:
    # Core fields (required for v0.1 builds)
    spec_version: str                   # e.g. "1.0"
    avatar_id: str
    display_name: str
    base_asset_id: str
    body: BodySpec
    face: FaceSpec
    hair: HairSpec
    outfit: OutfitSpec
    expressions: ExpressionSpec
    metadata: AvatarMetadata            # license, author, copyright
    # Extension hatch (opaque to the Loom in v0.1)
    extensions: dict[str, Any] = field(default_factory=dict)
```

The `extensions` dict is free-form. The Loom validates that it is a dict but does not inspect its contents. Any external system (NSE, VGSK, future projects) may write into a namespaced key:

```yaml
extensions:
  nse:
    bondmaid_id: "astrid"
    personality_profile_ref: "data/characters/astrid.yaml"
  vgsk:
    sigrid_voice_profile: "silvered_soprano"
```

**Critical invariant:** The Loom must round-trip the `extensions` dict faithfully on every serialize/deserialize cycle. It never strips, transforms, or validates the contents of extension namespaces. Cross-project coupling through this field is entirely the responsibility of the external consumer — Seiðr-Smiðja does not depend on those fields and never reads them.

---

## V. Forge Isolation — The Blender Subprocess Pattern

### Why Subprocess, Not Embedded

Blender exposes a Python interpreter that runs inside the Blender process. Embedding Blender as an in-process library is not supported on any platform. The only stable interface is the subprocess pattern:

```
[Forge Python Code]
        │
        │  subprocess.run([
        │      blender_executable,
        │      "--background",
        │      "--python", build_script_path,
        │      "--",               # separator: Blender stops parsing after this
        │      "--spec", spec_json_path,
        │      "--base", base_vrm_path,
        │      "--output", output_dir,
        │  ])
        │
        ▼
[Blender process — isolated, headless]
  Loads build_script.py
  Reads spec and base paths from argv
  Applies transformations via bpy
  Exports .vrm via VRM Add-on
  Exits with code 0 (success) or non-zero (failure)
        │
        │  stdout/stderr captured
        │  exit code checked
        ▼
[ForgeResult returned to Core]
```

### Spec Passing Convention

The spec is serialized to a temporary JSON file before subprocess invocation. The Blender script reads from that file. JSON is preferred over YAML for subprocess boundary crossing because the `json` module is available in all Python environments, including Blender's embedded Python.

### Blender Path Resolution

Priority order (first match wins):
1. Environment variable `BLENDER_PATH` (absolute path, set by user or CI)
2. `config/user.yaml` key `forge.blender_path`
3. `config/defaults.yaml` key `forge.blender_path` (set to `blender` to rely on `PATH`)
4. Platform-specific well-known locations (Windows: `C:\Program Files\Blender Foundation\Blender *\blender.exe`, Linux/macOS: `blender` in `PATH`)

The resolver raises `BlenderNotFoundError` with clear diagnostic text if none of the above resolve. It never hardcodes a single path.

---

## VI. Cross-Platform Stance

Seiðr-Smiðja is **Windows-first in development, Linux and macOS supported in production**. This means:

- All path construction uses `pathlib.Path` — never string concatenation, never `os.path.join` with forward slashes.
- Path separators in config files and YAML specs are always forward-slash (POSIX-style) — `pathlib.Path` normalizes them at parse time.
- No shell-specific features in subprocess calls (no `shell=True` in `subprocess.run` unless explicitly required and documented).
- File system case-sensitivity is always treated as case-sensitive internally, because Linux is case-sensitive and cross-platform portability requires the stricter assumption.
- Platform-specific behavior (Blender executable naming, default config paths) is isolated in `forge/platform.py` — never scattered through shared logic.

---

## VII. Process and Threading Model

```
[Calling Agent Process]
        │  Protocol (MCP / HTTP / CLI stdin)
        ▼
[seidr_smidja Orchestrator Process]
    Single-threaded per build request at v0.1
    Bridge → Core → Loom → Hoard → Annáll (fast, in-process)
        │
        │  subprocess.Popen
        ▼
[Blender subprocess — FORGE]
    Runs until .vrm export complete
    Exit captured by Forge module
        │
        │  subprocess.Popen (second invocation, or same session if feasible)
        ▼
[Blender subprocess — ORACLE EYE]
    Runs until render PNGs complete
    Exit captured by Oracle Eye module
        │
        ▼
[Back in Orchestrator Process]
    Gate runs in-process (parses VRM, applies rules)
    Annáll writes session record
    BuildResponse assembled and returned to Bridge
```

**Future concurrency note:** Concurrent builds (multiple agents submitting simultaneously) will require a task queue in front of the Core. At v0.1, this is not implemented — requests are serialized. The `BuildRequest.request_id` field is already present so that a future queue can correlate requests without redesigning the data model.

---

## VIII. Configuration Model

Configuration is **YAML-only, layered, and location-agnostic**.

```
config/
├── defaults.yaml        ← shipped with the package; never edited by users
├── user.yaml            ← user/operator overrides; gitignored; created on first run
└── README.md            ← explains the layering contract
```

Layer order (later layers override earlier):
1. `defaults.yaml` (package defaults)
2. `user.yaml` (user overrides, if present)
3. Environment variables with prefix `SEIDR_` (e.g., `SEIDR_BLENDER_PATH`)
4. Values passed directly in the `BuildRequest` (per-request overrides)

The configuration loader (`seidr_smidja.config`) resolves all paths relative to either the package root or an explicitly configured `output_root`. It never uses `os.getcwd()` as a default without explicit user consent.

---

## IX. Testing Strategy

### What Is Unit-Testable Without Blender

The following can be tested without any Blender installation:

- **Loom:** Schema validation, serialization, `extensions` round-trip, error cases. Pure Python, no subprocess.
- **Hoard:** Catalog resolution logic, `AssetNotFoundError` cases, cache contract. Can be tested with a fixture asset directory.
- **Gate:** Compliance rule logic given a known `.vrm` fixture. Pure Python VRM parsing.
- **Annáll:** Port contract, `SQLiteAnnallAdapter` against an in-memory SQLite database.
- **Bridge Core:** `dispatch()` logic with all domain dependencies mocked. Contract of `BuildRequest` / `BuildResponse`.
- **Bridge sub-modules:** Protocol parsing and translation against the core mock.

### What Requires Blender

The following require a live Blender executable:

- **Forge:** Any test that actually runs a Blender subprocess.
- **Oracle Eye:** Any test that actually produces rendered PNGs.
- **End-to-end pipeline:** Full `dispatch()` with no mocks.

These tests are marked with the `requires_blender` pytest marker (registered in `pyproject.toml`). They are excluded from the default CI run and enabled only on CI configurations that provision Blender:

```python
@pytest.mark.requires_blender
def test_forge_builds_minimal_spec():
    ...
```

All non-Blender tests must pass on every pull request, on every platform, without any external dependencies beyond Python and the package requirements.

---

## X. Error Handling Philosophy

**Fail loud at the Gate. Fail soft inside the Forge.**

| Layer | Error Behavior |
|---|---|
| **Loom** | Raises `LoomValidationError` immediately on invalid spec. No partial validation. |
| **Hoard** | Raises `AssetNotFoundError` immediately. Never returns `None`. |
| **Forge** | Wraps all subprocess execution in `try/except`. Returns a `ForgeResult` with `success=False` and captured stderr on any Blender failure. Never lets a subprocess exception propagate upward. |
| **Oracle Eye** | Same pattern as Forge. `RenderResult` with `success=False` on any render failure. Forge result is still returned to the caller; a render failure does not erase the `.vrm`. |
| **Gate** | Compliance failures are expressed as `ComplianceReport` data, not exceptions. Internal errors (corrupt VRM, I/O failure) raise `GateError`. |
| **Bridge Core** | Catches all domain exceptions. Always returns a `BuildResponse` — success or failure. The calling Bridge sub-module never receives an unhandled exception from `dispatch()`. |
| **Bridge sub-modules** | Translate `BuildResponse.errors` into their protocol's native error representation. |
| **Annáll** | Swallows all storage errors silently (logged to stderr). Never propagates to callers. |

This philosophy encodes Sacred Law VIII: *No Silent Failures* — every subsystem logs its failures with enough context to diagnose. But it also encodes the forge's resilience promise: the Forge does not crash; it reports and recovers.

---

## XI. Future Considerations (Parked, Not Designed)

These are open tensions noted for downstream phases. They are not architectural decisions yet.

1. **Concurrent build queue:** At v0.1, builds are sequential. A future task queue (e.g., `asyncio` + `concurrent.futures.ProcessPoolExecutor`) would sit between the Bridge layer and the Core. The `BuildRequest.request_id` already supports this.

2. **Rich render pipeline:** The Oracle Eye interface is designed to accommodate a second renderer (`three-vrm` headless browser). When this is added, it becomes a second `AnnallPort`-style adapter behind an `OracleEyePort` interface. The current `oracle_eye.render()` signature is already abstract enough to host this without breaking callers.

3. **Hoard remote fetch:** The `hoard.resolve()` contract accommodates fetch-and-cache, but the v0.1 implementation may be local-only. A future `HoardFetcher` adapter (HTTP, VRoid Hub API) slots in below `resolve()` without changing callers.

4. **Cross-project spec sharing (NSE/VGSK):** The `extensions` field handles this without coupling. No further architecture is required until a concrete consumer exists.

---

*Drawn at the second founding fire, 2026-05-06.*
*Rúnhild Svartdóttir, Architect — for Volmarr Wyrd.*
