"""
Forge — the Smiðja.

The headless Blender execution layer. The Forge receives a validated Loom spec
and a resolved base asset path, opens Blender in background mode, applies all
parametric transformations through the VRM Add-on for Blender, and exports a
.vrm output file.

This is where specification becomes mesh, weight, bone, and material.
Intention made solid.

Blender is always a subprocess — never in-process. Isolation is non-negotiable.

Public surface: see INTERFACE.md in this directory.
"""
