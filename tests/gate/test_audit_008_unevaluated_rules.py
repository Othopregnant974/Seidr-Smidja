"""AUDIT-008 regression tests — unevaluated Gate rules must produce advisory WARNINGs.

Design contract (AUDIT-008 fix):
  - When a rule exists in the YAML but full evaluation is not implemented in v0.1,
    the Gate appends a Violation(severity=WARNING) to the report.
  - WARNING violations do NOT set passed=False (they are advisories, not hard failures).
  - The advisory Violation carries the rule_id and any relevant budget/threshold from YAML
    so the calling agent has enough information to perform a manual check.

Affected rules:
  - vrchat.polycount     (VRChat — polygon budget, tier-dependent)
  - vrchat.texture_memory (VRChat — texture memory budget, tier-dependent)
  - vtube.first_person_bone (VTube Studio — firstPerson offset bone)
  - vtube.eye_bones         (VTube Studio — eye tracking bones)
"""
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any

import pytest

from seidr_smidja.gate.gate import check
from seidr_smidja.gate.models import (
    ComplianceTarget,
    ViolationSeverity,
)

_REPO_ROOT = Path(__file__).parent.parent.parent
_RULES_DIR = _REPO_ROOT / "data" / "gate"


def _build_minimal_vrm(tmp_path: Path, *, bones: list[str], blendshapes: list[str]) -> Path:
    """Build the smallest valid glTF binary the Gate can parse for AUDIT-008 tests.

    All required bones and blendshapes are injected so the only violations
    in the report should be the unevaluated-rule advisories we are testing.
    """
    gltf = {
        "asset": {"version": "2.0"},
        "extensionsUsed": ["VRM"],
        "extensions": {
            "VRM": {
                "specVersion": "0.0",
                "humanoid": {
                    "humanBones": [{"bone": b} for b in bones],
                },
                "blendShapeMaster": {
                    "blendShapeGroups": [
                        {"presetName": bs.lower(), "name": bs} for bs in blendshapes
                    ]
                },
                "firstPerson": {
                    "lookAtType": "Bone",
                    "lookAt": {"type": "Bone"},
                },
            }
        },
        "meshes": [{"name": "Body"}],
        "materials": [{"name": "Mat1"}],
        "nodes": [],
        "accessors": [],
    }
    json_bytes = json.dumps(gltf).encode("utf-8")
    pad = (4 - len(json_bytes) % 4) % 4
    json_bytes += b" " * pad
    total_len = 12 + 8 + len(json_bytes)
    binary = struct.pack("<III", 0x46546C67, 2, total_len)
    binary += struct.pack("<II", len(json_bytes), 0x4E4F534A)
    binary += json_bytes
    path = tmp_path / "test_audit008.vrm"
    path.write_bytes(binary)
    return path


# All 19 required VRChat humanoid bones
_FULL_BONES = [
    "hips", "spine", "chest", "neck", "head",
    "leftShoulder", "rightShoulder",
    "leftUpperArm", "rightUpperArm",
    "leftLowerArm", "rightLowerArm",
    "leftHand", "rightHand",
    "leftUpperLeg", "rightUpperLeg",
    "leftLowerLeg", "rightLowerLeg",
    "leftFoot", "rightFoot",
]

# All required VRChat visemes
_FULL_VISEMES = [
    "viseme_sil", "viseme_pp", "viseme_ff", "viseme_th", "viseme_dd",
    "viseme_kk", "viseme_ch", "viseme_ss", "viseme_nn", "viseme_rr",
    "viseme_aa", "viseme_E", "viseme_ih", "viseme_oh", "viseme_ou",
]

# All required VTube expressions
_FULL_EXPRESSIONS = ["Joy", "Angry", "Sorrow", "Fun"]


