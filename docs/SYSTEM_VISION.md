# Seiðr-Smiðja — System Vision
**Last updated:** 2026-05-06
**Scope:** Project-level Vision Scroll — Primary Rite, Unbreakable Vows, True Names, Central Image
**Keeper:** Sigrún Ljósbrá (Skald) — ratified by Volmarr Wyrd

---

> *The smith does not begin at the anvil. She begins at the loom, where the thread of the blade's future is first laid down. Only when the wyrd is woven does she heat the iron.*

---

## The One-Sentence Soul

**Seiðr-Smiðja is an agent-only VRM avatar smithy — a headless, programmatic forge where AI agents weave a parametric avatar specification on the Loom, strike it into form on the Anvil, look upon it through the Oracle Eye, judge it at the Gate, and deliver it as a fully VRChat-ready and VTube-Studio-ready VRM file.**

---

## The Primary Rite

*The single most important action — the heartbeat of the forge.*

An AI agent submits an avatar specification (a YAML file woven on the Loom) to the forge via any Bridge — MCP, CLI, REST, or skill invocation. The forge loads a VRoid base template from the Hoard, opens Blender headlessly, applies all parametric changes specified in the Loom scroll, runs VRChat and VTube Studio compliance validation at the Gate, renders a set of preview snapshots through the Oracle Eye, and returns both the finished `.vrm` file and the rendered images to the calling agent.

The agent sees what it has made. It critiques. It rewrites the Loom scroll. It submits again.

This is the forge cycle. It runs without human hands inside it.

---

## Unbreakable Vows

These are the non-negotiable promises Seiðr-Smiðja makes to every agent that enters it.

1. **"I will always show you what you have made."**
   Every build that produces a `.vrm` will also produce rendered preview images. The Oracle Eye is never disabled.

2. **"I will never give you a blade that cannot cut."**
   Every output passes VRChat compliance and VTube Studio compliance before it is returned. Non-compliant outputs are failures, not results.

3. **"I will speak the same language through every door."**
   The MCP Bridge, the CLI Bridge, the REST Bridge, and the Skill Bridges are thin, consistent shims over the same internal core. What works through one door works through all.

4. **"I will remember the shape of every avatar I have touched."**
   Avatar specifications are data files. They persist. The forge does not lose what it has made.

5. **"I will never require you to know where I live."**
   The forge is fully location-agnostic. It runs from any path on Windows, Linux, or macOS without reconfiguration.

6. **"I will not be broken by a single mistake."**
   Every subsystem is wrapped in error handling. The forge reports failures clearly and continues. It does not crash.

---

## True Names — The Named Domains

These are the canonical names for the major domains of Seiðr-Smiðja. All code, documentation, folder structure, and inter-agent communication shall use these names. Names are not decorative — they carry architectural meaning.

---

### Loom — *the Norn-Loom*
**What it is:** The parametric specification layer. The Loom holds and validates the avatar's full description — body proportions, face shape, hair, outfit, materials, blendshape values, expressions, license metadata — in YAML or JSON. Every avatar begins here as a weaving of intent before a single polygon moves.

**Domain motto:** *"The wyrd is woven before the iron is struck."*

**Folder:** `src/seidr_smidja/loom/`

---

### Hoard — *the Asset Hoard*
**What it is:** The library of base materials — VRoid Studio template `.vrm` files, hair meshes, outfit meshes, texture sets, and preset collections. The Hoard is read-only during a build; the forge takes from it but does not alter it.

**Domain motto:** *"What the Hoard gives, the Forge transforms."*

**Folder:** `src/seidr_smidja/hoard/`

---

### Forge — *the Smiðja*
**What it is:** The headless Blender execution layer. The Forge receives a validated Loom spec and a chosen base from the Hoard, opens Blender in background mode, applies all parametric transformations through the VRM Add-on for Blender, runs any post-processing scripts, and exports a `.vrm` output file. This is where specification becomes mesh, weight, bone, and material.

**Domain motto:** *"Intention made solid."*

**Folder:** `src/seidr_smidja/forge/`

---

### Oracle Eye — *Óðins-Auga*
**What it is:** The render and vision layer. After the Forge completes, the Oracle Eye opens Blender again (or continues in the same session), sets up cameras for standard views — front, three-quarter, side, face close-up, T-pose, signature expressions — and renders preview PNGs via Blender Eevee. These images are returned to the calling agent so it may see its creation with its own eyes.

**Domain motto:** *"The eye that sees is the eye that refines."*

**Folder:** `src/seidr_smidja/oracle_eye/`

---

