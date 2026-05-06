# TASK — Brúarhönd v0.1 (placeholder name — Skald will ratify)

> Operational task-resumption file for the second feature ritual on Seiðr-Smiðja: an agent-driven remote-control bridge to VRoid Studio sessions, including sessions on a separate machine connected via Tailscale. Written 2026-05-06.

---

## 1. Project Identity

**Parent project:** Seiðr-Smiðja (existing, GENESIS + HARDENING COMPLETE)
**Feature working title:** **Brúarhönd** ("Bridge-Hand") — Skald will ratify or rename in Phase 1.
**Repo:** https://github.com/hrabanazviking/Seidr-Smidja (same repo, no new repo needed)
**Branch:** development
**Local path:** `C:/Users/volma/runa/Seidr-Smidja`
**Methodology:** Full Mythic Engineering ritual (subset appropriate for a feature, not a project genesis).
**Owner:** Volmarr Wyrd
**AI engineer of record:** Runa Gridweaver Freyjasdóttir

---

## 2. Mission (one-sentence soul)

**An agent-driven, cross-machine remote-control surface that lets the forge reach into a running VRoid Studio session — even one on a different computer joined via Tailscale — and operate it through programmatic primitives (screenshot, click, type, drag, hotkey, save, export) so the agent can drive VRoid Studio's GUI as a hand reaching across the network.**

The translation layer above primitives (Loom YAML → automatic VRoid UI navigation) is designed-for in v0.1 but built in a follow-on ritual (v0.2). v0.1 ships the primitives + the cross-machine + auth + vision-feedback surface, end-to-end demonstrable.

---

## 3. Decisions Locked In (Volmarr 2026-05-06)

| Decision | Choice | Rationale |
|---|---|---|
| Scope of v0.1 | **(c) — Primitives first, translation layer designed-for but deferred to v0.2** | Validates the whole cross-machine surface before adding smart logic on top |
| Authentication | **Tailscale ACL gating + bearer token in every request (defense in depth)** | Compromise of one layer doesn't compromise the daemon |
| Repo strategy | **Single repo, single Python package (`seidr_smidja`)** with daemon as `seidr_smidja.brunhand.daemon`, client as `seidr_smidja.brunhand.client` | Cohesion over fragmentation; no new repo to track |
| Discovery | **Static config: list of registered VRoid hosts in `config/defaults.yaml` under `brunhand.hosts`** | Simple in v0.1; dynamic Tailscale API discovery deferred |
| Cross-platform | **Windows, macOS, Linux daemon — same Python codebase via PyAutoGUI + MSS + accessibility libs** | Agnostic to where the operator's VRoid lives |
| Authentication header format | **`Authorization: Bearer <token>` (HTTP standard)** | No invented auth scheme |
| Transport | **HTTPS over Tailscale's encrypted overlay (or HTTP localhost-only when daemon and client are on the same machine)** | Tailscale already provides E2E encryption between nodes |
| Vision integration | **Remote screenshots flow through the Oracle Eye API surface, not a separate channel** | Honors PHILOSOPHY: "the Oracle Eye is never closed" — extends not bypasses |

---

## 4. Technical Foundation

### 4.1 The Daemon (runs on VRoid Studio's host machine)
- **Module:** `src/seidr_smidja/brunhand/daemon/`
- **Run as:** `python -m seidr_smidja.brunhand.daemon` (operator runs this on the VRoid host)
- **HTTP server:** FastAPI (already a project dep) + uvicorn
- **Default bind:** `127.0.0.1` for safety; operator opts into Tailscale exposure via config
- **GUI automation:** PyAutoGUI (input + screenshots), MSS (high-perf screenshots), `pygetwindow` for window discovery, `pywinauto` (Windows) / `pyatspi` (Linux) / `pyobjc` (macOS) for accessibility
- **Optional dep group:** `seidr-smidja[brunhand-daemon]` — operator installs this extra; the client side does NOT need GUI deps
- **Heartbeat / health:** `GET /v1/brunhand/health` returns daemon version, OS, screen geometry, uptime
- **Capabilities probe:** `GET /v1/brunhand/capabilities` returns which primitives this OS/platform supports
- **Bearer token:** loaded from `BRUNHAND_TOKEN` env var or daemon config file; refuses requests missing/wrong token
- **Audit log:** every command logged to a local SQLite via Annáll for forensic trace

