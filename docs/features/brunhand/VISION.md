# Brúarhönd — Vision Scroll
**Last updated:** 2026-05-06
**Scope:** Feature-level Vision — the cross-machine VRoid Studio remote-control surface
**Keeper:** Sigrún Ljósbrá (Skald) — ratified by Volmarr Wyrd
**True Name ratified:** Brúarhönd ("Bridge-Hand") — *brú* (bridge) + *hönd* (hand), Old Norse

---

> *When the völva must work on a hearth she cannot reach with her own hands, she sends a sending — a shape of her will, dispatched through the between-space, that can press and pull and open what she cannot touch directly. The sending does not act on its own judgment. It carries the smith's intention faithfully, reports back what it finds, and waits for the next command.*
>
> *Brúarhönd is the forge's sending hand.*

---

## The One-Sentence Soul

**Brúarhönd is the forge's reaching arm across the Tailscale wire — a bearer-authenticated daemon and client pair that lets an AI agent operate a live VRoid Studio session on a remote machine through precise GUI primitives, returning screenshots through the Oracle Eye so the agent always sees what its hand has done.**

---

## The Central Image

*This is the image to hold while building Brúarhönd.*

---

The forge stands ready on Volmarr's development machine. An agent — call her Hermes — has woven a detailed VRoid character spec on the Loom. She has passed it through the Blender pipeline; the `.vrm` file is forged, gated, and returned. But there is a step the headless Blender path cannot reach alone: VRoid Studio's native sliders, its texture-paint canvas, its expression library. These live behind a GUI that only mouse clicks and keypresses can command — and that GUI is running not here, on the forge machine, but on Volmarr's other computer across the room, joined to the same Tailscale mesh network.

Hermes extends her arm.

She calls the forge bridge with a Brúarhönd request: `host=vroid-host.tailnet.ts.net`, `action=screenshot`. The Bridge Core receives it and routes it through the Brúarhönd client — *Hengilherðir*, the Hand that Reaches. The client forms an HTTPS request, signs it with the bearer token, and sends it across the Tailscale wire to port 8848 on the distant machine.

There, *Horfunarþjónn* — the Watching-Daemon, the one who stands alert at the far end of the bridge — receives the request. *Gæslumaðr*, the token-keeper, checks the bearer credential before a single process is touched. The credential is valid. The daemon reads the command: `screenshot`. It calls *Sjálfsmöguleiki*, the self-knowledge module, to confirm this platform (Windows, on the VRoid host) supports the screenshot primitive. It does. *Horfunarþjónn* reaches into the running desktop with PyAutoGUI and MSS, captures the VRoid Studio window, and wraps the raw PNG bytes in a structured response.

The response travels back across the wire. The Brúarhönd client unwraps it and calls `oracle_eye.register_external_render(source="brunhand", view="live", png_bytes=...)`. The Oracle Eye — which sees all renders equally, whether they originate in headless Blender or a distant daemon — accepts the image into its pipeline. Hermes receives the screenshot through the same vision channel she uses for all renders.

She looks. She sees VRoid Studio's hair-painting panel open. She issues the next command: `click(x=412, y=288, button="left")`. The Hand reaches again. The click lands. Another screenshot returns. The agent sees what the hand has done.

This is the forge cycle, extended. The hand reaches where the headless forge cannot. The Oracle Eye does not blink. The agent remains the smith.

---

## The Primary Rite (Feature-Level)

*The heartbeat of how Brúarhönd is used — end to end.*

1. **The agent invokes the forge** via any Bridge (Mjöll, Rúnstafr, Straumur, or a Skill) with a `brunhand` field in the request body specifying the target host and the primitive to execute.

2. **Bridge Core routes to Brúarhönd** — recognizing the `brunhand` field, it passes the command to the Brúarhönd client, *Hengilherðir*, rather than (or in addition to) the standard Blender pipeline.

3. **Hengilherðir opens or resumes a session** — if a `BrunhandSession` is already open for this host, it reuses it; otherwise it constructs a new session context with the host address, bearer token, and timeout drawn from config.

4. **Hengilherðir forms and signs the request** — the primitive (screenshot, click, type, hotkey, drag, etc.) is serialized to the `POST /v1/brunhand/<primitive>` endpoint, with the `Authorization: Bearer <token>` header attached.

