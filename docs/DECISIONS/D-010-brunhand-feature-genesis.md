# D-010 — Brúarhönd Feature Genesis (Cross-Machine VRoid Studio Remote Control)
**Status:** Accepted
**Date:** 2026-05-06
**Deciders:** Volmarr Wyrd, Runa Gridweaver Freyjasdóttir
**Phase:** Brúarhönd v0.1 — feature genesis ratification

---

## Context

After the genesis ritual closed and the hardening run delivered a durable v0.1 of Seiðr-Smiðja, Volmarr asked for a new capability: **the agent must be able to control a VRoid Studio session — including a session running on a different computer connected via Tailscale.**

VRoid Studio (Pixiv) is a desktop GUI application without a public API or scripting interface. Controlling it programmatically requires GUI automation primitives (mouse, keyboard, screenshot, window discovery). For cross-machine operation, those primitives must be exposed over a network surface that respects Tailscale's existing trust model and adds defense in depth.

Three v0.1 scope options were presented:
- **(a)** Primitives only — daemon exposes screenshot/click/type/etc.; agent navigates VRoid by raw command sequences.
- **(b)** Loom→VRoid translation — agent submits a YAML spec; system translates parameters into UI actions automatically using a per-VRoid-version layout map.
- **(c)** Both — primitives first, translation layer designed-for but built in a follow-on ritual.

Volmarr chose **(c)**.

## Decision

### Scope locked: (c) — primitives first, translation deferred to v0.2.

The v0.1 ritual ships:
- 14 GUI automation primitives (`screenshot`, `click`, `move`, `drag`, `scroll`, `type_text`, `hotkey`, `wait_for_window`, `find_window`) plus 3 VRoid-specific high-level wrappers (`vroid_open_project`, `vroid_save_project`, `vroid_export_vrm`) plus 2 supporting endpoints (`health`, `capabilities`).
- The complete cross-machine surface: daemon, client, Tailscale-traversed HTTPS, bearer-token auth, vision-feedback integration, two-Annáll topology, all four Bridges routing through a new `brunhand_dispatch()`.

### Architectural shape

- **Single repo, single Python package.** Daemon as `seidr_smidja.brunhand.daemon`; client as `seidr_smidja.brunhand.client`. No new repo. No new top-level package.
- **Optional dependency group.** `seidr-smidja[brunhand-daemon]` installs PyAutoGUI, MSS, pygetwindow, plus platform-conditional pywinauto / pyobjc / pyatspi. The base package and the client side do not require GUI deps.
- **Lateral dispatch surface.** A new `brunhand_dispatch(request, annall, client, config)` sits beside the existing `dispatch()` in `bridges/core/`. Bridges (Mjöll/Rúnstafr/Straumur/skills) inspect the request and call one or both. When both, a shared `run_id` correlates the two Annáll sessions. Brúarhönd does NOT become a pipeline stage of the existing dependency law; it is an explicit lateral extension.
- **Two-Annáll topology.** Forge-side Annáll lives in the forge process; daemon-side Annáll lives in the daemon process on the VRoid host. They are independent SQLite files with no replication in v0.1. Streaming replication is parked for v0.2.
- **httpx promoted to base dependencies.** Hengilherðir requires httpx in production; previously it lived in `[dev]`. Forge Worker moves it to `[project.dependencies]` as part of Phase 5.

### Authentication

