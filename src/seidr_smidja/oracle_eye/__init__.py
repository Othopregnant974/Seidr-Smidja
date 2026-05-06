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
    ExternalRenderMetadata,
    ExternalRenderResult,
    RenderError,
    RenderResult,
    RenderView,
    list_standard_views,
    register_external_render,
    render,
)

__all__ = [
    "render",
    "list_standard_views",
    "RenderView",
    "RenderResult",
    "RenderError",
    # Brúarhönd external render integration (additive — D-010)
    "register_external_render",
    "ExternalRenderMetadata",
    "ExternalRenderResult",
]
