# AUDIT_GENESIS — Seiðr-Smiðja Genesis Audit
**Date:** 2026-05-06
**Scope:** Full vertical slice (Phase 5 Forge Worker output). All commits on branch `development` as of 2026-05-06.
**Auditor:** Sólrún Hvítmynd (Auditor role)
**Commands run:**
- `python -m pytest -m "not requires_blender" -v` — 134 passed, 1.68s
- `python -m pytest -m "not requires_blender" --co -q` — no skip/xfail in collection
- Static grep/read analysis across `src/seidr_smidja/**/*.py`, `data/gate/*.yaml`, `tests/**/*.py`, all `docs/*.md`, all `src/**/INTERFACE.md`, and all ADRs D-001..D-007
**Environment:** Python 3.10.11, pytest-9.0.2, Windows 11 (win32), branch: development
**Reference documents read:** TASK, SYSTEM_VISION, PHILOSOPHY, DOMAIN_MAP, ARCHITECTURE, DATA_FLOW, D-001..D-007, all 8 INTERFACE.md files

---

## Summary Verdict

**PASS WITH CONCERNS**

The vertical slice is structurally honest: the pipeline wires correctly, the sacred principles are substantially honored, no GUI code exists, no domain reaches upward in the dependency law, AnnallPort is injected, soft render failure is correctly implemented, and all 134 non-Blender tests pass at the claimed count and timing. However, three medium-severity findings require correction before v0.1 is tagged, and one notable documentation drift is confirmed and must be corrected additively.

---

## Section A — Verification of Claims

| Forge Worker Claim | Status | Evidence |
|---|---|---|
| 134 non-Blender pytest tests passing | **VERIFIED** | `pytest -m "not requires_blender"`: `134 passed in 1.68s` (run confirmed personally, not inferred) |
| All seven ratified decisions D-001..D-007 honored in code | **PARTIAL** | D-003 (runner at `_internal/`) ✓, D-004 (local-only hoard) ✓, D-005 (injection) ✓, D-006 (soft render fail) ✓, D-007 (two subprocesses) ✓, D-001 (Path B, name) ✓. D-002 (repo/branch) is a repo-level, not code-level, decision — unverifiable from code. See AUDIT-006 for partial honor on D-005. |
| `_internal/blender_runner.py` shared between Forge and Oracle Eye | **VERIFIED** | `forge/runner.py:23`: `from seidr_smidja._internal.blender_runner import ...`; `oracle_eye/eye.py:18`: `from seidr_smidja._internal.blender_runner import BlenderNotFoundError, run_blender`. Neither imports from the other. |
| AnnallPort threaded through `dispatch()` to every domain | **PARTIAL** | `dispatch()` signature verified: `(request, annall, hoard=None, config=None)`. AnnallPort injected as parameter at `dispatch.py:86`. Domains receive `annall` as kwarg in each call (`forge/runner.py:66`, `oracle_eye/eye.py:84`, `gate/gate.py:237`). However, `loom/loader.py` and `hoard/local.py` do NOT receive `annall` as parameter — they accept no Annáll parameter at all in their public call signatures. The Core logs Loom and Hoard events itself inline. This is Option A (Core-only logging) for those two domains, contradicting D-005's stated confirmation of Option B for all five domains. See AUDIT-005. |
| Soft render failure returns `.vrm` + warnings | **VERIFIED** | `dispatch.py:244-281`: Oracle Eye exception is caught, VRM path is not cleared, Gate still executes after render failure. `test_dispatch_smoke.py::test_oracle_eye_failure_is_soft` confirms this path. D-006 honored. |
| Two separate Blender subprocesses for build vs render | **VERIFIED** | `forge/runner.py` calls `run_blender(script_path=_BUILD_SCRIPT, ...)`. `oracle_eye/eye.py` calls `run_blender(script_path=_RENDER_SCRIPT, ...)`. Two distinct script files, two distinct invocations. D-007 honored. |
| Local-only Hoard with bootstrap script for sample VRMs | **VERIFIED** | `hoard/local.py` exists; `hoard/bootstrap.py` exists; `seidr bootstrap-hoard` CLI command wired at `cli.py:288`. D-004 honored. |
| Compliance rules loaded from `data/gate/*.yaml` | **VERIFIED** | `gate/gate.py:32`: `_DEFAULT_RULES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "gate"`. Both `data/gate/vrchat_rules.yaml` and `data/gate/vtube_rules.yaml` present and non-empty. No rules hardcoded in Python beyond routing logic. |
| All four Bridges wired through the Shared Anvil | **VERIFIED** | Mjöll (`server.py:190`): `response = dispatch(request, annall, config=cfg)`. Rúnstafr (`cli.py:154`): `response = dispatch(request, annall, config=config)`. Straumur (`api.py:153`): `response = dispatch(request, annall, config=cfg)`. Skills (YAML manifests + SKILL.md): route through `seidr` CLI → Rúnstafr → dispatch. All four converge on `bridges.core.dispatch`. |
| All four skill manifests written (Hermes, OpenClaw, Claude Code) | **PARTIAL** | Hermes: `bridges/skills/hermes/manifest.yaml` ✓. OpenClaw: `bridges/skills/openclaw/manifest.yaml` ✓. Claude Code: `bridges/skills/claude_code/SKILL.md` ✓ (markdown doc, not a YAML manifest). No `claude_code_manifest.yaml` file exists. The BRIDGES INTERFACE.md lists `bridges/skills/claude_code/manifest.yaml` as the expected file. SKILL.md serves the same purpose but the name deviates from the documented contract. See AUDIT-007. Additionally, no fourth manifest is implied; the spec says three agents + manifests = three files, which is consistent, but the document naming diverges. |

