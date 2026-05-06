"""
Skills — Skaldic Skill Bridges.

Thin YAML manifests and Python adapters for agent skill invocation:
    - Hermes skill manifest
    - OpenClaw skill manifest
    - Claude Code skill manifest (MCP-based)

Each adapter translates the skill invocation format into a BuildRequest and
calls bridges.core.dispatch(). Manifests live as YAML files alongside this
package.

No forge logic lives here. Skills are doors, not the forge.
"""
