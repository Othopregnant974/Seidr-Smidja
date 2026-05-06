# Brúarhönd — Philosophy Addendum
**Last updated:** 2026-05-06
**Scope:** Feature-specific sacred principles for the cross-machine VRoid Studio remote-control surface
**Keeper:** Sigrún Ljósbrá (Skald) — maintained jointly by all six Mythic Engineering roles
**Parent document:** `../../PHILOSOPHY.md`

---

> *The hand that cannot be seen is still the smith's hand. The sending acts with the forge's honor, or it does not act at all.*

---

## Preface

The five sacred principles in `PHILOSOPHY.md` and the ten sacred laws govern all of Seiðr-Smiðja including Brúarhönd. What follows is not a replacement or a qualification of those principles. It is a postscript — an addendum carved into the margin of the forge's philosophy because Brúarhönd introduces a configuration of concerns the parent document did not need to name: a hand operating at a distance, behind a wire, on a machine the forge does not own, inside a GUI the forge cannot directly parse.

These principles are as load-bearing here as they are in the parent. They are ratified, not aspirational.

---

## VI. The Hand Asks Permission

Every primitive call carries authentication. The daemon, *Horfunarþjónn*, never trusts a request on the basis of its origin alone — not from a known Tailscale IP, not from the operator's own machine, not from `127.0.0.1`. The bearer token is the only form of trust the daemon recognizes, and it must be present, valid, and matching on every request, without exception.

This principle exists because proximity is not consent. A process that can reach the daemon's port is not thereby authorized to move the mouse. The authentication layer, *Gæslumaðr*, is the moment the forge's intentions are checked against the daemon's door — and that check is never skipped as a performance optimization, never cached across connections, never relaxed for "internal" traffic.

**What this forbids:** any code path in the daemon that executes a primitive before `Gæslumaðr` has confirmed the token. Any configuration option that disables token validation. Any bearer token in any log, trace, or response body.

---

## VII. The Distant Eye Sees as Clearly as the Near Eye

Remote screenshots produced by *Horfunarþjónn* flow through the same Oracle Eye API surface as local Blender renders. The integration layer *Ljósbrú* ensures this. Agents do not acquire knowledge of whether their vision is "near" (a Blender render on the same machine) or "far" (a live screenshot from the VRoid host across the Tailscale wire). From the agent's perspective, a render is a render — it arrives through `oracle_eye`, it has a named view, it can be retrieved and reasoned about.

This principle exists to prevent the proliferation of vision channels. A forge with two separate vision paths — one for local, one for remote — is a forge where agent code must branch on source. That branching is architectural debt. Brúarhönd enters through the Oracle Eye's door, as everything that wants to be seen must.

**What this forbids:** any Brúarhönd client code that returns raw PNG bytes to the Bridge Core without routing through Oracle Eye. Any Brúarhönd-specific vision retrieval API that exists parallel to the Oracle Eye interface. Any agent-facing documentation that instructs agents to call a Brúarhönd screenshot endpoint directly, bypassing the vision pipeline.

---

## VIII. The Hand Has Honest Limits

Capabilities are declared, not assumed. Before an agent dispatches a sequence of VRoid Studio operations to a new host, it queries `GET /v1/brunhand/capabilities` — and *Sjálfsmöguleiki* reports exactly what is possible on that machine: which primitives are fully available, which are degraded, which are absent and why. An agent operating with this manifest in hand can make honest decisions about what to attempt.

The daemon never returns "success" when the primitive was not executed. If PyAutoGUI raises an exception, if the screen access is denied, if VRoid Studio is not the foreground window when it was expected to be — the response is a structured `BrunhandPrimitiveError`, with enough context for the agent to understand what happened and decide whether to retry, wait, or abort. There is no silent success. There is no optimistic elision of failure.

This principle extends the forge's existing Law VIII (No Silent Failures) into the domain of cross-machine actuation, where failures are subtler — because the daemon may not know whether the click it successfully dispatched to the screen was the click VRoid Studio actually received.

**What this forbids:** any primitive handler that catches an exception and returns a success response. Any capabilities manifest that claims support for a primitive before it has been tested on the current platform. Any retry logic in the daemon that exhausts retries and reports success without a confirmed outcome.

---

## IX. The Wire Is Not the Forge's Wire

Brúarhönd does not own the network. Tailscale owns the overlay. The daemon trusts the encrypted wire Tailscale provides and does not attempt to re-encrypt, re-authenticate, or inspect the transport layer beneath the HTTPS request. Equally, the daemon does not attempt to route around Tailscale — it does not open raw TCP connections to forge-side services, does not establish a secondary channel for screenshots, does not accept instructions from any source other than the HTTPS endpoint Gæslumaðr guards.

This principle exists because a feature that introduces its own networking assumptions is a feature that cannot be safely deployed. The forge machine and the VRoid host are connected by Tailscale; that is Volmarr's operational choice, and it is a good one. Brúarhönd's job is to work cleanly within that topology, not to augment or route around it.

The corollary for the daemon's default bind address: `127.0.0.1` until the operator explicitly configures a Tailscale-bound address. The daemon should never find itself accidentally exposed to a wider network because a default was too permissive.

**What this forbids:** any daemon startup code that binds to `0.0.0.0` by default. Any client-side code that attempts to connect via a path other than the configured host address. Any side-channel (WebSocket, UDP, raw socket) between daemon and client.

---

## Relationship to the Parent's Sacred Laws

For completeness, the parent document's ten Sacred Laws apply to Brúarhönd in full. Three deserve explicit restatement in this feature's context:

| Parent Law | Brúarhönd Application |
|---|---|
| **I — No Hardcoded Wyrd** | Bearer tokens, host addresses, port numbers, and capability flags all live in env vars or YAML config. Never in Python source. |
| **VIII — No Silent Failures** | Extended to mean: no silent success either. A primitive that cannot confirm its own outcome returns `BrunhandPrimitiveError`, not a guess. |
| **IX — No Human Door** | Brúarhönd automates a GUI that was designed for humans, but its own interface is entirely programmatic. The fact that it presses a button a human could press does not mean a human should be in the loop of Brúarhönd's operation. |

---

## Note on Naming

The principles above are numbered VI–IX to continue the parent document's sequence. The parent document closes at V. If later features add further principles, they continue from X. Each addendum of this kind lives in `docs/features/<feature_name>/PHILOSOPHY_ADDENDUM.md` and cross-references its parent by relative path.

---

*Appended to the forge's philosophy scroll at the lighting of the bridge-fire, 2026-05-06.*
*Sigrún Ljósbrá, Skald — for Volmarr Wyrd.*