---

## Section B — Invariant Audit

### Sacred Principle 1 — Agent Is the Smith (No Human GUI)

**VERIFIED — no violation.**

Grep across all `src/seidr_smidja/**/*.py` for `tkinter`, `PyQt`, `PyGTK`, `wx.`, `kivy`: **zero matches**.

All entry points are programmatic: `seidr` CLI (click-based, no TUI/GUI), Mjöll MCP server, Straumur FastAPI REST server, skill YAML manifests. Sacred Law IX upheld.

---

### Sacred Principle 2 — Oracle Eye Is Never Closed

**VERIFIED — no bypass path found.**

`dispatch.py:244`: Oracle Eye render is called unconditionally after every successful Forge build. No `--skip-renders` flag, no `render_views=[]` bypass — the Forge Worker correctly noted in ARCHITECTURE.md §II that passing `render_views=[]` is the permitted "skip" mechanism (empty list, not a bypass of the call itself). The pipeline order Loom → Hoard → Forge → Oracle Eye → Gate is fixed and non-skippable.

Grep for `skip_renders`, `skip_render`, `skip.*oracle`, `oracle.*skip` across `src/`: zero matches. Sacred Law III upheld.

---

### Sacred Principle 3 — Loom Before the Hammer

**VERIFIED — no avatar data hardcoded in Python source.**

`schema.py` contains only schema definitions (Pydantic field constraints). No avatar body data, no bone names, no VRoid-specific constants. Default color values (`RGBColor(r=0.3, g=0.5, b=0.8)` for eye color, `RGBColor(r=0.1, g=0.07, b=0.05)` for hair) are schema defaults in YAML-serializable models, not hardcoded avatar data — this is acceptable as it represents the starting point for field defaults, not a fixed avatar definition.

Gate rules are in `data/gate/*.yaml` as required. Hoard catalog would be in `data/hoard/catalog.yaml` (bootstrap script produces this). Sacred Law I upheld.

---

### Sacred Principle 4 — Same Language Through Every Door

**VERIFIED.**

All three active Bridge implementations (Mjöll/server.py, Rúnstafr/cli.py, Straumur/api.py) construct a `BuildRequest` and call `dispatch(request, annall, config=cfg)`. Response fields are serialized to protocol-native formats but originate from the same `BuildResponse` structure. Semantic equivalence confirmed by inspection.

---

### Sacred Law V — Annáll Records Everything

**PARTIAL — finding AUDIT-005.**

The Core logs Loom and Hoard events on domains' behalf (Core-side logging, Option A). Forge, Oracle Eye, and Gate each receive `annall` as a parameter and log independently (Option B). The inconsistency is documented below as AUDIT-005.

---

### Sacred Law — Fail Loud at the Gate, Fail Soft in the Forge

**VERIFIED.**

