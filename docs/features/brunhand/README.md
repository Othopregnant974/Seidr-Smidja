# Brúarhönd — Feature Overview
**True Name:** Brúarhönd ("Bridge-Hand") — the bridge that grew a hand to grip live GUI.
**Status:** v0.1 design complete (Skald + Architect + Cartographer scrolls written, ADR D-010 ratified). Forge Worker implementation in progress.
**Last updated:** 2026-05-06

---

## What Brúarhönd Is

An agent-driven, cross-machine remote-control surface that lets the forge reach into a running VRoid Studio session — even one on a different computer joined via Tailscale — and operate it through programmatic primitives (screenshot, click, type, drag, hotkey, save, export) so the agent can drive VRoid Studio's GUI as a hand reaching across the network.

## What Brúarhönd Is Not

- It is not a generic remote desktop tool. (Use Tailscale + RDP/VNC for that.)
- It is not a screen-sharing service for humans. (No human GUI is part of the forge.)
- It does not bypass Tailscale's encryption with a side channel.
- It does not retain commands or screenshots beyond what Annáll explicitly records.
- It does not replace the Forge's headless Blender pipeline. The two are lateral, not competing.

## The Two Halves

| Half | True Name | Where it runs | What it does |
|---|---|---|---|
| The far hand | **Horfunarþjónn** (Watching-Daemon) | The VRoid host machine | Listens on a Tailscale-reachable port; executes GUI primitives on the VRoid Studio session; returns screenshots and structured responses. |
| The reaching arm | **Hengilherðir** (Reaching Client) | The forge process | Holds bearer-tokened sessions to one or many daemons; calls primitives; routes screenshots through Ljósbrú into Oracle Eye for agent vision. |

## Quickstart for an Operator

### 1. Install the daemon on the VRoid host

```bash
pip install "seidr-smidja[brunhand-daemon]"
```

This installs the GUI automation extras (PyAutoGUI, MSS, pygetwindow, platform-specific accessibility libs).

### 2. Configure a bearer token

```bash
# On the VRoid host machine:
export BRUNHAND_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

Store the token securely. The forge will need the same token in its config.

### 3. Configure the daemon to bind the Tailscale interface

In `config/user.yaml` on the VRoid host:

```yaml
brunhand:
  daemon:
    bind_address: 100.x.y.z   # the host's Tailscale IP (run `tailscale ip` to find)
    port: 8848
    require_https: true
    cert_path: /path/to/self-signed.pem  # optional but recommended
```

For same-machine use (forge and VRoid Studio on one box), default `127.0.0.1` is correct and no Tailscale config is needed.

### 4. Start the daemon

```bash
python -m seidr_smidja.brunhand.daemon
```

Health probe (no auth required, by design — Sacred Law of bounded exception):

```bash
curl https://100.x.y.z:8848/v1/brunhand/health
```

### 5. Configure the forge to know about this host

In `config/user.yaml` on the forge machine:

```yaml
brunhand:
  hosts:
    - name: vroid-workstation
      address: vroid-host.tailnet.ts.net  # MagicDNS or Tailscale IP
      port: 8848
      token_env: BRUNHAND_TOKEN_VROID_WORKSTATION
```

Set the token on the forge side via the named env var.

### 6. Verify connectivity

```bash
seidr brunhand health vroid-workstation
seidr brunhand capabilities vroid-workstation
seidr brunhand screenshot vroid-workstation --out /tmp/probe.png
```

### 7. Drive VRoid Studio

```bash
# Open a project
seidr brunhand vroid-open vroid-workstation /path/to/project.vroid

# Take a screenshot to confirm
seidr brunhand screenshot vroid-workstation --out /tmp/loaded.png

# Export VRM
seidr brunhand vroid-export vroid-workstation /path/to/output.vrm
```

Or invoke programmatically through any forge bridge — Mjöll (MCP), Rúnstafr (CLI), Straumur (REST), or via Hermes/OpenClaw/Claude Code skill manifests.

## Three Modes of Use

- **Mode A — Brúarhönd only.** Agent invokes the forge with `request.brunhand` set, no Loom spec. Pure VRoid Studio control. Used for: GUI exploration, manual export, agent-as-VRoid-pilot.
- **Mode B — Forge only.** Agent invokes with a Loom spec, no Brúarhönd. Existing headless Blender pipeline runs. (See the project-level `docs/DATA_FLOW.md` for this path.)
- **Mode C — Both arms.** Agent invokes with both `request.spec` and `request.brunhand`. Bridge generates a shared `run_id`; both `dispatch()` and `brunhand_dispatch()` run sequentially; both Annáll sessions reference the same `run_id`. Used for: complex flows where VRoid Studio shapes the avatar, then headless Blender refines the export.

See `DATA_FLOW.md` for the full Mode A walkthrough (15 steps), Mode C diagrams, and all failure flows.

## Authentication — Defense in Depth

Two layers, both required:

1. **Tailscale ACL** — gates *which* devices on the tailnet can reach the daemon's port. Configured outside Seiðr-Smiðja (in your Tailscale admin console or `acl.json`). See `TAILSCALE.md` for recommended configuration.
2. **Bearer token** — gates *which requests* the daemon will execute even from approved devices. Validated by `Gæslumaðr` middleware using constant-time comparison. Missing or wrong token → HTTP 401 + Annáll WARN event.

Compromise of either layer alone does not compromise the daemon.

## Vision Feedback — Through Oracle Eye

Every primitive that visibly affects the screen (most of them) can be followed by `screenshot()`. Daemon screenshots return as PNG bytes in the response, routed through `Ljósbrú` into Oracle Eye via `register_external_render(source="brunhand", view=..., png_bytes=..., metadata=...)`. The agent sees them through the same vision channel as Blender renders — there is no "remote view" vs "local view" distinction in the agent's perception.

## Reading Order for an Operator or Agent

1. This README — orientation.
2. `VISION.md` — soul, central image, Primary Rite.
3. `PHILOSOPHY_ADDENDUM.md` — feature-specific principles (The Hand Asks Permission, etc.).
4. `ARCHITECTURE.md` — daemon/client split, dispatch seam, internals.
5. `DATA_FLOW.md` — request flows, vision loop, all failure flows, two-Annáll topology.
6. `TAILSCALE.md` — recommended ACL setup.
7. `../../src/seidr_smidja/brunhand/INTERFACE.md` — top-level domain contract.
8. `../../src/seidr_smidja/brunhand/daemon/INTERFACE.md` — HTTP API contract.
9. `../../src/seidr_smidja/brunhand/client/INTERFACE.md` — Python client API.
10. `../../docs/DECISIONS/D-010-brunhand-feature-genesis.md` — the genesis ADR for this feature.

## Status

| Phase | Status |
|---|---|
| Phase 1 — Vision (Skald) | ✅ Complete |
| Phase 2 — Bones (Architect) | ✅ Complete |
| Phase 3 — Rivers (Cartographer) | ✅ Complete |
| Phase 4 — Memory mid-ritual (Scribe) | ✅ Complete (this document, TAILSCALE.md, ADR D-010) |
| Phase 5 — Forge (Forge Worker) | 🔨 In progress |
| Phase 6 — Audit (Auditor) | ⏳ Pending |
| Phase 7 — Close (Scribe) | ⏳ Pending |
