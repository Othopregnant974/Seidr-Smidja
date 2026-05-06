"""Tests for seidr_smidja.gate.gate — compliance checker."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from seidr_smidja.gate.gate import check, list_rules
from seidr_smidja.gate.models import (
    ComplianceReport,
    ComplianceTarget,
    GateError,
)

# The real rules dir relative to repo root
_REPO_ROOT = Path(__file__).parent.parent.parent
_RULES_DIR = _REPO_ROOT / "data" / "gate"


class TestGateCheck:
    def test_check_sample_vrm_all_targets(
        self, sample_vrm_fixture: Path, null_annall: Any
    ) -> None:
        """The sample fixture VRM should pass Gate checks (it has all required bones/visemes)."""
        report = check(
            vrm_path=sample_vrm_fixture,
            targets=None,
            rules_dir=_RULES_DIR,
            annall=null_annall,
            session_id="test-session",
        )
        assert isinstance(report, ComplianceReport)
        assert report.vrm_path == sample_vrm_fixture

    def test_check_returns_report_always(
        self, sample_vrm_fixture: Path, null_annall: Any
    ) -> None:
        """check() returns ComplianceReport, never raises for compliance failures."""
        report = check(
            vrm_path=sample_vrm_fixture,
            rules_dir=_RULES_DIR,
            annall=null_annall,
            session_id="s1",
        )
        assert isinstance(report, ComplianceReport)
        assert report.elapsed_seconds >= 0.0

    def test_check_specific_vrchat_target(
        self, sample_vrm_fixture: Path, null_annall: Any
    ) -> None:
        report = check(
            vrm_path=sample_vrm_fixture,
            targets=["VRCHAT"],
            rules_dir=_RULES_DIR,
            annall=null_annall,
            session_id="s2",
        )
        assert ComplianceTarget.VRCHAT in report.targets_checked
        assert ComplianceTarget.VTUBE_STUDIO not in report.targets_checked

    def test_check_specific_vtube_target(
        self, sample_vrm_fixture: Path, null_annall: Any
    ) -> None:
        report = check(
            vrm_path=sample_vrm_fixture,
            targets=["VTUBE_STUDIO"],
            rules_dir=_RULES_DIR,
            annall=null_annall,
            session_id="s3",
        )
        assert ComplianceTarget.VTUBE_STUDIO in report.targets_checked

    def test_check_missing_vrm_raises_gate_error(self, tmp_path: Path) -> None:
        with pytest.raises(GateError, match="not found"):
            check(vrm_path=tmp_path / "ghost.vrm", rules_dir=_RULES_DIR)

    def test_check_invalid_target_name_raises_gate_error(
        self, sample_vrm_fixture: Path
    ) -> None:
        with pytest.raises(GateError, match="Unknown compliance target"):
            check(
                vrm_path=sample_vrm_fixture,
                targets=["NOT_A_REAL_TARGET"],
                rules_dir=_RULES_DIR,
            )

    def test_missing_bone_produces_violation(
        self, tmp_path: Path, null_annall: Any
    ) -> None:
        """A VRM missing required humanoid bones should produce violations."""
        import json
        import struct

        # Build a minimal VRM with NO humanoid bones
        gltf = {
            "asset": {"version": "2.0"},
            "extensionsUsed": ["VRM"],
            "extensions": {
                "VRM": {
                    "specVersion": "0.0",
                    "humanoid": {"humanBones": []},
                    "blendShapeMaster": {"blendShapeGroups": []},
                    "firstPerson": {"lookAt": {"type": "Bone"}},
                }
            },
            "meshes": [],
            "materials": [],
            "nodes": [],
            "accessors": [],
        }
        json_bytes = json.dumps(gltf).encode("utf-8")
        pad = (4 - len(json_bytes) % 4) % 4
        json_bytes += b" " * pad
        total_len = 12 + 8 + len(json_bytes)
        magic = 0x46546C67
        binary = struct.pack("<III", magic, 2, total_len)
        binary += struct.pack("<II", len(json_bytes), 0x4E4F534A)
        binary += json_bytes
        path = tmp_path / "boneless.vrm"
        path.write_bytes(binary)

        report = check(
            vrm_path=path,
            targets=["VRCHAT"],
            rules_dir=_RULES_DIR,
            annall=null_annall,
            session_id="s4",
        )
        violations = report.all_violations()
        # Should have bone violations
        bone_violations = [
            v for v in violations if "bone" in v.rule_id
        ]
        assert len(bone_violations) > 0

    def test_check_without_annall(self, sample_vrm_fixture: Path) -> None:
        """check() works with annall=None (no logging)."""
        report = check(
            vrm_path=sample_vrm_fixture,
            targets=["VRCHAT"],
            rules_dir=_RULES_DIR,
        )
        assert isinstance(report, ComplianceReport)

    def test_sample_vrm_passes_vrchat_bones(
        self, sample_vrm_fixture: Path
    ) -> None:
        """sample_vrm_fixture has all 19 required VRChat humanoid bones."""
        report = check(
            vrm_path=sample_vrm_fixture,
            targets=["VRCHAT"],
            rules_dir=_RULES_DIR,
        )
        bone_violations = [
            v for v in report.all_violations() if "humanoid_bones" in v.rule_id
        ]
        assert bone_violations == []


class TestListRules:
    def test_list_vrchat_rules(self) -> None:
        rules = list_rules(ComplianceTarget.VRCHAT, rules_dir=_RULES_DIR)
        assert len(rules) > 0
        ids = [r.rule_id for r in rules]
        assert "vrchat.humanoid_bones.required" in ids

    def test_list_vtube_rules(self) -> None:
        rules = list_rules(ComplianceTarget.VTUBE_STUDIO, rules_dir=_RULES_DIR)
        assert len(rules) > 0
        ids = [r.rule_id for r in rules]
        assert "vtube.vrm_version" in ids

    def test_missing_rules_dir_raises(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty_rules"
        empty_dir.mkdir()
        with pytest.raises(GateError, match="not found"):
            list_rules(ComplianceTarget.VRCHAT, rules_dir=empty_dir)


class TestComplianceReport:
    def test_all_violations(self, sample_vrm_fixture: Path) -> None:
        report = check(
            vrm_path=sample_vrm_fixture,
            rules_dir=_RULES_DIR,
        )
        violations = report.all_violations()
        assert isinstance(violations, list)

    def test_target_result_errors_and_warnings(
        self, sample_vrm_fixture: Path
    ) -> None:
        report = check(
            vrm_path=sample_vrm_fixture,
            targets=["VRCHAT"],
            rules_dir=_RULES_DIR,
        )
        for result in report.results.values():
            errors = result.errors
            warnings = result.warnings
            assert isinstance(errors, list)
            assert isinstance(warnings, list)