Gate: `gate/gate.py:263-273`: `GateError` raised on corrupt VRM or missing file. Compliance failures returned as `ComplianceReport(passed=False)` — never as exceptions. Confirmed by `test_gate.py::test_check_returns_report_always`.

Forge: `forge/runner.py:162-176`: `BlenderNotFoundError` and `OSError` on launch failure raise `ForgeBuildError`. Blender subprocess failure (non-zero exit) returns `ForgeResult(success=False)` — no exception propagated. Confirmed by `test_dispatch_smoke.py::test_response_always_returned_never_raises`.

---

## Section C — Dependency Law Audit

Static import analysis conducted via grep across all domain directories.

| Check | Result |
|---|---|
| `forge/` imports from `bridges` | No match |
| `forge/` imports from `oracle_eye` | No match |
| `forge/` imports from `gate` | No match |
| `oracle_eye/` imports from `forge` | No match |
| `oracle_eye/` imports from `gate` | No match |
| `oracle_eye/` imports from `bridges` | No match |
| `loom/` imports from `forge`, `oracle_eye`, `gate`, `bridges`, `hoard` | No match |
| `hoard/` imports from `forge`, `oracle_eye`, `gate`, `bridges` | No match |
| `gate/` imports from `forge`, `oracle_eye`, `loom`, `hoard`, `bridges` | No match |
| `annall/` imports from any forge domain | No match |

**Dependency law: CLEAN.** No forbidden import direction found. Both `forge/` and `oracle_eye/` correctly share `_internal.blender_runner` without importing from each other.

---

## Section D — Interface Conformance Audit

### Loom INTERFACE.md

Documented: `load_and_validate(source: Path | dict) -> AvatarSpec`
Actual: `loom/loader.py` exports `load_spec(source)` as the public function; `load_and_validate` is also exported as an alias via `__init__.py`.

**FINDING AUDIT-001 (Low):** INTERFACE.md lists `AvatarSpec.to_file(path: Path) -> None`. `schema.py` implements `to_file`. INTERFACE also lists `spec.from_file(path)` in the DOMAIN_MAP.md description (`spec.from_file(path)`) but this is not in INTERFACE.md and is not a method on the model (loading is via `load_spec`). The DOMAIN_MAP text is slightly misleading. No functional breakage — the implemented interface matches what INTERFACE.md documents for the methods listed there.

The `load_and_validate` function documented in INTERFACE.md is exposed as an alias; the primary implementation name is `load_spec`. This is a naming drift worth documenting additively. Recommended: `INTERFACE_AMENDMENT_2026-05-06.md` noting the implementation uses `load_spec` as the primary name with `load_and_validate` as alias.

---

### Bridge Core INTERFACE.md

Documented: `dispatch(request: BuildRequest, annall: AnnallPort) -> BuildResponse`
Actual (confirmed at runtime): `dispatch(request: BuildRequest, annall: AnnallPort, hoard: Any | None = None, config: dict[str, Any] | None = None) -> BuildResponse`

**FINDING AUDIT-002 (Medium):** The implementation signature has two additional optional parameters (`hoard`, `config`) not present in the documented contract. These are used by the test suite to inject mock dependencies and by the Bridge callers to pass configuration. While they are optional and default to `None`, the INTERFACE.md contract is incomplete. Callers relying solely on the documented signature would not know about the `hoard` injection point — critical for testing.

Recommended addendum: `src/seidr_smidja/bridges/core/INTERFACE_AMENDMENT_2026-05-06.md`.

---

### Bridges INTERFACE.md (Rúnstafr CLI commands)

Documented commands:
```
seidr build ...
seidr check <vrm_file> [--targets ...]
seidr list-assets [--type <type>] [--tag <tag>]
seidr version
```

Actual commands registered:
```
seidr build ...      ← present
seidr inspect ...    ← present (INTERFACE says "seidr check")
seidr bootstrap-hoard ← present (not documented in INTERFACE)
seidr version        ← present
```

**FINDING AUDIT-003 (Medium):** Two command name discrepancies:
1. INTERFACE.md says `seidr check`; implementation registered as `seidr inspect` (`cli.py:210`).
2. INTERFACE.md says `seidr list-assets`; implementation has no `list-assets` CLI command. The REST bridge (`api.py:219`) exposes `GET /v1/assets` but the CLI has no equivalent `list-assets` subcommand.

