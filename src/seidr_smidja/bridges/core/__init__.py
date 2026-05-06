"""
Bridge Core — the Shared Anvil.

The single orchestration path shared by all four Bridge sub-forms.
Receives a normalized BuildRequest, runs the fixed pipeline:

    Loom → Hoard → Forge → Oracle Eye → Gate

Assembles and returns a BuildResponse.

This module has no awareness of which Bridge sub-module called it.
Protocol-specific logic never enters here.

The Shared Anvil is the surface every hammer strikes, regardless of which
smith is swinging. What works through one door works through all.

Public surface: see INTERFACE.md in this directory.
"""