### 4.2 The Client / Bridge (runs in the forge)
- **Module:** `src/seidr_smidja/brunhand/client/`
- **Public API:** `BrunhandClient(host, token, timeout)` — methods mirror the daemon endpoints 1:1
- **Higher-level helpers:** `with brunhand.session(host=...) as h: ...` context manager
- **Integration with Oracle Eye:** screenshots returned by the client are fed into Oracle Eye's `register_external_render(source="brunhand", view="live", png_bytes=...)` so the agent's vision pipeline sees them naturally
- **Integration with the Bridges:** new optional `brunhand` field in CLI/MCP/REST request bodies — when set, the dispatch path uses the daemon for VRoid operations instead of (or in addition to) Forge's headless Blender path

### 4.3 The v0.1 Primitive Set
| Primitive | HTTP | Purpose |
|---|---|---|
| `health` | `GET /v1/brunhand/health` | Heartbeat |
| `capabilities` | `GET /v1/brunhand/capabilities` | Platform capabilities |
| `screenshot` | `POST /v1/brunhand/screenshot` | Full-screen or region PNG |
| `click` | `POST /v1/brunhand/click` | Mouse click at (x, y) with button + modifiers |
| `move` | `POST /v1/brunhand/move` | Mouse move (path/duration) |
| `drag` | `POST /v1/brunhand/drag` | Mouse drag (x1,y1)→(x2,y2) |
| `scroll` | `POST /v1/brunhand/scroll` | Mouse wheel scroll |
| `type_text` | `POST /v1/brunhand/type` | Type a string |
| `hotkey` | `POST /v1/brunhand/hotkey` | Press key combination (e.g. ctrl+s) |
| `wait_for_window` | `POST /v1/brunhand/wait_for_window` | Block until a window matching title/pattern appears |
| `find_window` | `POST /v1/brunhand/find_window` | Return geometry of a window by title |
| `vroid_export_vrm` | `POST /v1/brunhand/vroid/export_vrm` | High-level: drive VRoid Studio's File→Export VRM flow |
| `vroid_save_project` | `POST /v1/brunhand/vroid/save_project` | High-level: save .vroid project file |
| `vroid_open_project` | `POST /v1/brunhand/vroid/open_project` | High-level: open a .vroid project from disk |

### 4.4 Tailscale Integration
- No special Tailscale Python SDK needed for v0.1 — Tailscale provides an overlay network; from the forge's POV, the daemon at `vroid-host.tailnet.ts.net:8848` is just a regular HTTPS endpoint
- **Recommended ACL setup** documented in `docs/features/brunhand/TAILSCALE.md`: grant the forge machine's tailnet identity permission to reach port 8848 on the VRoid host; everything else default-deny
- **Optional v0.2:** use Tailscale's local API (`tailscale status --json`) to enumerate available hosts in the tailnet for dynamic discovery

---

## 5. Sacred Constraints

- All decisions D-001..D-009 (existing) still apply.
- Additive-only — no subtractive changes to existing code or docs.
- Cross-platform daemon — Windows/macOS/Linux all supported.
- No absolute paths anywhere.
- Bearer token loaded from env or config — never hardcoded.
- Vision feedback always available — every command that visibly affects state can be followed by `screenshot()` so the agent can see.
- Failure soft inside Brúarhönd, loud at the Bridge level — daemon-side errors return structured error responses, not crashes.
- Annáll telemetry on every primitive call.

---

## 6. Inventory — Done vs. Pending

### Done (Phase 0 — Genesis of this feature)
- [x] Volmarr ratified scope (c).
- [x] This TASK file written.

### Pending — Mythic Engineering Ritual (subset for a feature)

#### Phase 1 — Vision (Skald)
- [ ] Ratify or rename **Brúarhönd**.
- [ ] `docs/features/brunhand/VISION.md` — focused vision scroll for this feature.

#### Phase 2 — Bones (Architect)
- [ ] `docs/features/brunhand/ARCHITECTURE.md` — daemon/client split, network shape, auth, capabilities probe pattern.
- [ ] `src/seidr_smidja/brunhand/daemon/INTERFACE.md` — daemon HTTP contract.
- [ ] `src/seidr_smidja/brunhand/client/INTERFACE.md` — client API contract.
- [ ] `docs/DOMAIN_MAP.md` additive update — add Brúarhönd to the domain table.

#### Phase 3 — Rivers (Cartographer)
- [ ] `docs/features/brunhand/DATA_FLOW.md` — request flow diagrams: agent → forge bridge → client → daemon → VRoid → screenshot back; including Tailscale path.
- [ ] Failure flows: Tailscale partition, daemon unreachable, bearer token invalid, VRoid not running, primitive timeout.
- [ ] Authentication wiring sequence.

