"""Tests for seidr_smidja.gate.vrm_reader — glTF binary parser."""
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any

import pytest

from seidr_smidja.gate.vrm_reader import (
    VRMReadError,
    extract_vrm_compliance_data,
    read_vrm_header,
)

_GLTF_MAGIC = 0x46546C67
_CHUNK_TYPE_JSON = 0x4E4F534A


def _make_gltf(gltf_json: dict[str, Any]) -> bytes:
    """Build a minimal valid glTF 2.0 binary from a JSON dict."""
    json_bytes = json.dumps(gltf_json).encode("utf-8")
    pad = (4 - len(json_bytes) % 4) % 4
    json_bytes += b" " * pad
    chunk_len = len(json_bytes)
    total_len = 12 + 8 + chunk_len
    binary = struct.pack("<III", _GLTF_MAGIC, 2, total_len)
    binary += struct.pack("<II", chunk_len, _CHUNK_TYPE_JSON)
    binary += json_bytes
    return binary


class TestReadVRMHeader:
    def test_reads_sample_fixture(self, sample_vrm_fixture: Path) -> None:
        header = read_vrm_header(sample_vrm_fixture)
        assert isinstance(header, dict)
        assert "extensions" in header

    def test_vrm_0x_extension_present(self, sample_vrm_fixture: Path) -> None:
        header = read_vrm_header(sample_vrm_fixture)
        assert "VRM" in header.get("extensions", {})

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_vrm_header(tmp_path / "ghost.vrm")

    def test_wrong_magic(self, tmp_path: Path) -> None:
        bad = struct.pack("<III", 0xDEADBEEF, 2, 20) + b"\x00" * 8
        path = tmp_path / "bad.vrm"
        path.write_bytes(bad)
        with pytest.raises(VRMReadError, match="magic"):
            read_vrm_header(path)

    def test_too_small(self, tmp_path: Path) -> None:
        path = tmp_path / "tiny.vrm"
        path.write_bytes(b"\x00" * 4)
        with pytest.raises(VRMReadError, match="too small"):
            read_vrm_header(path)

    def test_custom_gltf_binary(self, tmp_path: Path) -> None:
        data = {"asset": {"version": "2.0"}, "meshes": [{"name": "M"}]}
        path = tmp_path / "simple.vrm"
        path.write_bytes(_make_gltf(data))
        header = read_vrm_header(path)
        assert header["asset"]["version"] == "2.0"
        assert len(header["meshes"]) == 1

    def test_json_fallback_for_text_gltf(self, tmp_path: Path) -> None:
        """A text-format glTF should parse via JSON fallback."""
        data = {"asset": {"version": "2.0"}}
        path = tmp_path / "text.gltf"
        path.write_bytes(json.dumps(data).encode("utf-8"))
        header = read_vrm_header(path)
        assert header["asset"]["version"] == "2.0"


class TestExtractVRMComplianceData:
    def test_vrm_0x_full(self, sample_vrm_fixture: Path) -> None:
        header = read_vrm_header(sample_vrm_fixture)
        data = extract_vrm_compliance_data(header)
        assert data["vrm_spec_version"] == "0.0"
        assert "hips" in data["humanoid_bones"]
        assert "joy" in data["blendshape_groups"]
        # Visemes
        assert "a" in data["blendshape_groups"]

    def test_humanoid_bone_count(self, sample_vrm_fixture: Path) -> None:
        header = read_vrm_header(sample_vrm_fixture)
        data = extract_vrm_compliance_data(header)
        # sample_vrm_fixture has 19 humanoid bones
        assert len(data["humanoid_bones"]) == 19

    def test_first_person_extracted(self, sample_vrm_fixture: Path) -> None:
        header = read_vrm_header(sample_vrm_fixture)
        data = extract_vrm_compliance_data(header)
        assert isinstance(data["first_person"], dict)

    def test_empty_header_gives_defaults(self) -> None:
        data = extract_vrm_compliance_data({})
        assert data["vrm_spec_version"] == "unknown"
        assert data["humanoid_bones"] == []
        assert data["blendshape_groups"] == []
        assert data["mesh_count"] == 0

    def test_material_count(self, sample_vrm_fixture: Path) -> None:
        header = read_vrm_header(sample_vrm_fixture)
        data = extract_vrm_compliance_data(header)
        # sample fixture has 2 materials
        assert data["material_count"] == 2

    def test_vrm_1x_dict_humanoid(self, tmp_path: Path) -> None:
        """VRM 1.0 humanBones as dict of bone→node mappings."""
        gltf = {
            "asset": {"version": "2.0"},
            "extensionsUsed": ["VRMC_vrm"],
            "extensions": {
                "VRMC_vrm": {
                    "specVersion": "1.0",
                    "humanoid": {
                        "humanBones": {
                            "hips": {"node": 0},
                            "head": {"node": 1},
                            "spine": {"node": 2},
                        }
                    },
                    "expressions": {
                        "preset": {"happy": {}, "sad": {}, "surprised": {}}
                    },
                    "firstPerson": {"meshAnnotations": []},
                }
            },
        }
        path = tmp_path / "v1.vrm"
        path.write_bytes(_make_gltf(gltf))
        header = read_vrm_header(path)
        data = extract_vrm_compliance_data(header)
        assert data["vrm_spec_version"] == "1.0"
        assert "hips" in data["humanoid_bones"]
        assert "happy" in data["blendshape_groups"]
