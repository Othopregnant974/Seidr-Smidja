# HARDENING_AUDIT — Seiðr-Smiðja Phase A
**Date:** 2026-05-06
**Scope:** Full source tree + test suite + data files + config — branch `development`, HEAD `90981b1`
**Auditor:** Sólrún Hvítmynd (Auditor role)
**Prior audit:** `docs/AUDIT_GENESIS.md` (findings AUDIT-001..010, all addressed by HEAD)

---

## Section 1 — Run Metadata

| Field | Value |
|---|---|
| Date | 2026-05-06 |
| Branch | development |
| HEAD | `90981b1` |
| Python | 3.10.11 (win32) |
| pytest | 9.0.2 |
| pytest-cov | 7.1.0 (installed prior to this audit; was already present) |
| Test run command | `python -m pytest -m "not requires_blender" -v` |
| Coverage command | `python -m pytest -m "not requires_blender" --cov=seidr_smidja --cov-report=term-missing` |
| Test result | **159 passed, 0 failed, 0 skipped** |
| Total coverage | **53%** (1932 stmts, 905 missed) |
| Files audited (src) | 36 Python source files |
| Files audited (tests) | 20 test files |
| Files audited (data/config) | `config/defaults.yaml`, `data/gate/vrchat_rules.yaml`, `data/gate/vtube_rules.yaml` |
| Tooling installed during audit | None — pytest-cov already present |

---

## Section 2 — Findings by Severity

---

### H-001 — Temp directory leaked when spec file write raises OSError
- **Severity:** High
- **Domain:** forge
- **File:** `src/seidr_smidja/forge/runner.py:132-185`
- **Category:** Resource leak
- **Symptom:** On a disk-full or permission-denied error writing the temporary JSON spec file, `tempfile.mkdtemp()` has already created a directory that is never cleaned up. The temp dir remains until OS reboot or manual cleanup.
- **Root cause:** Two separate `try` blocks are used: the first (lines 132–141) creates the temp dir and writes the spec; the second (lines 161–185) runs Blender, with a `finally` block that cleans up the temp dir. If the first `try` raises `OSError` at line 137 (spec write fails), execution immediately jumps to the `except OSError` handler at line 138 which raises `ForgeBuildError`. The second `try`/`finally` block (line 177) is **never entered**, so the `shutil.rmtree(tmp_dir)` in its `finally` clause never executes. `tmp_dir` created at line 135 is orphaned.
- **Reproduction:**
  ```python
  # Patch spec_path.write_text to raise OSError after mkdtemp succeeds
  # Observe: tmp directory remains on disk after ForgeBuildError
  ```
- **Recommended fix (additive):** Wrap the entire block — from `tmp_dir = None` through `shutil.rmtree` — in a single outer `try/finally`:
  ```python
  tmp_dir = None
  try:
      tmp_dir = Path(tempfile.mkdtemp())
      spec_path = tmp_dir / "spec.json"
      spec_path.write_text(spec_json, encoding="utf-8")
      # ... rest of build ...
  except OSError as exc:
      raise ForgeBuildError(...)
  finally:
      if tmp_dir and tmp_dir.exists():
          shutil.rmtree(tmp_dir, ignore_errors=True)
  ```
- **Owner:** Forge Worker

---

### H-002 — No timeout on post-kill `communicate()` in blender_runner — potential hang
- **Severity:** High
- **Domain:** _internal
- **File:** `src/seidr_smidja/_internal/blender_runner.py:250-254`
- **Category:** Resource leak / concurrency
- **Symptom:** If Blender hangs and the first `communicate(timeout=timeout)` raises `SubprocessTimeoutExpired`, the code calls `process.kill()` followed by `process.communicate()` **without a timeout**. On Windows, `process.kill()` calls `TerminateProcess()` which is normally immediate, but on some locked or wedged processes (anti-virus hold, open file handles), the process may not terminate promptly. The second `communicate()` would block indefinitely, hanging the entire forge pipeline with no escape.
- **Root cause:** `blender_runner.py:253`: `_, stderr_raw = process.communicate()` — no `timeout` argument after `process.kill()`.
- **Reproduction:** Construct a subprocess that ignores `SIGKILL` equivalent on Windows (or a process that has open handles preventing termination). After first timeout, the second `communicate()` hangs.
- **Recommended fix (additive):** Add a short fixed timeout to the post-kill communicate:
  ```python
  except subprocess.TimeoutExpired:
      process.kill()
      try:
          _, stderr_raw = process.communicate(timeout=30)  # Hard ceiling post-kill
      except subprocess.TimeoutExpired:
          stderr_raw = ""
          logger.error("Blender process did not terminate after kill (timeout=30s)")
      stderr_lines.extend(stderr_raw.splitlines() if stderr_raw else [])
      timed_out = True
  ```
- **Owner:** Forge Worker

---