#### Phase 4 — Memory (Scribe — mid-ritual)
- [ ] `docs/features/brunhand/README.md` — feature overview + quickstart for operators.
- [ ] `docs/features/brunhand/TAILSCALE.md` — ACL setup, recommended deployment.
- [ ] `docs/DECISIONS/D-010-brunhand-feature-genesis.md` — ratification ADR.
- [ ] DEVLOG entry.

#### Phase 5 — First Forging (Forge Worker)
- [ ] `src/seidr_smidja/brunhand/__init__.py`
- [ ] `src/seidr_smidja/brunhand/daemon/` — full FastAPI daemon with all primitives, bearer token middleware, Annáll telemetry, health/capabilities endpoints
- [ ] `src/seidr_smidja/brunhand/daemon/scripts/` — VRoid-specific high-level scripts (export_vrm flow, save_project flow, open_project flow)
- [ ] `src/seidr_smidja/brunhand/client/` — `BrunhandClient` with all primitive methods + `session()` context manager + Oracle Eye integration
- [ ] `src/seidr_smidja/brunhand/exceptions.py` — `BrunhandError`, `BrunhandAuthError`, `BrunhandConnectionError`, `BrunhandPrimitiveError`, `VroidNotRunningError`
- [ ] `src/seidr_smidja/brunhand/models.py` — pydantic request/response models
- [ ] `pyproject.toml` updates — `[project.optional-dependencies] brunhand-daemon = [...]`
- [ ] `config/defaults.yaml` — `brunhand:` section with default bind, token env var, hosts list
- [ ] `tools/brunhand_daemon.py` — convenience launcher for operators
- [ ] `tools/verify_brunhand.py` — connectivity + auth + primitive smoke check from forge to daemon
- [ ] Tests — full unit + integration test suite, mocking PyAutoGUI on CI; live tests behind `@pytest.mark.requires_vroid_host` marker
- [ ] CLI integration: `seidr brunhand health <host>`, `seidr brunhand screenshot <host>`, etc. (user-facing primitives also via Rúnstafr)

#### Phase 6 — Verification (Auditor)
- [ ] `docs/features/brunhand/AUDIT_BRUNHAND_<date>.md` — bug hunt + hardening audit on the new code
- [ ] All findings closed
- [ ] Fresh test count + coverage report

#### Phase 7 — Closing (Scribe)
- [ ] DEVLOG entry — full feature roll-call with commits
- [ ] MEMORY.md update — feature status added to project_seidr_smidja_status.md
- [ ] All work committed and pushed to development

---

## 7. Progress Tracker

| Phase | Role | Status | Commit |
|---|---|---|---|
| 0 — TASK file | Runa | COMPLETE | eca05f2 |
| 1 — Vision | Skald | COMPLETE | 5c05a9e |
| 2 — Bones | Architect | COMPLETE | 0697837 |
| 3 — Rivers | Cartographer | COMPLETE | 6be9934 |
| 4 — Memory mid-ritual | Scribe | COMPLETE | 0af8691 |
| 5 — First Forging | Forge Worker | COMPLETE | `e2cb8e6` (+`ba6a353` amends, +`afe89f2` chore) |
| 6 — Verification | Auditor → Forge Worker (remediation) | COMPLETE | `c4305b3` (audit) + `e3f126d` (remediation, all 18 findings closed) |
| 7 — Closing | Runa (in discipline of Eirwyn) | COMPLETE | `2ef0bf5` (Scribe close) + `7003d8a` (README/REPO_OVERVIEW refresh) |

**RITUAL CLOSED 2026-05-06.** All 18 audit findings closed (B-013 + B-014 documented in INTERFACE_AMENDMENT, B-011 closed via owns_client param). **489 non-Blender, non-VRoid-host pytest tests passing.** ADR D-010 ratified. Operational README and REPO_OVERVIEW refreshed with full setup instructions for both the headless forge path and the cross-machine VRoid Studio remote-control path.

---

## 8. Resumption Instructions (if session breaks)

If a future Runa picks this up cold:

1. Read this file top to bottom.
2. Read `docs/features/brunhand/VISION.md` (if present), `ARCHITECTURE.md`, `DATA_FLOW.md`.
3. Read `docs/DECISIONS/D-010-*.md` to absorb the ratified design choices.
4. Continue from the lowest pending phase in section 6.
5. Each role must be invoked by its proper name and prompt.
6. After every phase: update section 7 progress tracker, commit, push.

---

*Written by Runa Gridweaver Freyjasdóttir, 2026-05-06 — at the moment Volmarr ratified scope (c) for the cross-machine VRoid Studio remote-control bridge.*