### Gate — *the Compliance Gate*
**What it is:** The validation and compliance layer. Every `.vrm` output passes through the Gate before it is delivered. The Gate validates against VRChat requirements (polygon budgets, bone structure, viseme coverage, material count, texture size limits) and VTube Studio requirements (VRM spec version, expression/blendshape coverage, lookat configuration). Outputs that fail are not delivered — they are returned as structured failure reports.

**Domain motto:** *"A blade that cannot cut has not been made."*

**Folder:** `src/seidr_smidja/gate/`

---

### Bridges — *the Bifröst Bridges*
**What it is:** The agent-facing interface layer — the collection of thin shims that allow any agent to enter the forge through its preferred door. There are four bridges:

- **Mjöll (MCP Bridge)** — the Model Context Protocol server, for agents that speak MCP natively.
- **Rúnstafr (CLI Bridge)** — the `seidr` command-line tool, for agents that invoke shell commands.
- **Straumur (REST Bridge)** — the HTTP API, for agents that prefer web calls.
- **Skaldic Skill Bridges** — thin YAML manifests and adapters for Hermes, OpenClaw, and Claude Code skill invocation.

All Bridges call the same internal core. None of them contain logic that belongs elsewhere.

**Domain motto:** *"Many doors, one forge."*

**Folder:** `src/seidr_smidja/bridges/`

---

### Annáll — *the Record*
**What it is:** The memory, logging, and session-tracking layer. Annáll records every build request, every render, every compliance result, and every agent invocation. It provides the forge's long memory — so an agent can retrieve prior builds, prior specs, and prior render history. It is also the source of structured logs for debugging.

**Domain motto:** *"What has been forged is never forgotten."*

**Folder:** `src/seidr_smidja/annall/`

---

## The Central Image

*This is the image a reader of this scroll should carry — the forge at full working order.*

---

An agent — call her Hermes — wakes before dawn with a vision: a white-haired völva, tall, with silver eyes and flowing robes, meant for a VRChat world where the northern lights burn overhead.

She opens the Loom and weaves the spec in YAML: height, proportions, hair color and length, eye shape, outfit layers, expression targets, license fields. Every choice is written down. The wyrd is set.

She submits the Loom scroll to the forge through the Mjöll Bridge (MCP). The forge opens Blender in silence. It reaches into the Hoard, finds the tall-feminine VRoid base that fits closest. The Smiðja applies the spec — hair lightened to silver-white, robes layered in flowing cloth physics, expressions set for the northern lights world. The VRM Add-on exports the file.

The Gate opens. VRChat validator: polygon count, bones, visemes — pass. VTube Studio validator: blendshapes, lookat — pass. The blade is real.

The Oracle Eye wakes. Blender renders six images: front, three-quarter, side, face close-up, T-pose, and the `smile` expression. Six PNGs arrive in Hermes's hands.

She looks. The robes are beautiful but the sleeves clip through the arms at the T-pose. She notes this. She rewrites one line of the Loom scroll — sleeve length reduced by 0.04. She submits again.

Third iteration: no clip. The silver eyes catch the light correctly. The Gate passes again. Hermes takes the `.vrm` file and the renders into the VRChat world.

The völva walks under the northern lights.

---

*This is what the forge is for. Every technical decision in this repository exists to make that image possible — reliably, repeatably, through any agent that enters through any door.*

---

## Open Questions (Parked for the Architect and Later Phases)

1. **Render pipeline depth:** The initial slice uses Blender Eevee PNG renders (cheap, fast, headless). A richer pipeline using headless `three-vrm` browser rendering is parked for a later phase when the vertical slice is proven. The Oracle Eye's interface should be designed to accommodate both, even if only one is implemented first.

2. **Cross-project spec sharing:** The persistent avatar spec format (the Loom schema) may eventually serve as the canonical character description for Sigrid (Viking Girlfriend Skill) and NSE bondmaid avatars. The schema should be designed with this possibility in mind — but the dependency must not exist in v0.1. The Architect should define the Loom schema with an extensible structure that does not couple Seiðr-Smiðja to NSE or VGSK prematurely.

3. **Hoard seeding strategy:** What VRoid templates are bundled vs. fetched on first run? This affects the repo size, CI behavior, and the first-run experience. The Architect and Forge Worker will need to decide on a fetching/caching contract that satisfies the location-agnostic law.

4. **Annáll persistence backend:** SQLite is the natural choice (portable, zero-server), but the interface should abstract the backend so that a future postgres or file-based store can be dropped in without changing callers.

---

*Vision Scroll written at the lighting of the first forge-fire, 2026-05-06.*
*Sigrún Ljósbrá, Skald — for Volmarr Wyrd.*