### H-003 — Path traversal: Hoard `resolve()` does not verify filename stays under `bases_dir`
- **Severity:** High
- **Domain:** hoard
- **File:** `src/seidr_smidja/hoard/local.py:122`
- **Category:** Path safety / Security
- **Symptom:** A maliciously crafted catalog entry with `filename: "../../etc/passwd"` would resolve to a path outside the `bases_dir`. The resolved path is returned to the Forge as a "base asset" path.
- **Root cause:** `local.py:122`: `asset_path = (self._bases_dir / filename).resolve()`. The `filename` field comes from the YAML catalog, which is under the operator's control but could be tampered with or contain path traversal sequences. The code calls `.resolve()` (which normalizes `..` components) but never verifies the result is a child of `self._bases_dir`. Verified by running:
  ```
  filename = '../../etc/passwd'
  result = (bases / filename).resolve()  # → C:\Users\volma\AppData\Local\Temp\etc\passwd
  result.startswith(str(bases.resolve()))  # → False
  ```
- **Reproduction:** Insert a catalog entry with `filename: "../../sensitive_file"` and call `resolve()`.
- **Recommended fix (additive):** After resolving, check containment:
  ```python
  asset_path = (self._bases_dir / filename).resolve()
  bases_resolved = self._bases_dir.resolve()
  try:
      asset_path.relative_to(bases_resolved)
  except ValueError:
      raise AssetNotFoundError(
          asset_id=asset_id,
          message=f"Catalog entry for '{asset_id}' has a filename that escapes the bases_dir. "
                  f"This may indicate a tampered catalog."
      )
  ```
- **Owner:** Forge Worker

---

### H-004 — REST `POST /v1/inspect` accepts arbitrary filesystem paths — no path restriction
- **Severity:** High
- **Domain:** bridges/straumur
- **File:** `src/seidr_smidja/bridges/straumur/api.py:181`
- **Category:** Security / Input validation
- **Symptom:** The `InspectRequestBody.vrm_path` field is a raw string that becomes `Path(body.vrm_path)` with no validation. Any caller of the REST API can pass `vrm_path: "/etc/passwd"` or `vrm_path: "C:/Windows/System32/kernel32.dll"` and the Gate will attempt to read and parse it as a VRM file. While the binary parser will reject it as non-VRM (raising `VRMReadError` → `GateError` → HTTP 500), the file is still opened and read.
- **Root cause:** `api.py:181`: `vrm_path = Path(body.vrm_path)` — no containment check, no allowlist, no stat guard before passing to `gate_check()`.
- **Reproduction:** `POST /v1/inspect` with `{"vrm_path": "C:/Windows/System32/kernel32.dll"}` — server opens and reads 1MB+ of system file content.
- **Recommended fix (additive):** Add a server-side path validation helper that checks: (a) the path must end in `.vrm`, (b) the path must be under a configured `output_root` or an explicit `allowed_inspect_paths` list in config:
  ```python
  def _validate_vrm_path(path: Path, cfg: dict) -> None:
      if path.suffix.lower() != ".vrm":
          raise HTTPException(400, "vrm_path must be a .vrm file")
      # Additional containment check if output_root is configured
  ```
- **Owner:** Forge Worker

---

### H-005 — REST server `__main__` binds to `0.0.0.0` — exposes forge on all network interfaces
- **Severity:** High
- **Domain:** bridges/straumur
- **File:** `src/seidr_smidja/bridges/straumur/api.py:299`
- **Category:** Security
- **Symptom:** When run as `python -m seidr_smidja.bridges.straumur.api`, the server binds to `host="0.0.0.0"`, making it reachable from any network interface — LAN, WiFi, VPN. There is no authentication, no rate limiting, and no token validation on any endpoint. The forge is documented as an "agent-only" system, but with `0.0.0.0` binding and no auth, any process on any connected host can submit arbitrary build requests.
- **Root cause:** `api.py:299`: `uvicorn.run(..., host="0.0.0.0", port=8765, ...)`. This violates the PHILOSOPHY's Sacred Law IX ("No Human Door") in spirit — an unauthenticated network service is the widest possible door.
- **Reproduction:** Start the server; make a `POST /v1/avatars` from another machine on the same network. No credentials required.
- **Recommended fix (additive):** Change the default to `host="127.0.0.1"` and add a `SEIDR_REST_HOST` and `SEIDR_REST_PORT` environment variable override:
  ```python
  import os
  host = os.environ.get("SEIDR_REST_HOST", "127.0.0.1")
  port = int(os.environ.get("SEIDR_REST_PORT", "8765"))
  uvicorn.run(..., host=host, port=port, ...)
  ```
  Document in ARCHITECTURE.md that the REST bridge is localhost-only by default and requires explicit operator configuration to expose further.
- **Owner:** Forge Worker

---

### H-006 — `assert` statements guard subprocess stdout/stderr handles — removed under `-O` flag
- **Severity:** Medium
- **Domain:** _internal
- **File:** `src/seidr_smidja/_internal/blender_runner.py:234-235`
- **Category:** Error handling / Cross-platform
- **Symptom:** Lines 234–235 are `assert process.stdout is not None` and `assert process.stderr is not None`. Python `assert` statements are silently removed when the interpreter is run with the `-O` (optimize) flag, as is common in production deployments and some CI setups. If these assertions are removed and `process.stdout` is `None` (which cannot happen given `subprocess.PIPE` is used, but defensive programming matters here), line 238 `for line in process.stdout:` raises `TypeError: 'NoneType' object is not iterable` with no actionable error message.
- **Root cause:** Using `assert` for runtime guard rather than an explicit `if`-check with a proper exception.
- **Reproduction:** Run with `python -O -c "from seidr_smidja._internal.blender_runner import run_blender; ..."` and inject a mocked Popen that returns `stdout=None`.
- **Recommended fix (additive):** Replace the assert with an explicit guard:
  ```python
  if process.stdout is None or process.stderr is None:
      raise RuntimeError("Blender subprocess stdout/stderr are None despite PIPE. This is a platform bug.")
  ```
