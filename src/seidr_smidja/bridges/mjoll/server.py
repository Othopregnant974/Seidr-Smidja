"""seidr_smidja.bridges.mjoll.server — Mjöll MCP Bridge.

A minimal MCP server exposing two tools:
    seidr.build_avatar  — runs the full forge pipeline
    seidr.inspect_vrm   — runs the Gate check standalone

The MCP SDK (mcp package) is an optional dependency. If importing fails,
the server emits a clear error when invoked rather than crashing at import time.
The rest of the package installs and works without mcp.

Usage:
    python -m seidr_smidja.bridges.mjoll
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Attempt to import MCP SDK — gracefully degrade if unavailable
_MCP_AVAILABLE = False
try:
    from mcp import types as mcp_types  # type: ignore[import]
    from mcp.server import Server  # type: ignore[import]
    from mcp.server.stdio import stdio_server  # type: ignore[import]

    _MCP_AVAILABLE = True
except ImportError:
    Server = None  # type: ignore[assignment,misc]
    stdio_server = None  # type: ignore[assignment]
    mcp_types = None  # type: ignore[assignment]


def _require_mcp() -> None:
    if not _MCP_AVAILABLE:
        raise ImportError(
            "The 'mcp' package is required to run the Mjöll MCP bridge. "
            "Install it with: pip install 'seidr-smidja[mcp]' or pip install mcp"
        )


def build_mcp_server(config: dict[str, Any] | None = None) -> Any:
    """Construct and return a configured MCP Server instance.

    Args:
        config: Optional config dict from load_config().

    Returns:
        An mcp.server.Server instance with tools registered.

    Raises:
        ImportError: If the mcp package is not installed.
    """
    _require_mcp()

    server = Server("seidr-smidja")  # type: ignore[call-arg]

    @server.list_tools()  # type: ignore[misc]
    async def list_tools() -> list[Any]:
        return [
            mcp_types.Tool(  # type: ignore[misc]
                name="seidr.build_avatar",
                description=(
                    "Build a VRM avatar from a parametric Loom spec. "
                    "Runs the full forge pipeline: validate → resolve base → "
                    "Blender build → render previews → compliance check. "
                    "Returns the .vrm path, render PNG paths, and compliance report."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spec": {
                            "oneOf": [
                                {"type": "object", "description": "Inline spec dict"},
                                {"type": "string", "description": "Path to a spec YAML/JSON file"},
                            ],
                            "description": "Avatar spec — inline dict or file path",
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Output directory path for .vrm and renders",
                        },
                        "render_views": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Render views to request. Omit for full standard set.",
                        },
                        "compliance_targets": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["VRCHAT", "VTUBE_STUDIO"]},
                            "description": "Compliance targets. Omit for all.",
                        },
                    },
                    "required": ["spec"],
                },
            ),
            mcp_types.Tool(  # type: ignore[misc]
                name="seidr.inspect_vrm",
                description=(
                    "Run Gate compliance check on an existing .vrm file. "
                    "Returns a full compliance report with pass/fail and violation details."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "vrm_path": {"type": "string", "description": "Path to the .vrm file"},
                        "targets": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["VRCHAT", "VTUBE_STUDIO"]},
                            "description": "Compliance targets. Omit for all.",
                        },
                    },
                    "required": ["vrm_path"],
                },
            ),
            # ── Brúarhönd tools ───────────────────────────────────────────────
            mcp_types.Tool(  # type: ignore[misc]
                name="seidr.brunhand_screenshot",
                description=(
                    "Capture a screenshot from a remote VRoid Studio host via Brúarhönd. "
                    "Returns base64-encoded PNG bytes, width, height, and capture timestamp. "
                    "Requires a configured brunhand.hosts entry and BRUNHAND_TOKEN."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "host_name": {
                            "type": "string",
                            "description": "Named host entry from brunhand.hosts config",
                        },
                        "agent_id": {
                            "type": "string",
                            "description": "Agent identifier for telemetry (optional)",
                        },
                    },
                    "required": ["host_name"],
                },
            ),
            mcp_types.Tool(  # type: ignore[misc]
                name="seidr.brunhand_click",
                description=(
                    "Send a mouse click to a remote VRoid Studio host via Brúarhönd. "
                    "Coordinates are in screen pixels on the daemon's display. "
                    "Requires a configured brunhand.hosts entry and BRUNHAND_TOKEN."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "host_name": {"type": "string", "description": "Named host from config"},
                        "x": {"type": "integer", "description": "Screen X coordinate"},
                        "y": {"type": "integer", "description": "Screen Y coordinate"},
                        "button": {
                            "type": "string",
                            "enum": ["left", "right", "middle"],
                            "description": "Mouse button (default: left)",
                        },
                        "clicks": {
                            "type": "integer",
                            "description": "Number of clicks (default: 1)",
                        },
                        "agent_id": {"type": "string"},
                    },
                    "required": ["host_name", "x", "y"],
                },
            ),
            mcp_types.Tool(  # type: ignore[misc]
                name="seidr.brunhand_vroid_export",
                description=(
                    "Export a VRM file from VRoid Studio on a remote host via Brúarhönd. "
                    "Triggers the VRoid Studio export dialog, waits for completion, "
                    "and returns the exported file path. "
                    "VRoid Studio must be running and have a project open. "
                    "Requires a configured brunhand.hosts entry and BRUNHAND_TOKEN."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "host_name": {"type": "string", "description": "Named host from config"},
                        "output_path": {
                            "type": "string",
                            "description": "VRM output path on the daemon's filesystem",
                        },
                        "overwrite": {
                            "type": "boolean",
                            "description": "Overwrite if file exists (default: true)",
                        },
                        "wait_timeout_seconds": {
                            "type": "number",
                            "description": "Max seconds to wait for export dialog (default: 120)",
                        },
                        "agent_id": {"type": "string"},
                    },
                    "required": ["host_name", "output_path"],
                },
            ),
        ]

    @server.call_tool()  # type: ignore[misc]
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[Any]:
        if name == "seidr.build_avatar":
            return await _handle_build_avatar(arguments, config)
        elif name == "seidr.inspect_vrm":
            return await _handle_inspect_vrm(arguments, config)
        elif name == "seidr.brunhand_screenshot":
            return await _handle_brunhand_screenshot(arguments, config)
        elif name == "seidr.brunhand_click":
            return await _handle_brunhand_click(arguments, config)
        elif name == "seidr.brunhand_vroid_export":
            return await _handle_brunhand_vroid_export(arguments, config)
        else:
            return [
                mcp_types.TextContent(  # type: ignore[misc]
                    type="text", text=json.dumps({"error": f"Unknown tool: {name}"})
                )
            ]

    return server


async def _handle_build_avatar(arguments: dict[str, Any], config: dict[str, Any] | None) -> list[Any]:
    """Handle seidr.build_avatar tool call."""
    from seidr_smidja.annall.factory import make_annall
    from seidr_smidja.bridges.core.dispatch import BuildRequest, dispatch
    from seidr_smidja.config import _find_config_root

    project_root = _find_config_root()
    cfg = config or {}

    # Determine output_dir
    output_dir_str = arguments.get("output_dir")
    if output_dir_str:
        output_dir = Path(output_dir_str).resolve()
    else:
        output_root = cfg.get("output", {}).get("root", "output")
        output_dir = (project_root / output_root).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine spec source
    spec_input = arguments.get("spec")
    if isinstance(spec_input, str):
        spec_source: Path | dict[str, Any] = Path(spec_input)
    else:
        spec_source = spec_input or {}

    # Get base_asset_id from spec
    base_asset_id = ""
    if isinstance(spec_source, dict):
        base_asset_id = spec_source.get("base_asset_id", "")
    else:
        try:
            from seidr_smidja.loom.loader import load_spec

            spec_obj = load_spec(spec_source)
            base_asset_id = spec_obj.base_asset_id
        except Exception:
            pass

    annall = make_annall(cfg, project_root)
    request = BuildRequest(
        spec_source=spec_source,
        base_asset_id=base_asset_id,
        output_dir=output_dir,
        render_views=arguments.get("render_views"),
        compliance_targets=arguments.get("compliance_targets"),
        session_metadata={
            "agent_id": "mcp_client",
            "bridge_type": "mjoll",
        },
        request_id=str(uuid.uuid4()),
    )

    response = dispatch(request, annall, config=cfg)

    result = {
        "success": response.success,
        "request_id": response.request_id,
        "vrm_path": str(response.vrm_path) if response.vrm_path else None,
        "render_paths": {k: str(v) for k, v in response.render_paths.items()},
        "compliance_passed": (
            response.compliance_report.passed if response.compliance_report else None
        ),
        "session_id": response.annall_session_id,
        "elapsed_seconds": response.elapsed_seconds,
        "errors": [
            {"stage": e.stage, "message": e.message}
            for e in response.errors
        ],
    }

    return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]  # type: ignore[misc]


async def _handle_inspect_vrm(arguments: dict[str, Any], config: dict[str, Any] | None) -> list[Any]:
    """Handle seidr.inspect_vrm tool call."""
    from seidr_smidja.config import _find_config_root
    from seidr_smidja.gate.gate import check as gate_check

    project_root = _find_config_root()
    cfg = config or {}

    vrm_path = Path(arguments["vrm_path"])
    targets = arguments.get("targets")

    gate_cfg = cfg.get("gate", {})
    rules_dir_str = gate_cfg.get("rules_dir")
    rules_dir = (project_root / rules_dir_str).resolve() if rules_dir_str else None
    vrchat_tier = gate_cfg.get("vrchat_tier_target", "Good")

    try:
        report = gate_check(
            vrm_path=vrm_path,
            targets=targets,
            rules_dir=rules_dir,
            vrchat_tier=vrchat_tier,
        )
        result = {
            "passed": report.passed,
            "vrm_path": str(report.vrm_path),
            "targets_checked": [t.value for t in report.targets_checked],
            "elapsed_seconds": report.elapsed_seconds,
            "results": {
                key: {
                    "passed": tr.passed,
                    "violations": [
                        {
                            "rule_id": v.rule_id,
                            "severity": v.severity.value,
                            "description": v.description,
                        }
                        for v in tr.violations
                    ],
                }
                for key, tr in report.results.items()
            },
        }
    except Exception as exc:
        result = {"error": str(exc), "passed": False}

    return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]  # type: ignore[misc]


async def _handle_brunhand_screenshot(
    arguments: dict[str, Any], config: dict[str, Any] | None,
) -> list[Any]:
    """Handle seidr.brunhand_screenshot MCP tool call."""
    import base64

    from seidr_smidja.annall.adapters.null import NullAnnallAdapter
    from seidr_smidja.bridges.core.dispatch import BrunhandDispatchRequest, brunhand_dispatch

    cfg = config or {}
    annall = NullAnnallAdapter()

    request = BrunhandDispatchRequest(
        host_name=arguments["host_name"],
        primitive="screenshot",
        primitive_args={},
        agent_id=arguments.get("agent_id", "mcp_client"),
        config=cfg,
    )
    response = brunhand_dispatch(request, annall)

    result: dict[str, Any] = {
        "success": response.success,
        "primitive": "screenshot",
        "host": response.host,
        "elapsed_seconds": response.elapsed_seconds,
    }
    if response.success and response.result is not None:
        r = response.result
        png_bytes = getattr(r, "png_bytes", b"")
        result["width"] = getattr(r, "width", 0)
        result["height"] = getattr(r, "height", 0)
        result["captured_at"] = getattr(r, "captured_at", "")
        result["byte_count"] = len(png_bytes)
        result["png_b64"] = base64.b64encode(png_bytes).decode("ascii") if png_bytes else ""
    else:
        result["error_type"] = response.error_type
        result["error_message"] = response.error_message

    return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]  # type: ignore[misc]


async def _handle_brunhand_click(
    arguments: dict[str, Any], config: dict[str, Any] | None,
) -> list[Any]:
    """Handle seidr.brunhand_click MCP tool call."""
    from seidr_smidja.annall.adapters.null import NullAnnallAdapter
    from seidr_smidja.bridges.core.dispatch import BrunhandDispatchRequest, brunhand_dispatch

    cfg = config or {}
    annall = NullAnnallAdapter()

    primitive_args = {
        "x": arguments["x"],
        "y": arguments["y"],
        "button": arguments.get("button", "left"),
        "clicks": arguments.get("clicks", 1),
    }

    request = BrunhandDispatchRequest(
        host_name=arguments["host_name"],
        primitive="click",
        primitive_args=primitive_args,
        agent_id=arguments.get("agent_id", "mcp_client"),
        config=cfg,
    )
    response = brunhand_dispatch(request, annall)

    result: dict[str, Any] = {
        "success": response.success,
        "primitive": "click",
        "host": response.host,
        "elapsed_seconds": response.elapsed_seconds,
    }
    if response.success and response.result is not None:
        r = response.result
        result["x"] = getattr(r, "x", arguments["x"])
        result["y"] = getattr(r, "y", arguments["y"])
        result["clicks_delivered"] = getattr(r, "clicks_delivered", 1)
    else:
        result["error_type"] = response.error_type
        result["error_message"] = response.error_message

    return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]  # type: ignore[misc]


async def _handle_brunhand_vroid_export(
    arguments: dict[str, Any], config: dict[str, Any] | None,
) -> list[Any]:
    """Handle seidr.brunhand_vroid_export MCP tool call."""
    from seidr_smidja.annall.adapters.null import NullAnnallAdapter
    from seidr_smidja.bridges.core.dispatch import BrunhandDispatchRequest, brunhand_dispatch

    cfg = config or {}
    annall = NullAnnallAdapter()

    primitive_args = {
        "output_path": arguments["output_path"],
        "overwrite": arguments.get("overwrite", True),
        "wait_timeout_seconds": float(arguments.get("wait_timeout_seconds", 120.0)),
    }

    request = BrunhandDispatchRequest(
        host_name=arguments["host_name"],
        primitive="vroid_export_vrm",
        primitive_args=primitive_args,
        agent_id=arguments.get("agent_id", "mcp_client"),
        config=cfg,
    )
    response = brunhand_dispatch(request, annall)

    result: dict[str, Any] = {
        "success": response.success,
        "primitive": "vroid_export_vrm",
        "host": response.host,
        "elapsed_seconds": response.elapsed_seconds,
    }
    if response.success and response.result is not None:
        r = response.result
        result["exported_path"] = getattr(r, "exported_path", arguments["output_path"])
        result["steps_executed"] = getattr(r, "steps_executed", [])
    else:
        result["error_type"] = response.error_type
        result["error_message"] = response.error_message

    return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]  # type: ignore[misc]


async def _run_server(config: dict[str, Any] | None = None) -> None:
    """Async entry point for running the MCP server."""
    _require_mcp()
    server = build_mcp_server(config)
    async with stdio_server() as (read_stream, write_stream):  # type: ignore[misc]
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    from seidr_smidja.config import load_config

    cfg = load_config()
    asyncio.run(_run_server(cfg))