`seidr bootstrap-hoard` exists in implementation but is undocumented in INTERFACE.md.

Recommended: `src/seidr_smidja/bridges/INTERFACE_AMENDMENT_2026-05-06.md` documenting the actual command names.

---

### Remaining INTERFACE.md files (Hoard, Forge, Oracle Eye, Gate, Annáll)

- **Hoard**: `resolve(asset_id: str) -> Path` — implementation `local.py` matches. `list_assets(filter)` present. `catalog_path() -> Path` present. No drift.
- **Forge**: `build(spec, base_asset, output_dir) -> ForgeResult` — actual implementation adds `config=None, annall=None, session_id=None`. These are optional parameters for DI (consistent with D-005). INTERFACE.md does not document these optional parameters. Same class of drift as AUDIT-002 but lower severity since callers can safely ignore them.
- **Oracle Eye**: `render(vrm_path, output_dir, views=None) -> RenderResult` — actual adds `config=None, annall=None, session_id=None`. Same pattern.
- **Gate**: `check(vrm_path, targets=None) -> ComplianceReport` — actual adds `rules_dir=None, vrchat_tier="Good", annall=None, session_id=None`. Same pattern.
- **Annáll**: `AnnallPort` protocol — five methods verified against `port.py`. All five methods present and conforming. `query_sessions` raises `AnnallQueryError` as documented.

**All domain INTERFACE.md files omit the `annall` and `config` DI parameters from their public signatures.** This is a consistent pattern across all five domains. The INTERFACE documents the conceptual signature; the implementation adds optional DI parameters for testing and runtime wiring. This is the D-005 design realized but not fully captured in the INTERFACE contracts.

Recommended: Add a single note to each domain's `INTERFACE_AMENDMENT_2026-05-06.md` documenting the optional parameters.

---

## Section E — Data-Driven-ness Audit

### Hardcoded values found

**FINDING AUDIT-004 (Low — platform hints, documented pattern):**
`_internal/blender_runner.py:33-45`: `_PLATFORM_HINTS` dict contains hardcoded Windows paths:
```python
r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
...
```
and Linux paths `/usr/bin/blender`, `/usr/local/bin/blender`, and macOS `/Applications/Blender.app/Contents/MacOS/Blender`.

ARCHITECTURE.md §V explicitly documents "Platform-specific well-known locations" as step 4 in the priority chain, intended as fallback hints. The constants are consistent with the documented design and their role is clearly fallback-only after env var, config, and PATH lookup. However, Sacred Law II ("No Absolute Paths") and RULES.AI.md state "Never use absolute paths no matter what!" These hints are absolute paths in code.

**The ARCHITECTURE.md explicitly anticipates platform hints, and the runner docstring labels them as hints of last resort.** This is a documented architectural tension — the ARCHITECTURE explicitly says these are checked "last" and only provide a hint. Nonetheless, the letter of Sacred Law II is violated. The paths are hardcoded in Python source.

Additive recommended fix: Move `_PLATFORM_HINTS` to `config/defaults.yaml` under a `blender.platform_hints` key. The runner reads from config at step 4 instead of from the hardcoded constant. This makes the hints configurable and satisfies the location-agnostic law without breaking functionality.

### Hardcoded default color values in schema

`schema.py` lines such as `RGBColor(r=0.3, g=0.5, b=0.8)` for default eye color are field defaults on Pydantic models. These are schema defaults, not avatar data. They are overridden by any spec. This is acceptable and not a violation of "No Hardcoded Wyrd" — the Loom schema necessarily carries sensible defaults.

### Gate: polycount check silently skipped

`gate/gate.py:121-129`: The `vrchat.polycount` rule is loaded from YAML (`vrchat_rules.yaml` line 191-197) but the Python implementation explicitly skips it with a `TODO` comment:
```python
# TODO(forge-worker): integrate a full glTF mesh parser when available.
if budget is not None:
    logger.debug("Gate: polycount check skipped in v0.1 structural mode ...")
```