- **Owner:** Forge Worker

---

### H-007 — `loom/validator.py` is a complete module that is never called — orphaned code
- **Severity:** Medium
- **Domain:** loom
- **File:** `src/seidr_smidja/loom/validator.py:1-135` (full file, 0% coverage)
- **Category:** Other (Sacred Law IV violation)
- **Symptom:** `loom/validator.py` defines `validate_semantics()` and `validate_and_raise()` — a second-pass semantic validator for blendshape names, `base_asset_id` content, and license strings. It is **never imported from anywhere** in the pipeline: not from `loader.py`, not from `dispatch.py`, not from `__init__.py` exports, and has zero test coverage. It exists, but it is never executed.
- **Root cause:** The module was written but the wiring step was never completed. Sacred Law IV: "No Orphaned Metal — no code module may be written without its connections completed."
- **Evidence:** `grep -r "validate_semantics"` in `src/` returns only `validator.py` itself. `grep -r "validate_and_raise"` returns only `validator.py` itself. The module is not in `loom/__init__.py.__all__`. Coverage: 0%.
- **Recommended fix (additive):** Either (a) wire `validate_and_raise(spec)` into `load_spec()` after the pydantic validation step, or (b) document explicitly in `loom/validator.py` that it is a future extension not yet wired, and add a TODO tracked in the ADR system. The orphaned state is the violation; the resolution is either wiring or explicit acknowledgment.
- **Owner:** Forge Worker (wiring) or Scribe (documented deferral)

---

### H-008 — `config/defaults.yaml` key `annall.write_jsonl_alongside` is dead — never read
- **Severity:** Medium
- **Domain:** annall / config
- **File:** `config/defaults.yaml:39`, `src/seidr_smidja/annall/factory.py:1-53`
- **Category:** Config / Doc drift
- **Symptom:** `defaults.yaml:39` documents `write_jsonl_alongside: true` — described as "when adapter=sqlite, also write JSON-lines to the file adapter path." However, `factory.py` reads `adapter_name` and constructs only one adapter — either sqlite, null, or file. It **never reads** `write_jsonl_alongside` and never constructs a dual-write (sqlite + file) adapter. The config key is completely inert.
- **Root cause:** The key was added to the config as a documented feature but the factory code to honor it was never written. Verified: `"write_jsonl_alongside" in factory.py` → `False`.
- **Recommended fix (additive):** Either implement dual-write in `factory.py` (wrap both adapters in a `CompositeAnnallAdapter` that forwards all calls to both), or add a comment to `defaults.yaml` noting the key is `RESERVED — not yet implemented` and create a tracking ADR. The dead config key misleads operators who read the documentation and expect JSONL trace files to appear.
- **Owner:** Forge Worker (implementation) or Scribe (documentation of deferred state)

---

### H-009 — CLI `cmd_build` calls `load_spec()` twice — double validation on every build
- **Severity:** Medium
- **Domain:** bridges/runstafr
- **File:** `src/seidr_smidja/bridges/runstafr/cli.py:137-146`
- **Category:** Other (redundant work, potential divergence)
- **Symptom:** The CLI `cmd_build` function calls `load_spec(spec_path)` at line 137–146 to extract `spec.base_asset_id` before calling `dispatch()`. Then `dispatch()` calls `load_spec(request.spec_source)` again at the Loom step (Step 1). The spec is loaded, parsed, and validated twice per build. This is inefficient and creates a brief window of divergence: if the spec file changes between the two reads, the `base_asset_id` used for the first display and the `BuildRequest` is from a different version of the file than what dispatch processes.
- **Root cause:** The CLI needs `base_asset_id` to populate `BuildRequest.base_asset_id` before calling dispatch. Rather than extracting it from a pre-parsed spec, it re-reads from file. The Mjöll MCP bridge has the same pattern at `server.py:169-174`.
- **Reproduction:** Modify a spec file between the two reads (race condition). The `BuildRequest.base_asset_id` will differ from what the Loom processes.
- **Recommended fix (additive):** Pass the already-loaded spec directly into dispatch via the `spec_source: dict` path:
  ```python
  spec = load_spec(spec_path)
  request = BuildRequest(
      spec_source=spec.to_dict(),  # pass dict not path — no re-read
      base_asset_id=spec.base_asset_id,
      ...
  )
  ```
  This eliminates both the double I/O and the race window.
- **Owner:** Forge Worker

---

### H-010 — SQLite `_connect()` uses `raise exc` not `raise` — traceback origin replaced
- **Severity:** Low
- **Domain:** annall
- **File:** `src/seidr_smidja/annall/adapters/sqlite.py:102`
- **Category:** Error handling
- **Symptom:** In the `_connect()` context manager, the `except sqlite3.Error` handler executes `conn.rollback()` then `raise exc`. Using `raise exc` (re-raise the bound variable) replaces the exception's traceback with the current frame, obscuring the original call site that caused the error. `raise` (bare re-raise) would preserve the full traceback.
- **Root cause:** `sqlite.py:102`: `raise exc` instead of `raise`.
- **Recommended fix (additive):** Change `raise exc` to `raise` to preserve the original traceback:
  ```python
  except sqlite3.Error as exc:
      conn.rollback()
      raise  # bare re-raise preserves traceback
  ```