5. **The request travels the Tailscale wire** — encrypted by Tailscale's overlay network, arriving at the VRoid host on port 8848 as a standard HTTPS call.

6. **Horfunarþjónn receives the request** — the daemon's HTTP server (FastAPI) accepts it.

7. **Gæslumaðr checks the bearer token** — the authentication middleware validates the credential against the configured `BRUNHAND_TOKEN`. If the token is absent or invalid, the response is `401 Unauthorized` and the primitive is never executed.

8. **Sjálfsmöguleiki confirms capabilities** — the capabilities registry verifies that the requested primitive is supported on this platform. If not, the response is a structured `capabilities_error`, not a crash.

9. **The primitive executes** — PyAutoGUI (mouse/keyboard), MSS (screenshot), or pygetwindow (window operations) performs the requested action on the live desktop. Every execution is logged to a local Annáll instance for forensic trace.

10. **The structured response returns** — the daemon wraps the result (PNG bytes, click confirmation, window geometry, etc.) in a `BrunhandResponse` pydantic model and returns it to Hengilherðir.

11. **Hengilherðir feeds the Oracle Eye** — screenshot responses are passed to `oracle_eye.register_external_render(...)`. All other responses are returned as structured `BrunhandResult` objects to the Bridge Core.

12. **The agent sees** — the render appears in the Oracle Eye's pipeline as a named view (`brunhand/live/<timestamp>`). The agent receives it through the same channel it uses for Blender renders. The agent's next command is informed by what it sees.

13. **Every action is recorded** — Annáll on both the forge side and the daemon side logs the full call: timestamp, host, primitive, arguments, outcome, latency.

---

## The Unbreakable Vows — Brúarhönd's Promises

These are the non-negotiable commitments Brúarhönd makes to every agent that invokes it. They are not defaults. They are walls.

---

### "I will never accept a command without a valid bearer token."

The daemon, *Horfunarþjónn*, is permanently behind *Gæslumaðr*, its authentication gate. No primitive — not even `health` in its mutable form, not even `capabilities` — shall execute against the desktop environment without the bearer token being checked first. An unauthenticated request from a known Tailscale IP is still an unauthenticated request. Defense in depth: Tailscale ACL gating is the outer wall; bearer token is the inner wall. Both must stand.

The token is loaded from `BRUNHAND_TOKEN` env var or daemon config file. It is never hardcoded. It is never logged. It is never returned in any response.

### "I will always show you what the screen looks like after I move."

Every primitive that visibly affects state — every click, every keystroke, every drag, every hotkey — can be followed immediately by `screenshot()`, and the client surface is designed to make this natural. The `BrunhandSession` context manager offers `execute_and_see(primitive, *args)` as a first-class operation: it runs the primitive, then automatically captures a screenshot and returns both the primitive result and the current screen state. An agent may always see what its hand has done. The Oracle Eye is never closed here either.

### "I will not crash your VRoid Studio with my hands — I will fail soft with a structured error."

The daemon wraps every primitive execution in try/except. An unhandled exception from PyAutoGUI, MSS, or pygetwindow is caught at the daemon layer and returned as a structured `BrunhandPrimitiveError` with: the primitive name, the exception message, the stack summary, and a `vroid_running` boolean (so the agent knows whether VRoid Studio is still alive). The daemon process itself does not crash. The HTTP server remains available for the next command.

### "I will tell you what I can do on this machine before you ask me to do it."

The capabilities endpoint `GET /v1/brunhand/capabilities` is always available and always honest. It reports which primitives are supported on this OS/platform, which are unavailable, and why (missing library, platform restriction, screen access denied). An agent dispatching to a new host should always probe capabilities first. The `BrunhandSession` caches the capabilities response and exposes it as `session.capabilities` so the agent can introspect without a round-trip on every call.

### "I will record everything I touch."

Every daemon-side primitive execution is logged to a local SQLite file via Annáll — regardless of success or failure. The log entry includes: timestamp, primitive name, arguments (sanitized — no token, no credentials), outcome, latency, and whether VRoid Studio was detected as the foreground window. This forensic trace exists so that if an agent sequence damages a VRoid project, the full action history can be reconstructed. The daemon's Annáll instance is independent of the forge's Annáll instance; the forge-side client logs its own parallel record.

