"""
Mjöll — the MCP Bridge.

Receives build requests via the Model Context Protocol. Translates MCP tool
invocations into BuildRequest objects, calls bridges.core.dispatch(), and
translates the BuildResponse back into MCP-native tool results.

No forge logic lives here. Mjöll is a door, not the forge.
"""
