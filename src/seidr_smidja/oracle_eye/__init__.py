"""Oracle Eye — Óðins-Auga.

The render and vision feedback layer. After the Forge completes, the Oracle Eye
orchestrates Blender (or a compatible headless renderer) to produce standard
preview PNGs: front, three-quarter, side, face close-up, T-pose, and signature
expressions. These images are returned to the calling agent.

The eye that sees is the eye that refines.

The Oracle Eye is never disabled in a compliant build that produces a .vrm.
This is Sacred Principle 2 — the Oracle Eye Is Never Closed.

Public surface: see INTERFACE.md in this directory.
"""

from seidr_smidja.oracle_eye.eye import (
    RenderError,
    RenderResult,
    RenderView,
    list_standard_views,
    render,
)

__all__ = [
    "render",
    "list_standard_views",
    "RenderView",
    "RenderResult",
    "RenderError",
]