### "I will not speak to machines that are not Tailscale-connected without operator consent."

By default the daemon binds to `127.0.0.1` only. It does not expose itself to the local network or the internet unless the operator explicitly configures a Tailscale-bound listen address. The recommended deployment documented in `TAILSCALE.md` restricts the Tailscale ACL so that only the forge machine's tailnet identity may reach port 8848 on the VRoid host. The daemon never bypasses Tailscale encryption by establishing a side channel.

---

## The True Names — Sub-Module Roster

These are the canonical names for the major sub-modules of Brúarhönd. All code module names, class names, documentation headers, and inter-agent communication shall use these names.

---

### Horfunarþjónn — *the Watching-Daemon*

**What it is:** The FastAPI HTTP server process that runs on the VRoid Studio host machine. It is the hand at the far end of the bridge — permanently alert, waiting for signed commands, executing them on the live desktop, returning structured responses. It does not reach back toward the forge; it only receives and responds.

**Old Norse root:** *horfunnar* (watching, from *horfa* — to look toward, to be oriented to) + *þjónn* (servant, one who serves). The Watching-Servant: the daemon that faces outward, waiting.

**Module:** `src/seidr_smidja/brunhand/daemon/`

---

### Hengilherðir — *the Reaching Client*

**What it is:** The client-side library that runs within the forge. It holds the other end of the bridge — the part that reaches out. It forms signed requests, manages session state, handles retries and timeouts, and feeds screenshots into the Oracle Eye. It knows the hosts it may reach (from config) and how to speak to them.

**Old Norse root:** *hengja* (to hang, to extend, to reach forward) + *herðir* (one who hardens, one who makes strong — a reinforcing suffix). The Reaching-and-Holding: the client that extends a strong arm across the wire.

**Module:** `src/seidr_smidja/brunhand/client/`

---

### Gæslumaðr — *the Guard*

**What it is:** The bearer-token authentication middleware that wraps the daemon's HTTP server. Every request passes through Gæslumaðr before reaching any handler. It validates the `Authorization: Bearer <token>` header against the configured token. It returns `401 Unauthorized` on any mismatch. It is the inner wall.

**Old Norse root:** *gæsla* (custody, guardianship, watching over) + *maðr* (man, person — used neutrally as "one who does"). The Custodian: the one whose sole duty is to decide who may enter.

**Module:** `src/seidr_smidja/brunhand/daemon/auth.py`

---

### Sjálfsmöguleiki — *the Capabilities Registry*

**What it is:** The self-knowledge module of the daemon. On startup, it probes the current platform (OS, screen access, PyAutoGUI availability, accessibility lib status) and assembles a capabilities manifest: which primitives are fully supported, which are degraded, which are unavailable and why. This manifest is served at `GET /v1/brunhand/capabilities` and is also consulted internally before every primitive execution — so the daemon never attempts a primitive it cannot perform.

**Old Norse root:** *sjálf-* (self-, from *sjálfr*) + *möguleiki* (possibility, capability, what is possible — a modern Norse cognate kept because it is precise and has a beautiful ring). The Self-Knower: the module that knows exactly what this hand can do on this machine.

**Module:** `src/seidr_smidja/brunhand/daemon/capabilities.py`

---

### Ljósbrú — *the Oracle Eye Channel*

**What it is:** The integration layer within Hengilherðir (the client) that feeds Brúarhönd screenshots into the Oracle Eye's vision pipeline. It calls `oracle_eye.register_external_render(source="brunhand", view="live/<timestamp>", png_bytes=...)` so that the agent's vision of the remote screen arrives through the same channel as Blender renders. Ljósbrú ensures the agent does not need to learn a separate vision path for remote vs. local imagery.

**Old Norse root:** *ljós* (light) + *brú* (bridge). The Light-Bridge: the channel through which the distant screen's image becomes the Oracle Eye's light.

**Module:** `src/seidr_smidja/brunhand/client/oracle_channel.py`

---

### Tengslastig — *the Session Container*