- **Owner:** Forge Worker

---

### H-011 — `print()` used for error reporting in Annáll adapters and bootstrap — violates coding standard
- **Severity:** Low
- **Domain:** annall, hoard/bootstrap
- **File:** `src/seidr_smidja/annall/adapters/sqlite.py:86,129,150,170`; `src/seidr_smidja/annall/adapters/file.py:62`; `src/seidr_smidja/hoard/bootstrap.py:74,75,94,98,130,136,137,151,156,157,160,165,167`
- **Category:** Error handling / Cross-platform
- **Symptom:** Multiple uses of `print(..., file=sys.stderr)` in production code paths. RULES.AI.md coding standards state: "never use `print()`; use loggers only." The bootstrap's verbose output is intentional CLI feedback, but the sqlite and file adapter warnings should use the module `logger.warning()`.
- **Root cause:** The Annáll adapter "never raises" contract was implemented by swallowing errors to stderr via `print()`. Bootstrap uses `print()` for user-facing verbose output (more defensible but still inconsistent).
- **Recommended fix (additive):** Replace `print(..., file=sys.stderr)` with `logger.warning(...)` in sqlite.py and file.py. For bootstrap.py, `print()` is acceptable for a CLI utility but the verbose flag should control it consistently (it already does via the `verbose` parameter).
- **Owner:** Forge Worker

---

### H-012 — `hoard/bootstrap.py` has no SHA-256 verification against expected values
- **Severity:** Low
- **Domain:** hoard/bootstrap
- **File:** `src/seidr_smidja/hoard/bootstrap.py:147-153`
- **Category:** Security
- **Symptom:** The bootstrap downloads VRM files from GitHub URLs, computes their SHA-256 after download, and stores the hash in the catalog. But there are no expected (pinned) SHA-256 hashes to compare against. A compromised URL (DNS hijack, MITM, CDN poisoning) would result in a malicious file being stored in the Hoard and marked as `cached: True`, which would then be used as a base asset for every Forge build without further validation.
- **Root cause:** `_BOOTSTRAP_ASSETS` entries contain no `expected_sha256` field. The downloaded hash is computed and stored but never compared to an expected value.
- **Recommended fix (additive):** Add `expected_sha256` to each entry in `_BOOTSTRAP_ASSETS`. After download, compare computed vs. expected and delete the file + raise an error if they do not match:
  ```python
  if asset_info.get("expected_sha256") and sha256 != asset_info["expected_sha256"]:
      dest.unlink()  # Delete corrupted/tampered file
      logger.error("SHA-256 mismatch for '%s': expected %s, got %s",
                   asset_id, asset_info["expected_sha256"], sha256)
      results[asset_id] = False
      continue
  ```
- **Owner:** Forge Worker

---

### H-013 — `hoard/local.py` `_load_catalog()` silently accepts None/malformed entries without field validation
- **Severity:** Low
- **Domain:** hoard
- **File:** `src/seidr_smidja/hoard/local.py:51-73`
- **Category:** Input validation
- **Symptom:** The catalog YAML is loaded with `yaml.safe_load()`, which is correct. But entries are accessed with `.get()` calls that silently return `None` for missing fields. A catalog with duplicate `asset_id` values would silently use the first match; a catalog with a null `filename` field is only caught at `resolve()` time, not at catalog load time. An empty catalog (`bases: []`) is accepted silently.
- **Root cause:** `_load_catalog()` does no structural validation beyond checking `isinstance(data, dict)`. Entry-level fields (`asset_id`, `filename`, `vrm_version`) are unchecked.
- **Recommended fix (additive):** Add a catalog validation pass in `_load_catalog()` that warns (via logger) on: missing `asset_id`, missing `filename`, and duplicate `asset_id` values. Do not crash — warn and continue (graceful degradation). This surfaces data quality issues without breaking the pipeline.
- **Owner:** Forge Worker

---

### H-014 — `Straumur` REST `_get_annall()` creates a new `SQLiteAnnallAdapter` on every request
- **Severity:** Low
- **Domain:** bridges/straumur
- **File:** `src/seidr_smidja/bridges/straumur/api.py:101-106`
- **Category:** Resource / Performance
- **Symptom:** `_get_annall()` is called once per `/v1/avatars` request and once per `/v1/avatars/{session_id}` request, creating a new `SQLiteAnnallAdapter` each time. `SQLiteAnnallAdapter.__init__` calls `_ensure_db()` which opens a connection, runs `PRAGMA journal_mode=WAL` and `CREATE TABLE IF NOT EXISTS` — every request. Under any load this is wasteful and adds latency. WAL re-enabling on an already-WAL database is a no-op but still incurs the connection overhead.
- **Root cause:** `_get_annall()` is not cached; `_config` uses `nonlocal` and caches, but the annall adapter does not.
- **Recommended fix (additive):** Cache the annall adapter in the `create_app()` closure alongside `_config`:
  ```python
  _annall: Any = None

  def _get_annall() -> Any:
      nonlocal _annall
      if _annall is None:
          from seidr_smidja.annall.factory import make_annall
          _annall = make_annall(_get_config(), _find_config_root())
      return _annall
  ```