**FINDING AUDIT-008 (Medium):** The polycount rule exists in the YAML (data-driven, as required) but is silently not enforced in v0.1. The SYSTEM_VISION Unbreakable Vow 2 says "Every output passes VRChat compliance." A VRM with 200,000 polygons would pass the Gate in the current implementation. This is not silent — it is logged at DEBUG — but the agent receives no warning in the `ComplianceReport` that a budget check was skipped. The vow is not currently delivered. PHILOSOPHY §5 permits this for v0.1 if it is an explicit acknowledged deferral, but it is only in a code comment, not in a documented decision or INTERFACE amendment.

Additionally, `vrchat.texture_memory` rule exists in YAML but has no corresponding handling code in `_check_vrchat()`. It will silently produce no violation even on overbudget texture memory.

Recommended additive fix: When polycount and texture_memory checks are skipped, append a `Violation(severity=WARNING, ...)` to the report indicating the check was not performed in v0.1 mode. This turns a silent skip into a transparent advisory.

---

## Section F — Cross-Platform / Path-Agnostic Audit

### Absolute path in platform hints (covered in Section E — AUDIT-004)

`_internal/blender_runner.py:33-45`: Multiple absolute paths in `_PLATFORM_HINTS`.

### `os.path.join` in Blender render script

`oracle_eye/scripts/render_avatar.py:125`:
```python
output_path = os.path.join(output_dir, f"{view_name}.png")
```
This script runs inside the Blender process (not the main Python process). `os.path.join` is cross-platform correct — it normalizes separators. However, `pathlib.Path` is the project standard per ARCHITECTURE.md §VI: "All path construction uses `pathlib.Path`." The Blender script uses `os.path.join` instead.

**FINDING AUDIT-009 (Low):** The render script (`oracle_eye/scripts/render_avatar.py:125`) uses `os.path.join` rather than `pathlib.Path`. Functionally equivalent on all platforms but violates the stated cross-platform standard. Note: this file runs inside Blender's embedded Python, which supports `pathlib.Path`.

### Remaining path construction

All other `src/seidr_smidja/**/*.py` files examined use `pathlib.Path` for path operations. No hardcoded path separators found in the main package beyond the noted exceptions.

---

## Section G — Test Quality Audit

### Count and runtime

Personally run: **134 passed in 1.68s** (second run: 1.64s). Claim VERIFIED.

### `test_dispatch_smoke.py` — wiring test quality

`test_full_pipeline_returns_success`: mocks Forge (`forge.runner.build`) and Oracle Eye (`oracle_eye.eye.render`), uses real `LocalHoardAdapter`, real `SQLiteAnnallAdapter`, and real `gate.check` with real sample VRM fixture. The Shared Anvil wiring is genuinely exercised — this is not a trivial stub test. The test confirms:
- Loom validates the real spec dict
- Hoard resolves against a real fixture catalog
- Forge is called (mocked return confirmed via `response.vrm_path == sample_vrm_fixture`)
- Gate runs for real against a known-good VRM fixture
- Annáll session is opened and closed
- `BuildResponse.request_id` matches the `BuildRequest`

**Assessment: real wiring, not a tautological test.**

`test_oracle_eye_failure_is_soft`: Oracle Eye raises `RuntimeError`, yet Gate still executes and `vrm_path` is returned. D-006 behavior confirmed.

`test_gate_failure_recorded_in_errors`: constructs a minimal boneless glTF binary inline, passes it through the Gate, confirms compliance errors appear in `BuildResponse.errors`. This is substantive — it verifies the Gate actually evaluates bone structure from binary VRM data.

### Skipped / xfail tests

`pytest --co -q` confirms: **zero skipped tests, zero xfail tests** in the non-Blender suite. No hidden work.

### Test assertion strength spot-check (three tests)

1. `test_full_pipeline_returns_success`: Asserts `response.vrm_path == sample_vrm_fixture`, `response.request_id == request.request_id`, `response.annall_session_id != ""`. Strong field-level assertions.
2. `test_extensions_hatch_round_trips` (loom/test_schema.py): Asserts that the extensions dict survives `to_dict()` and reconstruction. Concrete value assertions.
3. `test_missing_bone_produces_violation` (gate/test_gate.py): Asserts that a VRM with specific bones removed produces a violation for that specific bone rule_id. Precise rule-level assertion.

**Test quality: adequate for a vertical slice. No tautological assertions found in sampled tests.**

---

## Section H — Documentation Drift Audit

### DOMAIN_MAP.md opening sentence vs. Mermaid diagram