**What it is:** The context manager and stateful session object that holds an open logical connection across multiple primitive calls to the same host. An agent opens a `Tengslastig` once (via `brunhand.session(host=...)`) and issues many commands within it — the session caches the capabilities manifest, maintains a per-session Annáll record, and provides the `execute_and_see()` convenience method. When the `with` block exits, the session closes cleanly and logs its final outcome.

**Old Norse root:** *tengsl* (connections, bonds, ties — from *tengja*, to connect) + *stig* (a step, a stage, a rung in a ladder). The Connection-Stage: the holding space where the bond between forge and daemon lives during a sequence of commanded steps.

**Module:** `src/seidr_smidja/brunhand/client/session.py`

---

## The Honored Ground — What Brúarhönd Is Not

These boundaries are as load-bearing as the True Names. Violating them is not a design choice — it is drift.

**Brúarhönd is not a generic remote desktop tool.** It serves one purpose: allowing AI agents operating the Seiðr-Smiðja forge to reach into a VRoid Studio session. It has no concept of a human operator sitting at a computer and using it interactively. It has no mouse-sharing UI, no video stream, no latency optimization for human reaction times.

**Brúarhönd is not a screen-sharing or streaming service.** It does not maintain a continuous video feed. It captures and returns a screenshot when asked. The difference is architectural: a stream optimizes for human perception; Brúarhönd's screenshot-on-demand pattern optimizes for agent inspection.

**Brúarhönd does not bypass Tailscale's encryption with a side channel.** The daemon speaks HTTPS over the Tailscale overlay. It does not establish a secondary UDP channel, a WebSocket bypass, or any other path that circumvents the encrypted overlay. When daemon and client are on the same machine, it speaks to `127.0.0.1` over HTTP — and Tailscale is not involved. There is no third mode.

**Brúarhönd does not retain commands or screenshots beyond what Annáll explicitly records.** Screenshots are returned to the caller and then released. The daemon does not cache recent screenshots in memory beyond the current request cycle. If the forge side wants screenshot history, it routes through Annáll's session log, not through any Brúarhönd buffer.

**Brúarhönd's translation layer (Loom YAML → automatic VRoid UI navigation) is not part of v0.1.** The higher-level logic that knows "to set hair color to #3a1a0e, click this slider, drag to this value" belongs to v0.2. What v0.1 provides is the primitive surface — click, type, screenshot, hotkey — that makes the translation layer possible. Agents writing v0.1 scripts will issue explicit coordinate-based commands. The smart translation belongs to the follow-on ritual.

**Brúarhönd does not operate arbitrary GUIs.** It ships with high-level VRoid-specific scripts (`vroid_export_vrm`, `vroid_save_project`, `vroid_open_project`) as named primitives — but these are thin coordinate-and-hotkey sequences for VRoid Studio specifically, not a general GUI scripting engine. The scope is the VRoid Studio session, and it remains so.

---

## Resonance with the Existing Forge

Brúarhönd joins the forge's existing domains as a lateral extension rather than a layer in the pipeline. It does not replace the Blender path — it complements it. An agent may use both in a single build:

1. Use the Blender/VRM pipeline (Forge, Oracle Eye, Gate) to produce a compliant `.vrm` from a Loom spec.
2. Use Brúarhönd to then open that `.vrm` in the live VRoid Studio session on the remote host, make fine adjustments only possible through VRoid's native GUI, and export a refined version.

This is the combined forge cycle that v0.2's translation layer will enable fluently. In v0.1, an agent that understands VRoid Studio's UI can already do it manually, primitive by primitive, with vision feedback at every step.

The existing Vows still govern:
- "I will always show you what you have made." — *Yes: Ljósbrú channels remote screenshots through Oracle Eye.*
- "I will speak the same language through every door." — *Yes: Brúarhönd appears as a field in the standard Bridge request, not as a separate protocol.*
- "I will not be broken by a single mistake." — *Yes: Horfunarþjónn fails soft; Hengilherðir surfaces structured errors.*

---

*Vision Scroll written at the lighting of the bridge-fire, 2026-05-06.*
*Sigrún Ljósbrá, Skald — for Volmarr Wyrd.*