- **Owner:** Forge Worker

---

### H-015 — `blender_runner.py` stdout loop reads all lines then `communicate()` collects remaining stderr — stderr may be incomplete for fast-exiting processes
- **Severity:** Notable
- **Domain:** _internal
- **File:** `src/seidr_smidja/_internal/blender_runner.py:238-253`
- **Category:** Other
- **Symptom:** The pattern reads stdout line-by-line (blocking until EOF), then calls `process.communicate()` to collect stderr. If Blender exits quickly with a large amount of stderr output, the stdout loop may block briefly after EOF, and `communicate()` then collects the buffered stderr correctly. However, the stdout loop never calls `process.wait()` independently — it relies on the for-loop exhausting the stdout pipe. On some platforms, if the process closes stdout but not stderr (unusual for Blender but possible for custom scripts), the for-loop may complete but stderr is still being written. `communicate()` handles this correctly but the ordering is non-obvious and fragile.
- **Root cause:** Architectural: the pattern could be replaced by `communicate()` alone (collecting both stdout and stderr at once) without the line-streaming callback for a simpler design. The streaming callback adds complexity that interacts with the two-step collection pattern.
- **Recommended fix (additive):** Document the ordering contract in a code comment. No behavior change needed now, but this pattern should be reviewed if the streaming callback is used heavily in production.
- **Owner:** Scribe (documentation)

---

### H-016 — `gate.py` `_DEFAULT_RULES_DIR` resolved at module import time via `__file__` — fragile in some install/packaging scenarios
- **Severity:** Notable
- **Domain:** gate
- **File:** `src/seidr_smidja/gate/gate.py:31`
- **Category:** Path safety / Cross-platform
- **Symptom:** `_DEFAULT_RULES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "gate"` — four `.parent` traversals from the gate module to reach `data/gate`. This pattern works when the package is installed in development mode (`pip install -e .`) or when the src layout is preserved. But in a flat-install or zip-import scenario (e.g., PyInstaller), `__file__` may not point to the expected location, and `data/gate` may not be four parents up.
- **Root cause:** Hard-coded parent traversal count. The same pattern exists in `loom/validator.py:26` (`_DEFAULT_BLENDSHAPES_PATH`).
- **Recommended fix (additive):** Use `importlib.resources` or a package-relative path discovery that works with installed packages. As a minimal improvement, add an assertion at module load that `_DEFAULT_RULES_DIR.exists()` and log a warning if it does not, so failures are loud rather than silent.
- **Owner:** Forge Worker

---

### H-017 — `forge/runner.py` and `oracle_eye/eye.py` at 28% and 36% coverage respectively — Blender-dependent paths untested
- **Severity:** Notable
- **Domain:** forge, oracle_eye
- **File:** `src/seidr_smidja/forge/runner.py` (28% coverage); `src/seidr_smidja/oracle_eye/eye.py` (36%)
- **Category:** Test quality
- **Symptom:** The non-Blender test coverage for these two domains is very thin. `forge/runner.py:85-220` (the entire `build()` function body including temp file handling, argument construction, and success/failure branching) is at 28% — mostly because it requires a real Blender process. However, **the temp file creation/cleanup logic, argument construction, and pre-launch validation code** (lines 85-141) could be tested without Blender by mocking `run_blender`. No such tests exist.
- **Root cause:** No unit tests for the Forge and Oracle Eye beyond what the `requires_blender` marker gates. The pre-launch validation paths (bad output_dir, missing base asset, missing build script) have no tests.
- **Recommended fix (additive):** Add `@pytest.mark.not requires_blender` (non-Blender) unit tests for `forge.runner.build()` that mock `run_blender` and verify: (a) temp dir is created and cleaned up, (b) `ForgeBuildError` is raised for missing base asset, (c) the blender args list is constructed correctly for a given spec. Same for `oracle_eye.eye.render()`.
- **Owner:** Forge Worker

---

### H-018 — `bridges/mjoll/server.py` (0% coverage), `bridges/runstafr/cli.py` (0%), `bridges/straumur/api.py` (0%) — all Bridge sub-modules completely untested
- **Severity:** Notable
- **Domain:** bridges (all sub-modules)
- **File:** coverage data — three modules at 0%
- **Category:** Test quality
- **Symptom:** None of the three concrete Bridge implementations (MCP, CLI, REST) has a single test. The only bridge test is `tests/bridges/test_dispatch.py` which tests the data models (`BuildRequest`, `BuildResponse`, `BuildError`) but not the bridge translation logic.
- **Root cause:** The genesis audit and phase 6 work produced tests for domain internals, but bridge-layer argument parsing, error output formatting, and JSON serialization are completely untested.
- **Recommended fix (additive):** Add at minimum: (a) CLI tests using `click.testing.CliRunner` for `cmd_build`, `cmd_inspect`, `cmd_bootstrap_hoard`, and `cmd_version`; (b) REST tests using `fastapi.testclient.TestClient` for `/v1/health`, `/v1/assets`, and error response shapes. These require no Blender.
- **Owner:** Forge Worker

---

