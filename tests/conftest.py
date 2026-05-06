"""Shared test fixtures and configuration for the Seiðr-Smiðja test suite."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

# ─── Pytest marker registration ──────────────────────────────────────────────
# The requires_blender marker is registered in pyproject.toml.
# This conftest provides fixtures — registration is in pyproject.toml.


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def null_annall():
    """A NullAnnallAdapter for tests that don't need telemetry."""
    from seidr_smidja.annall.adapters.null import NullAnnallAdapter

    return NullAnnallAdapter()


@pytest.fixture
def sqlite_annall(tmp_path: Path):
    """A SQLiteAnnallAdapter backed by a temp database."""
    from seidr_smidja.annall.adapters.sqlite import SQLiteAnnallAdapter

    db_path = tmp_path / "test_annall.sqlite"
    return SQLiteAnnallAdapter(db_path=db_path)


@pytest.fixture
def minimal_spec_dict() -> dict[str, Any]:
    """A minimal valid AvatarSpec dict."""
    return {
        "spec_version": "1.0",
        "avatar_id": "test_avatar_v1",
        "display_name": "Test Avatar",
        "base_asset_id": "vroid/sample_a",
        "body": {
            "height_scale": 1.0,
        },
        "hair": {
            "color": {"r": 0.8, "g": 0.6, "b": 0.2},
        },
        "face": {
            "eye_color": {"r": 0.2, "g": 0.4, "b": 0.9},
        },
        "metadata": {
            "author": "Test Agent",
            "license": "CC0-1.0",
        },
    }


@pytest.fixture
def full_spec_dict() -> dict[str, Any]:
    """A fully-populated AvatarSpec dict covering all v0.1 fields."""
    return {
        "spec_version": "1.0",
        "avatar_id": "full_test_avatar",
        "display_name": "Full Test Avatar",
        "base_asset_id": "vroid/sample_a",
        "body": {
            "height_scale": 1.05,
            "head_scale": 1.0,
            "upper_body_scale": 1.0,
            "lower_body_scale": 0.98,
            "arm_length_scale": 1.02,
            "leg_length_scale": 1.05,
        },
        "face": {
            "eye_color": {"r": 0.1, "g": 0.7, "b": 0.9},
            "eye_scale": 1.1,
            "nose_scale": 0.9,
            "mouth_width_scale": 1.0,
            "skin_color": {"r": 1.0, "g": 0.88, "b": 0.79},
        },
        "hair": {
            "color": {"r": 0.95, "g": 0.95, "b": 1.0},
            "style_id": None,
            "length_scale": 1.5,
            "physics_enabled": True,
        },
        "outfit": {
            "layers": [
                {
                    "layer_id": "top",
                    "mesh_id": None,
                    "primary_color": {"r": 0.2, "g": 0.2, "b": 0.4},
                    "secondary_color": None,
                    "visible": True,
                }
            ]
        },
        "expressions": {
            "targets": [
                {"name": "joy", "weight": 0.0},
                {"name": "blink", "weight": 0.0},
            ]
        },
        "metadata": {
            "author": "Full Test Agent",
            "license": "CC-BY-4.0",
            "contact_url": "https://example.com",
            "commercial_use": False,
            "redistribution": True,
            "platform_tags": ["vrchat", "vtube_studio"],
        },
        "extensions": {
            "nse": {"bondmaid_id": "test_bondmaid"},
        },
    }


@pytest.fixture
def minimal_spec_yaml_file(tmp_path: Path, minimal_spec_dict: dict[str, Any]) -> Path:
    """Write the minimal spec dict to a temp YAML file and return the path."""
    spec_path = tmp_path / "spec_minimal.yaml"
    spec_path.write_text(yaml.dump(minimal_spec_dict, allow_unicode=True), encoding="utf-8")
    return spec_path