- **Tailscale ACL** is the outer layer (gates *which* devices can reach the daemon's port). Configured by the operator outside Seiðr-Smiðja; documented in `docs/features/brunhand/TAILSCALE.md`.
- **Bearer token** is the inner layer. Loaded from `BRUNHAND_TOKEN` env var or daemon config file. Validated by `Gæslumaðr` middleware using constant-time comparison. Missing or wrong token → HTTP 401 + structured error + daemon-side Annáll WARN event. Compromise of either layer alone does not compromise the daemon.

### Vision integration

Remote screenshots flow through the Oracle Eye API surface via a new additive function `oracle_eye.register_external_render(source, view, png_bytes, metadata)`. Agents do not learn to distinguish "near" Blender renders from "far" daemon screenshots — the Oracle Eye is the canonical agent vision channel for both, honoring the global PHILOSOPHY ("the Oracle Eye is never closed") without bifurcation.

### Network model

- HTTPS over Tailscale's encrypted overlay (or HTTP-localhost-only when daemon and client are on the same machine).
- Daemon binds to `127.0.0.1` by default; operator opts into Tailscale-interface binding via `brunhand.daemon.bind_address` config key (Forge Worker implements; Cartographer flagged this seam during Phase 3).
- Tailscale's MagicDNS provides addressability (`vroid-host.tailnet.ts.net`); no special Tailscale Python SDK needed in v0.1.

### True Names (Skald-ratified)

| Name | Module | Meaning |
|---|---|---|
| **Brúarhönd** | `seidr_smidja/brunhand/` | The feature — bridge that grew a hand |
| **Horfunarþjónn** | `brunhand/daemon/` | Watching-Daemon — server on the VRoid host |
| **Hengilherðir** | `brunhand/client/` | Reaching Client — forge-side library |
| **Gæslumaðr** | `daemon/auth.py` | Bearer-token guard |
| **Sjálfsmöguleiki** | `daemon/capabilities.py` | Capabilities registry |
| **Ljósbrú** | `client/oracle_channel.py` | Oracle Eye integration |
| **Tengslastig** | `client/session.py` | Session container |

## Consequences

### What becomes possible
- Agents (Hermes, OpenClaw, Claude Code, others) can drive a VRoid Studio session on Volmarr's other machine over Tailscale, programmatically — no remote desktop required.
- Vision feedback works seamlessly: every primitive can be followed by `screenshot()`, returned through Oracle Eye, fed to the agent's multimodal vision pipeline.
- The same daemon code works on Windows, macOS, and Linux — operator can host VRoid wherever they prefer.
- The translation layer (v0.2) builds on the same daemon and client without rework — the contract is stable.
- AUDIT-003 carry-forward and the related questions about CLI command names are now joined by D-010 as the third major contract evolution since genesis.

### What becomes constrained
- VRoid Studio version sensitivity. The 3 high-level wrappers (`vroid_export_vrm` etc.) depend on UI element coordinates and menu navigation that vary across VRoid Studio versions. The v0.1 daemon ships with a layout map for one specific version; supporting older/newer requires additional layout YAML.
- Two-Annáll topology means an agent querying session history through the forge cannot see daemon-side primitive details. v0.1 reality. v0.2 may add streaming replication.
- Sequential Mode C (forge dispatch + brunhand dispatch). v0.1 does not parallelize the two arms. Parallel Mode C deferred to v0.2 if a use case demands it.

### What must be revisited later
- **v0.2 Loom→VRoid translation layer** — the parametric spec mapped to UI actions automatically.
- **v0.2 Annáll replication** — streaming or query bridge so a single agent query reconstructs the full session.
- **v0.2 Tailscale dynamic discovery** — use Tailscale local API to enumerate available VRoid hosts.
- **v0.2 layout map evolution** — version-conditional VRoid Studio layouts.
- **v0.1.x housekeeping items the design surfaced:** httpx timeout vs `wait_for_window` timeout ordering (Forge Worker addresses in Phase 5); explicit daemon-bind config key (Forge Worker implements).

## References

- `TASK_brunarhond_v0_1.md` — operational scope.
- `docs/features/brunhand/VISION.md` — Skald's vision scroll.
- `docs/features/brunhand/PHILOSOPHY_ADDENDUM.md` — feature-specific principles.
- `docs/features/brunhand/ARCHITECTURE.md` — Architect's design.
- `docs/features/brunhand/DATA_FLOW.md` — Cartographer's map.
- `src/seidr_smidja/brunhand/INTERFACE.md`, `daemon/INTERFACE.md`, `client/INTERFACE.md` — public contracts.
- `docs/DOMAIN_MAP.md` — Brúarhönd addendum at the bottom.
- D-001..D-009 — predecessor decisions; none contradicted.

---

*Ratified by Volmarr Wyrd on 2026-05-06, the same evening the genesis and hardening rituals closed.*