### H-019 — `annall/factory.py` at 23% coverage — adapter construction paths untested
- **Severity:** Notable
- **Domain:** annall
- **File:** `src/seidr_smidja/annall/factory.py:30-53` (23% coverage)
- **Category:** Test quality
- **Symptom:** `make_annall()` is only exercised by tests that go through the full dispatch pipeline with `sqlite_annall` fixture (which bypasses the factory). The factory's own logic — selecting between sqlite, null, and file adapters based on config — is not directly tested. If the factory's path-resolution logic for `db_path` or `jsonl_path` is wrong, no test catches it.
- **Recommended fix (additive):** Add a `TestAnnallFactory` class that calls `make_annall()` with config dicts specifying each adapter type and verifies the returned adapter is of the expected type and has the expected path.
- **Owner:** Forge Worker

---

### H-020 — `hoard/bootstrap.py` at 0% coverage — the download and catalog-update logic is completely untested
- **Severity:** Notable
- **Domain:** hoard/bootstrap
- **File:** `src/seidr_smidja/hoard/bootstrap.py:1-250` (0% coverage)
- **Category:** Test quality
- **Symptom:** `run_bootstrap()`, `_download()`, `_update_catalog_entry()`, and `_compute_sha256()` have zero test coverage. The catalog write path, the fallback URL logic, and the catalog update merge logic (which modifies YAML in-place) are completely untested.
- **Recommended fix (additive):** Add unit tests using `tmp_path`, mocked `httpx.Client` or `urllib.request.urlretrieve`, and a real temporary catalog YAML to verify: (a) successful download marks `cached: True` in catalog, (b) failed download returns `False` in results dict, (c) `force=True` re-downloads existing files, (d) sha256 is stored in catalog after download.
- **Owner:** Forge Worker

---

### H-021 — `config.py` at 27% coverage — environment variable mapping and deep-merge untested
- **Severity:** Low
- **Domain:** config
- **File:** `src/seidr_smidja/config.py:36-131` (27% coverage)
- **Category:** Test quality
- **Symptom:** `_apply_env_vars()`, `_deep_merge()`, `_find_config_root()`, and `load_config()` are largely untested. The env var → nested config key mapping (e.g., `SEIDR_BLENDER_PATH` → `config["blender"]["executable"]`) has no tests. If a new env var mapping is added incorrectly, no test catches it.
- **Recommended fix (additive):** Add a `TestConfig` class covering: (a) env var override correctly sets nested key, (b) deep merge does not mutate the base dict, (c) `load_config()` with a custom `project_root` pointing to a temp dir with a minimal `defaults.yaml`.
- **Owner:** Forge Worker

---

### H-022 — Carry-forward from Genesis: `seidr list-assets` CLI command not implemented (D-008 open item)
- **Severity:** Notable (tracked)
- **Domain:** bridges/runstafr
- **File:** `src/seidr_smidja/bridges/INTERFACE.md`, `src/seidr_smidja/bridges/INTERFACE_AMENDMENT_2026-05-06.md`
- **Category:** Doc drift (known deferral, D-008)
- **Symptom:** `INTERFACE.md` documents `seidr list-assets` as a CLI command. The REST bridge has `GET /v1/assets` but the CLI has no equivalent. D-008 explicitly defers this to v0.1.1.
- **Owner:** Forge Worker (v0.1.1)

---

### H-023 — Carry-forward from Genesis: `seidr bootstrap-hoard` undocumented in `INTERFACE.md` (D-008 open item)
- **Severity:** Notable (tracked)
- **Domain:** bridges/runstafr
- **File:** `src/seidr_smidja/bridges/INTERFACE.md`
- **Category:** Doc drift (known deferral, D-008)
- **Symptom:** `seidr bootstrap-hoard` is implemented (`cli.py:288-307`) but not documented in `bridges/INTERFACE.md`. D-008 defers the documentation update to the next INTERFACE revision.
- **Owner:** Scribe (v0.1.1)

---

## Section 3 — Coverage Map

| Domain | Coverage | Verdict | Key uncovered functions/branches |
|---|---|---|---|
| `annall/adapters/sqlite.py` | 84% | **Adequate** | `_ensure_db()` error path (line 84-86), `_connect()` rollback path (101-102); `close_session()` warning path (169-170) |
| `annall/adapters/null.py` | 100% | **Strong** | — |
| `annall/adapters/file.py` | 36% | **Thin** | All of `query_sessions()` and `get_session()` body (lines 106-211) |
| `annall/factory.py` | 23% | **Thin** | `make_annall()` for sqlite and file adapter branches (lines 30-53) |
| `annall/port.py` | 97% | **Strong** | Lines 116-117 (minor) |
| `_internal/blender_runner.py` | 55% | **Thin** | Entire `run_blender()` function body (lines 200-289) — requires Blender |
| `bridges/core/dispatch.py` | 85% | **Adequate** | Core catch-all handler (318-329); `_get_hoard()` default construction (394-403) |
| `bridges/mjoll/server.py` | 0% | **Untested** | Entire file |
| `bridges/runstafr/cli.py` | 0% | **Untested** | Entire file |
| `bridges/straumur/api.py` | 0% | **Untested** | Entire file |
| `config.py` | 27% | **Thin** | `_find_config_root()`, `_apply_env_vars()`, `load_config()` |
| `forge/exceptions.py` | 60% | **Thin** | `ForgeBuildError.__init__` with `cause` param (21-22) |
| `forge/runner.py` | 28% | **Thin** | Entire `build()` function body — partially requires Blender, partially does not |
| `gate/gate.py` | 90% | **Strong** | Edge branches in `_check_vrchat()` (186, 252-257) and `_check_vtube()` (271) |
| `gate/models.py` | 96% | **Strong** | `ComplianceRule.__init__` severity-validation error branch (97-98) |
| `gate/vrm_reader.py` | 90% | **Strong** | JSON-fallback path for non-binary glTF (62-63); UTF-8 decode error (102-103) |
| `hoard/bootstrap.py` | 0% | **Untested** | Entire file |
| `hoard/exceptions.py` | 60% | **Thin** | `AssetNotFoundError.__init__` multi-field variant (34-39) |
| `hoard/local.py` | 91% | **Strong** | `_load_catalog()` YAML parse path (line 54, 59); `resolve()` not-cached branch (line 118) |
| `loom/exceptions.py` | 100% | **Strong** | — |
| `loom/loader.py` | 94% | **Strong** | OSError in `_load_file()` (114-115); unexpected exception in `_validate()` (148-149) |
| `loom/schema.py` | 98% | **Strong** | `to_file()` OS error path (281, 321-322) |
| `loom/validator.py` | 0% | **Untested** | Entire file — AND never called anywhere |
| `oracle_eye/eye.py` | 36% | **Thin** | Entire `render()` function body — partially requires Blender, partially does not |

