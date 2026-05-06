"""
Seiðr-Smiðja — the Seething-Forge.

An agent-only VRM avatar smithy. AI agents design, build, render, critique,
and export VRChat-ready and VTube-Studio-ready VRM avatars through any Bridge
(MCP, CLI, REST, skill manifests) with a built-in vision feedback loop.

Domain structure:
    loom/       — Norn-Loom: parametric avatar specification
    hoard/      — Asset Hoard: base mesh and asset library
    forge/      — Smiðja: headless Blender execution
    oracle_eye/ — Óðins-Auga: render and vision feedback
    gate/       — Compliance Gate: VRChat and VTube Studio validation
    annall/     — The Record: logging and session memory
    bridges/    — Bifröst Bridges: agent-facing interface layer
"""