@pytest.fixture
def sample_vrm_fixture(tmp_path: Path) -> Path:
    """Create a minimal valid glTF binary file for Gate testing.

    This is not a real VRM — it is the smallest valid glTF 2.0 binary
    that the Gate's header reader can parse without Blender.

    The JSON chunk contains a minimal VRM 0.x extension so the Gate rules
    can evaluate against it.
    """
    import struct

    # Minimal glTF JSON with a VRM 0.x extension
    gltf_json = {
        "asset": {"version": "2.0"},
        "extensionsUsed": ["VRM"],
        "extensions": {
            "VRM": {
                "specVersion": "0.0",
                "humanoid": {
                    "humanBones": [
                        {"bone": "hips"},
                        {"bone": "spine"},
                        {"bone": "chest"},
                        {"bone": "neck"},
                        {"bone": "head"},
                        {"bone": "leftShoulder"},
                        {"bone": "rightShoulder"},
                        {"bone": "leftUpperArm"},
                        {"bone": "rightUpperArm"},
                        {"bone": "leftLowerArm"},
                        {"bone": "rightLowerArm"},
                        {"bone": "leftHand"},
                        {"bone": "rightHand"},
                        {"bone": "leftUpperLeg"},
                        {"bone": "rightUpperLeg"},
                        {"bone": "leftLowerLeg"},
                        {"bone": "rightLowerLeg"},
                        {"bone": "leftFoot"},
                        {"bone": "rightFoot"},
                    ]
                },
                "blendShapeMaster": {
                    "blendShapeGroups": [
                        {"presetName": "joy", "name": "Joy"},
                        {"presetName": "angry", "name": "Angry"},
                        {"presetName": "sorrow", "name": "Sorrow"},
                        {"presetName": "fun", "name": "Fun"},
                        {"presetName": "neutral", "name": "Neutral"},
                        {"presetName": "surprised", "name": "Surprised"},
                        {"presetName": "blink", "name": "Blink"},
                        # Visemes
                        {"presetName": "a", "name": "viseme_aa"},
                        {"presetName": "i", "name": "viseme_ih"},
                        {"presetName": "u", "name": "viseme_ou"},
                        {"presetName": "e", "name": "viseme_E"},
                        {"presetName": "o", "name": "viseme_oh"},
                    ]
                },
                "firstPerson": {
                    "lookAtType": "Bone",
                    "lookAt": {"type": "Bone"},
                },
            }
        },
        "meshes": [{"name": "Body"}],
        "materials": [{"name": "Mat1"}, {"name": "Mat2"}],
        "nodes": [{"name": "Root"}],
        "accessors": [],
    }

    json_bytes = json.dumps(gltf_json).encode("utf-8")
    # Pad to 4-byte alignment
    pad = (4 - len(json_bytes) % 4) % 4
    json_bytes += b" " * pad

    # glTF binary: header + JSON chunk
    # Header: magic(4) + version(4) + length(4)
    # Chunk: length(4) + type(4) + data
    MAGIC = 0x46546C67
    VERSION = 2
    CHUNK_TYPE_JSON = 0x4E4F534A

    chunk_data = json_bytes
    chunk_len = len(chunk_data)
    total_len = 12 + 8 + chunk_len

    binary = struct.pack("<III", MAGIC, VERSION, total_len)
    binary += struct.pack("<II", chunk_len, CHUNK_TYPE_JSON)
    binary += chunk_data

    vrm_path = tmp_path / "test_avatar.vrm"
    vrm_path.write_bytes(binary)
    return vrm_path


@pytest.fixture
def tmp_hoard(tmp_path: Path, sample_vrm_fixture: Path) -> Path:
    """Create a minimal temporary Hoard with the sample VRM and a catalog."""
    bases_dir = tmp_path / "data" / "hoard" / "bases"
    bases_dir.mkdir(parents=True, exist_ok=True)

    # Copy the sample VRM into the bases dir
    import shutil

    dest = bases_dir / "AvatarSampleA.vrm"
    shutil.copy(sample_vrm_fixture, dest)

    # Write a catalog
    catalog_path = tmp_path / "data" / "hoard" / "catalog.yaml"
    catalog_data = {
        "format_version": "1",
        "bases": [
            {
                "asset_id": "vroid/sample_a",
                "display_name": "Test Sample A",
                "filename": "AvatarSampleA.vrm",
                "vrm_version": "0.0",
                "tags": ["feminine", "sample"],
                "license": "CC0-1.0",
                "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                "source_url": "https://example.com",
                "sha256": None,
                "cached": True,
                "file_size_bytes": dest.stat().st_size,
            }
        ],
    }
    catalog_path.write_text(yaml.dump(catalog_data), encoding="utf-8")

    return tmp_path
