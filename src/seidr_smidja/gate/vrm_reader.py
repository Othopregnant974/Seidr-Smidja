"""seidr_smidja.gate.vrm_reader — Lightweight VRM/glTF header reader.

VRM files are glTF 2.0 binary files with a VRM extension in the JSON chunk.
This module reads the glTF JSON header without parsing the full binary payload,
extracting the fields needed for Gate compliance checking.

This is intentionally minimal and self-contained:
    - No external VRM parsing library required
    - Uses stdlib struct + json only
    - Returns a dict with the fields the Gate rules need
    - Gracefully handles unknown or malformed fields

The Gate does not need to fully parse the VRM — it needs:
    - spec version (vrm.specVersion or extensions.VRM.specVersion)
    - humanoid bone names
    - blendShapeGroups / expression preset names
    - firstPerson config
    - mesh data (polycount is not directly in the header — noted as limitation)
"""
from __future__ import annotations

import json
import logging
import struct
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# glTF 2.0 binary format constants
_GLTF_MAGIC = 0x46546C67   # "glTF" in little-endian
_CHUNK_TYPE_JSON = 0x4E4F534A  # "JSON"
_CHUNK_TYPE_BIN = 0x004E4942   # "BIN\0"


class VRMReadError(RuntimeError):
    """Raised when the VRM file cannot be parsed."""


def read_vrm_header(vrm_path: Path) -> dict[str, Any]:
    """Read the JSON header from a VRM (glTF binary) file.

    Args:
        vrm_path: Path to the .vrm file.

    Returns:
        A dict representing the parsed glTF JSON chunk. Includes:
            - extensions.VRM      (VRM 0.x extension data)
            - extensions.VRMC_vrm (VRM 1.0 extension data)
            - meshes, materials, nodes, accessors (abbreviated — counts only)

    Raises:
        VRMReadError: If the file is not a valid glTF binary or cannot be parsed.
        FileNotFoundError: If the file does not exist.
    """
    if not vrm_path.exists():
        raise FileNotFoundError(f"VRM file not found: {vrm_path}")

    try:
        with vrm_path.open("rb") as fh:
            raw = fh.read()
    except OSError as exc:
        raise VRMReadError(f"Cannot read VRM file {vrm_path}: {exc}") from exc

    return _parse_gltf_binary(raw, vrm_path)


def _parse_gltf_binary(raw: bytes, path: Path) -> dict[str, Any]:
    """Parse a glTF binary buffer and return the JSON chunk as a dict."""
    if len(raw) < 12:
        raise VRMReadError(f"File too small to be a valid glTF binary: {path}")

    magic, version, total_length = struct.unpack_from("<III", raw, 0)

    if magic != _GLTF_MAGIC:
        # Try interpreting as JSON-format glTF (rare but valid)
        try:
            data = json.loads(raw.decode("utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        raise VRMReadError(
            f"Not a valid glTF binary file (wrong magic: 0x{magic:08X}): {path}"
        )

    # Parse chunks
    offset = 12
    json_data: dict[str, Any] | None = None

    while offset < len(raw):
        if offset + 8 > len(raw):
            break
        chunk_length, chunk_type = struct.unpack_from("<II", raw, offset)
        offset += 8
        chunk_data = raw[offset: offset + chunk_length]
        offset += chunk_length

        if chunk_type == _CHUNK_TYPE_JSON:
            try:
                json_data = json.loads(chunk_data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise VRMReadError(
                    f"Failed to parse glTF JSON chunk in {path}: {exc}"
                ) from exc
            break  # JSON chunk is always first; we don't need BIN data

    if json_data is None:
        raise VRMReadError(f"No JSON chunk found in glTF binary: {path}")

    return json_data


def extract_vrm_compliance_data(header: dict[str, Any]) -> dict[str, Any]:
    """Extract compliance-relevant fields from a parsed VRM header.

    Returns a normalized dict with the fields the Gate rules need,
    abstracting over VRM 0.x vs 1.0 differences.

    Fields returned:
        vrm_spec_version:     str — "0.0" or "1.0" (best guess)
        humanoid_bones:       list[str] — list of bone node names
        blendshape_groups:    list[str] — expression/blendshape preset names
        first_person:         dict — firstPerson block (lookat etc.)
        mesh_count:           int — number of mesh entries
        material_count:       int — number of material entries
        node_count:           int — number of node entries
        accessor_count:       int — number of accessor entries
        # Note: actual polygon count is NOT available from the header without
        # parsing the BIN chunk (accessor data). Gate does structural checks only
        # unless a full parsing library is provided.
    """
    result: dict[str, Any] = {
        "vrm_spec_version": "unknown",
        "humanoid_bones": [],
        "blendshape_groups": [],
        "first_person": {},
        "mesh_count": len(header.get("meshes", [])),
        "material_count": len(header.get("materials", [])),
        "node_count": len(header.get("nodes", [])),
        "accessor_count": len(header.get("accessors", [])),
    }

    extensions = header.get("extensions", {})

    # ── VRM 0.x ──────────────────────────────────────────────────────────────
    vrm0 = extensions.get("VRM", {})
    if vrm0:
        result["vrm_spec_version"] = vrm0.get("specVersion", "0.0")

        # Humanoid bones
        humanoid = vrm0.get("humanoid", {})
        human_bones = humanoid.get("humanBones", [])
        result["humanoid_bones"] = [
            b.get("bone", "") for b in human_bones if isinstance(b, dict)
        ]

        # BlendShape groups
        blend_groups = vrm0.get("blendShapeMaster", {}).get("blendShapeGroups", [])
        result["blendshape_groups"] = [
            g.get("presetName", g.get("name", ""))
            for g in blend_groups
            if isinstance(g, dict)
        ]

        # FirstPerson
        result["first_person"] = vrm0.get("firstPerson", {})

    # ── VRM 1.0 ──────────────────────────────────────────────────────────────
    vrmc_vrm = extensions.get("VRMC_vrm", {})
    if vrmc_vrm:
        result["vrm_spec_version"] = vrmc_vrm.get("specVersion", "1.0")

        # Humanoid bones (1.0: humanoid.humanBones is a dict, not a list)
        humanoid = vrmc_vrm.get("humanoid", {})
        human_bones = humanoid.get("humanBones", {})
        if isinstance(human_bones, dict):
            result["humanoid_bones"] = list(human_bones.keys())
        elif isinstance(human_bones, list):
            result["humanoid_bones"] = [b.get("bone", "") for b in human_bones if isinstance(b, dict)]

        # Expressions (1.0: expressions.preset is a dict)
        expressions = vrmc_vrm.get("expressions", {})
        preset = expressions.get("preset", {})
        if isinstance(preset, dict):
            result["blendshape_groups"] = list(preset.keys())

        # FirstPerson
        result["first_person"] = vrmc_vrm.get("firstPerson", {})

    return result