The Scribe flagged: "DOMAIN_MAP.md opening sentence omits Hoard."

Confirmed. `DOMAIN_MAP.md:17-19`:
```
Dependencies flow in one direction only, from the outermost layer inward:

Bridges → Loom → Forge → Oracle Eye → Gate → Annáll
```

The Mermaid diagram at `DOMAIN_MAP.md:179-207` correctly shows `CORE --> HOARD` (Hoard as a separate node called by Bridge Core alongside Loom, Forge, Oracle Eye, Gate).

**FINDING AUDIT-010 (Notable):** The linear dependency notation in the opening paragraph omits Hoard. The Mermaid diagram is correct. The ARCHITECTURE.md `§I` layer model also correctly lists Hoard in Layer 2 Domain Core. The prose shorthand is inconsistent with both diagrams and the full domain catalog that immediately follows in the same file.

This is the Scribe-flagged drift. Confirmed accurate.

Additive recommended correction (per additive-only rule): Add a clarifying parenthetical after the linear notation, e.g.:
```
Bridges → Loom → Hoard → Forge → Oracle Eye → Gate → Annáll
(Hoard is called by Bridge Core alongside Loom — see the diagram below for the full dependency topology)
```

Do NOT delete the existing sentence. The Scribe applies this correction in Phase 7.

---

### Cross-reference link validation

The following links exist in DATA_FLOW.md (lines 13-20) pointing to INTERFACE.md files:
- `../src/seidr_smidja/loom/INTERFACE.md` — file exists at `src/seidr_smidja/loom/INTERFACE.md`. ✓
- `../src/seidr_smidja/hoard/INTERFACE.md` — file exists. ✓
- `../src/seidr_smidja/forge/INTERFACE.md` — file exists. ✓
- `../src/seidr_smidja/oracle_eye/INTERFACE.md` — file exists. ✓
- `../src/seidr_smidja/gate/INTERFACE.md` — file exists. ✓
- `../src/seidr_smidja/annall/INTERFACE.md` — file exists. ✓
- `../src/seidr_smidja/bridges/core/INTERFACE.md` — file exists. ✓
- `../src/seidr_smidja/bridges/INTERFACE.md` — file exists. ✓

All cross-reference paths resolve. ✓

D-006 reference in `ARCHITECTURE.md §X` links to `PHILOSOPHY.md §X Error Handling` — PHILOSOPHY.md has no numbered sections; it has I–VI. The cross-reference text is descriptive and correct in intent even though the section numbering does not match. Minor navigational inaccuracy only.

ADRs D-001..D-007 are referenced from DATA_FLOW.md §X (T1–T5), from ARCHITECTURE.md inline, and from the INTERFACE.md files. All seven ADRs exist and are accessible. ✓

---

### DEVLOG.md

`docs/DEVLOG.md` — the TASK file says "initialized" in Phase 4 (Memory/Scribe). The audit cannot confirm its current state without reading it, but it is listed as pending in TASK Phase 7. No unresolved DEVLOG references found in other documents.

---

## Section I — Compliance Pre-Check

### VRChat rules (`data/gate/vrchat_rules.yaml`)

| Required category | Present |
|---|---|
| Polygon count budget (per tier) | Yes — `performance_tiers` with `polycount` per tier; `vrchat.polycount` rule in `rules:` array |
| Bone structure | Yes — `vrchat.humanoid_bones.required` with 19 required bones |
| Viseme coverage | Yes — 15 viseme rules (sil, pp, ff, th, dd, kk, ch, ss, nn, rr, aa, e, ih, oh, ou) |
| Material count | Yes — `vrchat.material_count` rule (WARNING severity) with tier budgets |
| Texture size limits | Yes — `vrchat.texture_memory` rule (WARNING severity) |

All promised VRChat categories are present in the YAML.

**However, per AUDIT-008: `vrchat.polycount` is loaded but silently not enforced in Python. `vrchat.texture_memory` is loaded but has no corresponding evaluation code in `_check_vrchat()`.**

### VTube Studio rules (`data/gate/vtube_rules.yaml`)

