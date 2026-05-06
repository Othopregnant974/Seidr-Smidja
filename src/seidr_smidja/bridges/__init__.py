"""
Bridges — the Bifröst Bridges.

The agent-facing interface layer. Four bridges allow any agent to enter the
forge through its preferred door:

    core/       — Shared Anvil: the single canonical orchestration path
    mjoll/      — Mjöll: MCP (Model Context Protocol) bridge
    runstafr/   — Rúnstafr: CLI bridge (the `seidr` command)
    straumur/   — Straumur: REST/HTTP bridge
    skills/     — Skill Bridges: Hermes, OpenClaw, Claude Code manifests

All sub-modules call only through bridges.core.dispatch().
None contain forge logic. Many doors, one forge.

Public surface: see INTERFACE.md in this directory.
"""