---

## Section 4 — Cross-Cutting Themes

**Theme 1: Bridge layer is an untested black box.** All three concrete bridge implementations (Mjöll, Rúnstafr, Straumur) sit at 0% coverage. The domain internals are well-tested; the translation layer between protocol input and `BuildRequest` construction is completely untested. Any mistake in how a bridge parses its protocol, constructs the request, or serializes the response is invisible to the test suite. This is the layer most likely to diverge across agent integrations.

**Theme 2: "Never raises" contracts are implemented with `print()` rather than `logger`.** The Annáll adapters correctly swallow failures to protect callers, but they do so with `print(..., file=sys.stderr)` rather than `logger.warning()`. This means the silent-swallow behavior bypasses the Python logging system entirely — an operator who configures a structured log handler will never see Annáll warning messages. The RULES.AI.md standard ("no `print()`; use loggers only") is violated in four places in production code.

**Theme 3: Resource cleanup is inconsistently scoped.** The Forge correctly cleans up its temp directory in a `finally` block, but only for the second `try` block — not for the first (H-001). The Blender subprocess has a `process.kill()` path but no bounded post-kill wait (H-002). The REST server creates a new database connection on every request rather than a shared one (H-014). These are three distinct patterns of resource management that share a common root: the lifecycle of external resources (files, processes, connections) is not managed with a single clear ownership boundary.

**Theme 4: No path containment checks on any user-controlled path.** Three entry points accept paths from external callers (REST body `vrm_path`, REST body `output_dir`, Hoard catalog `filename`) without verifying the paths are contained within expected directories. The catalog traversal (H-003) is the most dangerous because it reaches into the Forge pipeline itself. The REST `vrm_path` (H-004) allows arbitrary file reads. These represent a consistent gap: path-building code uses `.resolve()` for normalization but never `.relative_to()` for containment.

**Theme 5: Coverage gaps cluster in the "how to run" code, not the "what to compute" code.** The mathematical and validation logic (gate rules, schema validation, VRM parsing) is well-covered (84-98%). The operational infrastructure (how to start, configure, connect, clean up) is poorly covered (0-36%). This means the codebase has verified that the forge's logic is correct but not that the forge can be reliably started, configured, and shut down in production.

---

## Section 5 — Carry-Forward from Genesis

These items from AUDIT_GENESIS.md remain open per D-008's explicit deferral to v0.1.1:

| Genesis finding | Status in HEAD | Notes |
|---|---|---|
| AUDIT-001 (DOMAIN_MAP `from_file` naming) | Closed — corrected per Phase 7 Scribe work | |
| AUDIT-002 (dispatch signature underdocumented) | Closed — INTERFACE_AMENDMENT written | |
| AUDIT-003 partial: `seidr check` → `seidr inspect` | Closed — D-008 ratifies `seidr inspect` | |
| AUDIT-003 partial: `seidr list-assets` missing | **Open (H-022)** — deferred to v0.1.1 per D-008 | |
| AUDIT-003 partial: `seidr bootstrap-hoard` undocumented | **Open (H-023)** — deferred to v0.1.1 per D-008 | |
| AUDIT-004 (platform hints in Python) | Closed — moved to config/defaults.yaml | |
| AUDIT-005 (Annáll injection inconsistency) | Closed — Loom and Hoard now accept annall param | |
| AUDIT-006 (D-002 unverifiable) | Closed — documented in DEVLOG | |
| AUDIT-007 (Claude Code SKILL.md vs manifest.yaml) | Closed — noted in amendment | |
| AUDIT-008 (silent polycount skip) | Closed — advisory WARNINGs now emitted | |
| AUDIT-009 (render script uses os.path.join) | **Verify** — `oracle_eye/scripts/render_avatar.py:125` was the target. Not re-audited in this pass (file not in coverage run — runs in Blender's embedded Python) | |
| AUDIT-010 (DOMAIN_MAP linear notation) | Closed — corrected per Phase 7 Scribe work | |

---

## Section 6 — Punch List

All findings ordered by severity for Phase B (Forge Worker).

| ID | Severity | Domain | File:line | Category | Owner |
|---|---|---|---|---|---|
| H-001 | **High** | forge | `forge/runner.py:132-185` | Resource leak | Forge Worker |
| H-002 | **High** | _internal | `_internal/blender_runner.py:250-254` | Resource leak/concurrency | Forge Worker |
| H-003 | **High** | hoard | `hoard/local.py:122` | Path safety/Security | Forge Worker |
| H-004 | **High** | bridges/straumur | `bridges/straumur/api.py:181` | Security/Input validation | Forge Worker |
| H-005 | **High** | bridges/straumur | `bridges/straumur/api.py:299` | Security | Forge Worker |
| H-006 | **Medium** | _internal | `_internal/blender_runner.py:234-235` | Error handling | Forge Worker |
| H-007 | **Medium** | loom | `loom/validator.py:1-135` | Orphaned code | Forge Worker / Scribe |
| H-008 | **Medium** | annall/config | `config/defaults.yaml:39`, `annall/factory.py` | Dead config | Forge Worker |
| H-009 | **Medium** | bridges/runstafr | `bridges/runstafr/cli.py:137-146` | Redundant work | Forge Worker |
| H-010 | **Low** | annall | `annall/adapters/sqlite.py:102` | Error handling | Forge Worker |
| H-011 | **Low** | annall, hoard | sqlite.py:86,129,150,170; file.py:62 | Error handling | Forge Worker |
| H-012 | **Low** | hoard/bootstrap | `hoard/bootstrap.py:147-153` | Security | Forge Worker |
| H-013 | **Low** | hoard | `hoard/local.py:51-73` | Input validation | Forge Worker |
| H-014 | **Low** | bridges/straumur | `bridges/straumur/api.py:101-106` | Resource/Performance | Forge Worker |
| H-015 | **Notable** | _internal | `_internal/blender_runner.py:238-253` | Other | Scribe (doc) |
| H-016 | **Notable** | gate, loom | `gate/gate.py:31`, `loom/validator.py:26` | Path safety | Forge Worker |
| H-017 | **Notable** | forge, oracle_eye | `forge/runner.py`, `oracle_eye/eye.py` | Test quality | Forge Worker |
| H-018 | **Notable** | bridges (all) | mjoll/server.py, runstafr/cli.py, straumur/api.py | Test quality | Forge Worker |
| H-019 | **Notable** | annall | `annall/factory.py` | Test quality | Forge Worker |
| H-020 | **Notable** | hoard/bootstrap | `hoard/bootstrap.py` | Test quality | Forge Worker |
| H-021 | **Low** | config | `config.py:36-131` | Test quality | Forge Worker |
| H-022 | **Notable** | bridges/runstafr | INTERFACE.md | Doc drift (tracked, D-008) | Forge Worker (v0.1.1) |
| H-023 | **Notable** | bridges/runstafr | INTERFACE.md | Doc drift (tracked, D-008) | Scribe (v0.1.1) |

---

## Section 7 — Verdict

The codebase has advanced meaningfully since the genesis audit. All ten genesis findings are addressed. The pipeline wires correctly, the sacred principles hold structurally, and the 159 non-Blender tests pass cleanly. The domains with the most risk in production — the Loom schema, the Gate, and the Annáll adapter — are well-tested and behave correctly.

**The riskiest finding is H-003** (path traversal in `hoard/local.py:122`): a crafted catalog entry can cause `resolve()` to return a path outside the Hoard's `bases_dir`, which the Forge then opens and passes to Blender. This is a containment boundary failure at a data-trusted input point. The fix is additive, targeted, and small — one `relative_to()` check after `.resolve()` — but until it lands, anyone who can modify `data/hoard/catalog.yaml` can direct the Forge to read arbitrary filesystem paths.

**H-001** (temp directory leak on write failure) and **H-002** (unbounded post-kill `communicate()`) are the two resource lifetime failures that will manifest under real load. H-001 is triggered by a disk-full condition during a build; H-002 is triggered by a Blender process that does not terminate promptly after `kill()` on Windows. Both are fixable in a single focused session.

**H-005** (REST server binds `0.0.0.0` by default) must be addressed before any deployment that connects Straumur to a network. An agent-only forge should not be reachable from outside `localhost` without explicit operator configuration.

The **bridge layer at 0% coverage** is the largest unverified surface area. It is not a safety issue today (all dispatch logic is tested indirectly), but it is a maintenance liability: any future change to CLI argument parsing, REST request deserialization, or MCP tool schema is invisible to the test suite.

Will the codebase survive Volmarr's first real Blender run with a real spec? **Yes, with caveats.** The pipeline logic is sound. The three immediate risks to the first real run are: (1) `BlenderNotFoundError` if Blender is not on PATH and not configured — the runner will fail loudly with a clear diagnostic (good); (2) the Hoard catalog file not seeded — bootstrap must be run first; (3) on Windows, if the Blender process hangs past timeout, the forge hangs indefinitely (H-002). Fix H-002 before the first real run.

---

*Sólrún Hvítmynd, Auditor — second forge audit, Phase A, 2026-05-06.*
*Twenty-three findings: five High, four Medium, six Low, eight Notable. The blade is sharper than the first audit left it. But five of those findings can bite on first contact with a real user.*