| Required category | Present |
|---|---|
| VRM 0.x or 1.0 version check | Yes — `vtube.vrm_version` with `accepted_versions: ["0.0", "1.0"]` |
| Expression presets | Yes — joy, angry, sorrow, fun (ERROR), surprised, neutral (WARNING) |
| LookAt configuration | Yes — `vtube.lookat_sane` with valid types Bone/BlendShape |
| Head/neck bones | Yes — `vtube.humanoid_bones.head`, `vtube.humanoid_bones.neck` |

All promised VTube Studio categories are present.

**One gap:** `vtube.first_person_bone` (WARNING) and `vtube.eye_bones` (WARNING) exist in the YAML but have no corresponding evaluation code in `_check_vtube()` — they will never produce a violation. Like the polycount issue, these are silently unenforced warnings.

---

## Section J — Punch List

| ID | Severity | Section | Description | Recommended Fix | Owner |
|---|---|---|---|---|---|
| AUDIT-001 | Low | D | `DOMAIN_MAP.md` references `spec.from_file(path)` as a Loom public method, but implementation uses `load_spec()` / `load_and_validate()` — no instance method `from_file`. INTERFACE.md is internally consistent (does not list `from_file`) but DOMAIN_MAP text deviates. | Additive note in `DOMAIN_MAP.md` clarifying that `spec.from_file()` is the pattern description, not a method; the function is `load_spec()`. | Scribe |
| AUDIT-002 | Medium | D | `bridges/core/INTERFACE.md` documents `dispatch(request, annall)` but implementation is `dispatch(request, annall, hoard=None, config=None)`. The `hoard` injection point is undocumented — critical for testing and for callers that need to inject mock Hoards. | Create `src/seidr_smidja/bridges/core/INTERFACE_AMENDMENT_2026-05-06.md` documenting the additional parameters. | Scribe |
| AUDIT-003 | Medium | D | `bridges/INTERFACE.md` documents `seidr check` (not `seidr inspect`) and `seidr list-assets` (no such command in CLI). Implementation has `seidr inspect` and `seidr bootstrap-hoard` instead. Two command names diverged from contract. | Create `src/seidr_smidja/bridges/INTERFACE_AMENDMENT_2026-05-06.md` documenting the actual registered command names. Verify with Volmarr whether `seidr check` vs `seidr inspect` was an intentional rename. | Scribe (doc), Forge Worker (confirm rename intent) |
| AUDIT-004 | Low | E, F | `_internal/blender_runner.py:33-45`: `_PLATFORM_HINTS` dict contains absolute Windows, Linux, and macOS paths hardcoded in Python source, violating Sacred Law II. Architecturally documented as a "last resort hint" but still absolute paths in code. | Additive: move platform hints to `config/defaults.yaml` under `blender.platform_hints`. Runner reads from config at step 4. | Forge Worker |
| AUDIT-005 | Medium | A, B | D-005 states all five domains (Loom, Hoard, Forge, Oracle Eye, Gate) should receive `annall` as a parameter and log independently (Option B). Actual: Forge, Oracle Eye, and Gate log independently (Option B). Loom and Hoard do not accept `annall` in their public call signatures — Core logs on their behalf (Option A). The inconsistency means the Loom and Hoard log events but the `loom.validated` and `hoard.resolved` events are logged by Core code, not by the domains themselves. This is inconsistent with D-005 and with what the INTERFACE.md files say ("May write to Annáll for validation event logging"). Functional, but architecturally inconsistent with the ratified decision. | Additive: add optional `annall: AnnallPort | None = None` and `session_id` parameters to `loom.load_spec()` and `hoard.resolve()` (and `hoard.list_assets()`). Update INTERFACE.md files accordingly via amendment. | Forge Worker |
| AUDIT-006 | Low | A | D-002 (Repo and Branch) is a repo-level decision unverifiable from code. Noted as unverifiable-as-tested from code inspection alone. | No code change needed. Document in DEVLOG.md that D-002 compliance is verified at the repo level (standalone repo created, development branch in use). | Scribe |
| AUDIT-007 | Low | A | Claude Code skill uses `bridges/skills/claude_code/SKILL.md` (markdown doc), not `bridges/skills/claude_code/manifest.yaml` (as listed in `bridges/INTERFACE.md:99`). The content is equivalent but the filename deviates from the documented contract. | Additive: note in `INTERFACE_AMENDMENT_2026-05-06.md` that the Claude Code skill uses a Markdown document format (`SKILL.md`) rather than a YAML manifest, and explain why (Claude Code skill invokes via CLI rather than a YAML-schema adapter). | Scribe |
| AUDIT-008 | Medium | E, I | VRChat compliance: `vrchat.polycount` rule is in YAML but silently skipped in `gate.py:128`. `vrchat.texture_memory` rule is in YAML but has no evaluation code. VTube Studio compliance: `vtube.first_person_bone` and `vtube.eye_bones` are in YAML but unevaluated. The Gate currently passes VRMs that would exceed polygon budgets, violating Unbreakable Vow 2 ("Every output passes VRChat compliance"). | Additive: when a rule exists in YAML but evaluation is not implemented, append a `Violation(severity=WARNING, rule_id=..., description="Rule not evaluated in v0.1 — manual check required")` to the report. This turns a silent gap into an explicit advisory the agent can see. Do not remove the TODO comment — add the warning generation beside it. | Forge Worker |
| AUDIT-009 | Low | F | `oracle_eye/scripts/render_avatar.py:125`: uses `os.path.join(output_dir, ...)` instead of `pathlib.Path` per project standard (ARCHITECTURE.md §VI). Functionally equivalent but inconsistent with the stated cross-platform standard. | Replace with `str(Path(output_dir) / f"{view_name}.png")`. | Forge Worker |
| AUDIT-010 | Notable | H | `DOMAIN_MAP.md` opening linear notation `Bridges → Loom → Forge → Oracle Eye → Gate → Annáll` omits Hoard, contradicting the Mermaid diagram in the same file (which correctly shows Hoard as a Core dependency). Confirmed as the Scribe-flagged drift. | Additive correction: update the linear notation to `Bridges → Loom → Hoard → Forge → Oracle Eye → Gate → Annáll` with a parenthetical clarifying the Core calls all five domains in pipeline order. Do NOT delete the existing sentence — prepend or replace in-place with Scribe approval. Apply in Phase 7. | Scribe |