class TestAudit008VRChatUnevaluatedRules:
    """vrchat.polycount and vrchat.texture_memory must produce WARNING advisories."""

    def test_polycount_rule_produces_warning_advisory(
        self, tmp_path: Path, null_annall: Any
    ) -> None:
        """A VRM with no detected polycount violation still gets a WARNING advisory
        for vrchat.polycount because the check is not implemented in v0.1."""
        vrm = _build_minimal_vrm(
            tmp_path,
            bones=_FULL_BONES,
            blendshapes=_FULL_VISEMES,
        )
        report = check(
            vrm_path=vrm,
            targets=["VRCHAT"],
            rules_dir=_RULES_DIR,
            vrchat_tier="Good",
            annall=null_annall,
            session_id="audit008-polycount",
        )

        rule_ids = [v.rule_id for v in report.all_violations()]
        assert "vrchat.polycount" in rule_ids, (
            "Expected an advisory WARNING for vrchat.polycount but none was found."
        )

        polycount_violations = [
            v for v in report.all_violations() if v.rule_id == "vrchat.polycount"
        ]
        assert len(polycount_violations) == 1
        pv = polycount_violations[0]
        assert pv.severity == ViolationSeverity.WARNING, (
            f"Expected WARNING severity, got {pv.severity}"
        )
        assert "manual check required" in pv.description.lower()
        # The budget value should appear in the violation details
        assert pv.limit_value is not None, (
            "Violation should carry the polygon budget from the YAML tier config."
        )

    def test_polycount_warning_does_not_cause_is_compliant_false(
        self, tmp_path: Path, null_annall: Any
    ) -> None:
        """WARNING violations from unevaluated rules must not flip passed=False.
        Only ERROR-severity violations cause a target to fail."""
        vrm = _build_minimal_vrm(
            tmp_path,
            bones=_FULL_BONES,
            blendshapes=_FULL_VISEMES,
        )
        report = check(
            vrm_path=vrm,
            targets=["VRCHAT"],
            rules_dir=_RULES_DIR,
            vrchat_tier="Good",
            annall=null_annall,
            session_id="audit008-polycount-passed",
        )

        vrchat_result = report.results.get(ComplianceTarget.VRCHAT.value)
        assert vrchat_result is not None

        # Warnings are advisory — they must not set passed=False
        error_violations = [
            v for v in vrchat_result.violations
            if v.severity == ViolationSeverity.ERROR
        ]
        if error_violations:
            pytest.skip(
                f"Sample has error violations unrelated to unevaluated rules: "
                f"{[v.rule_id for v in error_violations]}"
            )

        assert vrchat_result.passed, (
            "A target with only WARNING violations should still have passed=True."
        )

    def test_texture_memory_rule_produces_warning_advisory(
        self, tmp_path: Path, null_annall: Any
    ) -> None:
        """vrchat.texture_memory is unevaluated in v0.1 and must emit a WARNING."""
        vrm = _build_minimal_vrm(
            tmp_path,
            bones=_FULL_BONES,
            blendshapes=_FULL_VISEMES,
        )
        report = check(
            vrm_path=vrm,
            targets=["VRCHAT"],
            rules_dir=_RULES_DIR,
            annall=null_annall,
            session_id="audit008-texture-memory",
        )

        rule_ids = [v.rule_id for v in report.all_violations()]
        assert "vrchat.texture_memory" in rule_ids, (
            "Expected an advisory WARNING for vrchat.texture_memory but none was found."
        )

        texture_violations = [
            v for v in report.all_violations() if v.rule_id == "vrchat.texture_memory"
        ]
        assert len(texture_violations) == 1
        tv = texture_violations[0]
        assert tv.severity == ViolationSeverity.WARNING
        assert "manual check required" in tv.description.lower()


class TestAudit008VTubeUnevaluatedRules:
    """vtube.first_person_bone and vtube.eye_bones must produce WARNING advisories."""

    def test_first_person_bone_produces_warning_advisory(
        self, tmp_path: Path, null_annall: Any
    ) -> None:
        """vtube.first_person_bone is unevaluated in v0.1 and must emit a WARNING."""
        vrm = _build_minimal_vrm(
            tmp_path,
            bones=_FULL_BONES,
            blendshapes=_FULL_EXPRESSIONS,
        )
        report = check(
            vrm_path=vrm,
            targets=["VTUBE_STUDIO"],
            rules_dir=_RULES_DIR,
            annall=null_annall,
            session_id="audit008-vtube-fpbone",
        )

        rule_ids = [v.rule_id for v in report.all_violations()]
        assert "vtube.first_person_bone" in rule_ids, (
            "Expected an advisory WARNING for vtube.first_person_bone but none was found."
        )

        fp_violations = [
            v for v in report.all_violations() if v.rule_id == "vtube.first_person_bone"
        ]
        assert len(fp_violations) == 1
        fpv = fp_violations[0]
        assert fpv.severity == ViolationSeverity.WARNING
        assert "manual check required" in fpv.description.lower()

    def test_eye_bones_produces_warning_advisory(
        self, tmp_path: Path, null_annall: Any
    ) -> None:
        """vtube.eye_bones is unevaluated in v0.1 and must emit a WARNING."""
        vrm = _build_minimal_vrm(
            tmp_path,
            bones=_FULL_BONES,
            blendshapes=_FULL_EXPRESSIONS,
        )
        report = check(
            vrm_path=vrm,
            targets=["VTUBE_STUDIO"],
            rules_dir=_RULES_DIR,
            annall=null_annall,
            session_id="audit008-vtube-eyebones",
        )

        rule_ids = [v.rule_id for v in report.all_violations()]
        assert "vtube.eye_bones" in rule_ids, (
            "Expected an advisory WARNING for vtube.eye_bones but none was found."
        )

        eye_violations = [
            v for v in report.all_violations() if v.rule_id == "vtube.eye_bones"
        ]
        assert len(eye_violations) == 1
        ev = eye_violations[0]
        assert ev.severity == ViolationSeverity.WARNING
        assert "manual check required" in ev.description.lower()

    def test_first_person_bone_warning_does_not_fail_target(
        self, tmp_path: Path, null_annall: Any
    ) -> None:
        """Advisory WARNINGs from vtube.first_person_bone and vtube.eye_bones
        must not cause the VTube Studio target to fail (passed=False)."""
        vrm = _build_minimal_vrm(
            tmp_path,
            bones=_FULL_BONES,
            blendshapes=_FULL_EXPRESSIONS,
        )
        report = check(
            vrm_path=vrm,
            targets=["VTUBE_STUDIO"],
            rules_dir=_RULES_DIR,
            annall=null_annall,
            session_id="audit008-vtube-warning-no-fail",
        )

        vtube_result = report.results.get(ComplianceTarget.VTUBE_STUDIO.value)
        assert vtube_result is not None

        error_violations = vtube_result.errors
        advisory_ids = {"vtube.first_person_bone", "vtube.eye_bones"}
        non_advisory_errors = [
            v for v in error_violations if v.rule_id not in advisory_ids
        ]
        if non_advisory_errors:
            pytest.skip(
                f"Sample has error violations unrelated to AUDIT-008: "
                f"{[v.rule_id for v in non_advisory_errors]}"
            )

        assert vtube_result.passed, (
            "Target should pass when only advisory WARNINGs are present."
        )
