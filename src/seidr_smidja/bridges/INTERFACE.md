# Bridges — Interface Contract
**Last updated:** 2026-05-06
**Domain:** Bridges — the Bifröst Bridges
**Keeper:** Rúnhild Svartdóttir (Architect)

---

## Purpose

The Bridges layer is the agent-facing interface layer — the collection of thin protocol-translation shims that allow any agent to enter the forge through its preferred door. All four Bridge sub-modules (Mjöll, Rúnstafr, Straumur, Skills) call exclusively through `bridges.core.dispatch()`. No Bridge sub-module contains forge logic.

---

## Entry Points

### Mjöll (MCP Bridge)

**Entry:** The MCP server is started as a long-running process. It registers the `seidr_build` tool with the MCP protocol.

**MCP tool signature:**
```
tool: seidr_build
input schema:
    spec: object | string   # inline spec dict or path to spec file
    base_asset_id: string   # Hoard catalog key
    output_dir: string      # path string (portable)
    render_views: [string]  # optional; omit for full standard set
    compliance_targets: [string]  # optional; omit for all targets
output schema:
    success: boolean
    vrm_path: string | null
    render_paths: object    # {view_name: path_string}
    compliance_report: object | null
    session_id: string
    errors: [object]
```

---

### Rúnstafr (CLI Bridge)

**Entry:** `seidr` console script, registered as `seidr_smidja.bridges.runstafr.cli:main`.

**Commands:**
```
seidr build <spec_file> [--base <asset_id>] [--output <dir>]
    [--views <view,...>] [--targets <target,...>]
    Builds an avatar from a spec file. Returns exit code 0 on success.

seidr check <vrm_file> [--targets <target,...>]
    Runs Gate compliance check on an existing .vrm file. Standalone.

seidr list-assets [--type <type>] [--tag <tag>]
    Lists available Hoard assets.

seidr version
    Prints the package version and exits.
```

**Exit codes:**
```
0  — success
1  — build failure (structured output on stdout as JSON)
2  — invalid arguments
3  — internal error
```

---

### Straumur (REST Bridge)

**Entry:** FastAPI application, importable as `seidr_smidja.bridges.straumur.app:app`.

**Endpoints:**
```
POST /build
    Body: BuildRequestBody (JSON matching BuildRequest fields)
    Response 200: BuildResponseBody (JSON matching BuildResponse fields)
    Response 422: validation error
    Response 500: internal error with structured error body

POST /check
    Body: { vrm_path: string, targets: [string] | null }
    Response 200: ComplianceReport (JSON)

GET /assets
    Query: type=string, tag=string
    Response 200: [AssetMeta] (JSON array)

GET /health
    Response 200: { status: "ok", version: string }
```

---

### Skills (Skill Manifests)

**Hermes manifest:** `bridges/skills/hermes_manifest.yaml`
**OpenClaw manifest:** `bridges/skills/openclaw_manifest.yaml`
**Claude Code manifest:** `bridges/skills/claude_code_manifest.yaml` (MCP-based, references Mjöll)

Each manifest declares the skill's invocation schema. The corresponding Python adapter in `bridges/skills/` translates the skill's native invocation format into a `BuildRequest` and calls `bridges.core.dispatch()`.

---

## Invariants

1. Every Bridge sub-module calls only `bridges.core.dispatch(request: BuildRequest) -> BuildResponse`. No sub-module imports from Loom, Hoard, Forge, Oracle Eye, Gate, or Annáll directly.
2. Protocol-specific logic (MCP framing, CLI argument parsing, HTTP routing, skill YAML schemas) is confined entirely within the Bridge sub-module and never leaks into the Core.
3. A `BuildRequest` constructed by any Bridge must be semantically equivalent to the same logical request arriving through any other Bridge.
4. No Bridge sub-module catches exceptions from `bridges.core.dispatch()` other than `BuildResponse` errors — the Core guarantees a `BuildResponse` is always returned.

---

## Dependencies

- `bridges.core` — the only forge domain any Bridge sub-module calls into
- `seidr_smidja.loom` — for spec parsing from raw protocol input (Bridges may call `loom.load_and_validate` to validate user-provided specs before dispatching)
- `seidr_smidja.annall.port` — for request/response logging

---

*Rúnhild Svartdóttir, Architect — 2026-05-06*