**Summary by severity:**
- Critical: 0
- High: 0
- Medium: 4 (AUDIT-002, AUDIT-003, AUDIT-005, AUDIT-008)
- Low / Notable: 6 (AUDIT-001, AUDIT-004, AUDIT-006, AUDIT-007, AUDIT-009, AUDIT-010)

---

## Section K — Verdict

**PASS WITH CONCERNS**

The vertical slice delivers the structural skeleton of the Primary Rite. The forge pipeline wires correctly end-to-end. All sacred principles are substantially honored. The dependency law is clean. No GUI code exists. The AnnallPort injection pattern is implemented, the Shared Blender runner is in `_internal/` per D-003, soft render failure is correct per D-006, two separate subprocesses per D-007. The 134 non-Blender tests pass at the claimed count and timing, and the dispatch smoke test exercises real wiring, not a trivial stub.

The slice does **not** yet fully deliver Unbreakable Vow 2 ("Every output passes VRChat compliance"): the polycount rule is silently unenforced. An agent using this forge today can receive a VRM that exceeds the VRChat polygon budget without being told so. This gap must be addressed before v0.1 is tagged.

The three medium-severity issues that must be resolved before v0.1 tagging:
1. **AUDIT-002**: `dispatch()` signature is underdocumented — hoard injection point is invisible to callers relying on the INTERFACE contract.
2. **AUDIT-003**: CLI command names (`seidr check` vs `seidr inspect`, `seidr list-assets` missing) diverge from the BRIDGES INTERFACE contract.
3. **AUDIT-008**: Polycount and texture memory compliance rules are silently unenforced — the Gate does not fully deliver the compliance promise. Agents receive no advisory.

AUDIT-005 (Annáll injection inconsistency between domains) should be resolved to honor D-005 cleanly, but it does not break the pipeline and may be addressed in Phase 7 cleanup rather than as a blocker.

The Scribe's primary task in Phase 7 is AUDIT-010 (DOMAIN_MAP linear notation correction) and AUDIT-002/003 INTERFACE amendments. The Forge Worker should address AUDIT-008 (silent polycount skip) as the highest-priority code change.

---

*Sólrún Hvítmynd, Auditor — first forge audit, 2026-05-06.*
*The blade is mostly shaped. Three edges remain unfinished. The Gate does not yet fully judge what it receives.*
