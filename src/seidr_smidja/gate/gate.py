"""seidr_smidja.gate.gate — Gate compliance checker.

check() is the public API. Loads VRM header, loads compliance rules from YAML,
applies each rule, returns a ComplianceReport. All rules from YAML — none hardcoded.

Per PHILOSOPHY: fail loud at the Gate. A blade that cannot cut has not been made.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import yaml

from seidr_smidja.gate.models import (
    ComplianceReport,
    ComplianceRule,
    ComplianceTarget,
    GateError,
    TargetResult,
    Violation,
    ViolationSeverity,
)
from seidr_smidja.gate.vrm_reader import VRMReadError, extract_vrm_compliance_data, read_vrm_header

logger = logging.getLogger(__name__)

# Default rules directory — resolved relative to project at startup, not hardcoded.
_DEFAULT_RULES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "gate"


def _load_rules(rules_file: Path) -> tuple[list[ComplianceRule], dict[str, Any]]:
    """Load compliance rules from a YAML file.

    Returns:
        (rules_list, raw_data) — the parsed ComplianceRule objects and the full
        raw YAML dict (needed for performance_tiers, accepted_versions, etc.)
    """
    try:
        with rules_file.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except FileNotFoundError as exc:
        raise GateError(f"Rules file not found: {rules_file}") from exc
    except Exception as exc:
        raise GateError(f"Failed to load rules from {rules_file}: {exc}") from exc

    raw_rules: list[dict[str, Any]] = data.get("rules", [])
    rules: list[ComplianceRule] = []
    for entry in raw_rules:
        rule_id = entry.get("rule_id", "unknown")
        rules.append(
            ComplianceRule(
                rule_id=rule_id,
                display_name=entry.get("display_name", rule_id),
                severity=entry.get("severity", "ERROR"),
                description=entry.get("description", ""),
                **{k: v for k, v in entry.items()
                   if k not in ("rule_id", "display_name", "severity", "description")},
            )
        )
    return rules, data


def _check_vrchat(
    vrm_data: dict[str, Any],
    rules: list[ComplianceRule],
    raw_data: dict[str, Any],
    tier: str = "Good",
) -> TargetResult:
    """Apply VRChat compliance rules to extracted VRM data."""
    violations: list[Violation] = []
    tier_budgets: dict[str, Any] = (
        raw_data.get("performance_tiers", {}).get(tier, {})
    )

    bone_names_lower = {b.lower() for b in vrm_data.get("humanoid_bones", [])}
    blendshapes_lower = {b.lower() for b in vrm_data.get("blendshape_groups", [])}

    for rule in rules:
        rid = rule.rule_id

        if rid == "vrchat.humanoid_bones.required":
            required = [b.lower() for b in rule.extra.get("required_bones", [])]
            missing = [b for b in required if b not in bone_names_lower]
            if missing:
                violations.append(
                    Violation(
                        rule_id=rid,
                        severity=rule.severity,
                        field_path="humanoid.bones",
                        description=f"Missing required humanoid bones: {missing}",
                        actual_value=sorted(bone_names_lower),
                        limit_value=required,
                    )
                )

        elif rid.startswith("vrchat.visemes."):
            # Each viseme rule checks for one blendshape name
            viseme_name = rid.split("vrchat.visemes.")[-1].lower()
            # Map common viseme variants
            variants = {
                viseme_name,
                f"viseme_{viseme_name}",
                viseme_name.upper(),
                f"viseme_{viseme_name.upper()}",
            }
            if not any(v.lower() in blendshapes_lower for v in variants):
                violations.append(
                    Violation(
                        rule_id=rid,
                        severity=rule.severity,
                        field_path=rule.extra.get("field_path", f"blendShapes.{viseme_name}"),
                        description=rule.description,
                        actual_value=sorted(blendshapes_lower),
                        limit_value=viseme_name,
                    )
                )

        elif rid == "vrchat.polycount":
            budget = tier_budgets.get("polycount")
            # Actual polygon count requires parsing the binary chunk.
            # In v0.1 structural-only mode, we skip this check with a note.
            # TODO(forge-worker): integrate a full glTF mesh parser when available.
            if budget is not None:
                logger.debug(
                    "Gate: polycount check skipped in v0.1 structural mode (budget: %d).", budget
                )
                # AUDIT-008 fix: Emit an advisory WARNING so agents are never silently
                # passed a VRM that might exceed polygon budget.
                # Design intent: WARNINGs from unevaluated rules do NOT set passed=False
                # (they are advisories, not hard failures). They appear in the report so
                # the calling agent can trigger a manual or downstream check.
                # This satisfies Unbreakable Vow 2's spirit until full glTF mesh
                # parsing lands in v0.1.1.
                violations.append(
                    Violation(
                        rule_id=rid,
                        severity=ViolationSeverity.WARNING,
                        field_path=rule.extra.get("field_path", "mesh.polycount"),
                        description=(
                            "Rule not evaluated in v0.1 — manual check required. "
                            f"Budget for '{tier}' tier: {budget} polygons."
                        ),
                        actual_value=None,
                        limit_value=budget,
                    )
                )

        elif rid == "vrchat.texture_memory":
            budget_mb = tier_budgets.get("texture_memory_mb")
            # Actual texture memory requires inspecting binary image data.
            # In v0.1 structural-only mode, we skip this check with an advisory.
            # TODO(forge-worker): integrate texture size inspection when glTF binary
            # chunk parsing is available.
            if budget_mb is not None:
                logger.debug(
                    "Gate: texture_memory check skipped in v0.1 structural mode (budget: %d MB).",
                    budget_mb,
                )
            # AUDIT-008 fix: Always emit the advisory WARNING so agents see the
            # unevaluated rule regardless of whether a tier budget is configured.
            violations.append(
                Violation(
                    rule_id=rid,
                    severity=ViolationSeverity.WARNING,
                    field_path=rule.extra.get("field_path", "textures.estimated_memory_mb"),
                    description=(
                        "Rule not evaluated in v0.1 — manual check required. "
                        + (
                            f"Budget for '{tier}' tier: {budget_mb} MB."
                            if budget_mb is not None
                            else "No tier budget configured — check vrchat_rules.yaml."
                        )
                    ),
                    actual_value=None,
                    limit_value=budget_mb,
                )
            )

        elif rid == "vrchat.material_count":
            budget = tier_budgets.get("material_count")
            actual = vrm_data.get("material_count", 0)
            if budget is not None and actual > budget:
                violations.append(
                    Violation(
                        rule_id=rid,
                        severity=rule.severity,
                        field_path="materials.count",
                        description=f"Material count {actual} exceeds {tier} tier budget {budget}.",
                        actual_value=actual,
                        limit_value=budget,
                    )
                )

    passed = not any(v.severity == ViolationSeverity.ERROR for v in violations)
    return TargetResult(
        target=ComplianceTarget.VRCHAT, passed=passed, violations=violations
    )


def _check_vtube(
    vrm_data: dict[str, Any],
    rules: list[ComplianceRule],
    raw_data: dict[str, Any],
) -> TargetResult:
    """Apply VTube Studio compliance rules to extracted VRM data."""
    violations: list[Violation] = []
    blendshapes_lower = {b.lower() for b in vrm_data.get("blendshape_groups", [])}
    bone_names_lower = {b.lower() for b in vrm_data.get("humanoid_bones", [])}

    for rule in rules:
        rid = rule.rule_id

        if rid == "vtube.vrm_version":
            accepted = [v.lower() for v in rule.extra.get("accepted_versions", ["0.0", "1.0"])]
            actual = vrm_data.get("vrm_spec_version", "unknown").lower()
            if actual not in accepted:
                violations.append(
                    Violation(
                        rule_id=rid,
                        severity=rule.severity,
                        field_path="vrm.specVersion",
                        description=f"VRM version '{actual}' not accepted. Accepted: {accepted}",
                        actual_value=actual,
                        limit_value=accepted,
                    )
                )

        elif rid.startswith("vtube.expression."):
            # Each expression rule checks for one blendshape preset
            expr_name = rid.split("vtube.expression.")[-1].lower()
            if expr_name not in blendshapes_lower:
                violations.append(
                    Violation(
                        rule_id=rid,
                        severity=rule.severity,
                        field_path=rule.extra.get("field_path", f"blendShapeGroups.{expr_name}"),
                        description=rule.description,
                        actual_value=sorted(blendshapes_lower),
                        limit_value=expr_name,
                    )
                )

        elif rid == "vtube.lookat_sane":
            fp = vrm_data.get("first_person", {})
            lookat = fp.get("lookAt", fp.get("lookAtTypeName", {}))
            valid_types = [t.lower() for t in rule.extra.get("valid_lookat_types", ["Bone", "BlendShape"])]
            if isinstance(lookat, dict):
                lookat_type = lookat.get("type", lookat.get("lookAtTypeName", "")).lower()
            elif isinstance(lookat, str):
                lookat_type = lookat.lower()
            else:
                lookat_type = ""
            if lookat_type and lookat_type not in valid_types:
                violations.append(
                    Violation(
                        rule_id=rid,
                        severity=rule.severity,
                        field_path="firstPerson.lookAt",
                        description=f"LookAt type '{lookat_type}' is not valid. Expected: {valid_types}",
                        actual_value=lookat_type,
                        limit_value=valid_types,
                    )
                )

        elif rid in ("vtube.humanoid_bones.head", "vtube.humanoid_bones.neck"):
            bone_name = rid.split(".")[-1].lower()
            if bone_name not in bone_names_lower:
                violations.append(
                    Violation(
                        rule_id=rid,
                        severity=rule.severity,
                        field_path=f"humanoid.bones.{bone_name}",
                        description=rule.description,
                        actual_value=sorted(bone_names_lower),
                        limit_value=bone_name,
                    )
                )

        elif rid == "vtube.first_person_bone":
            # AUDIT-008 fix: firstPersonBone evaluation requires inspecting the VRM
            # firstPerson extension field beyond what structural parsing exposes in v0.1.
            # Emit an advisory WARNING so agents are never silently unaware.
            # TODO(forge-worker): read firstPerson.firstPersonBone from VRM data when
            # full firstPerson extraction is implemented.
            violations.append(
                Violation(
                    rule_id=rid,
                    severity=ViolationSeverity.WARNING,
                    field_path=rule.extra.get("field_path", "firstPerson.firstPersonBone"),
                    description=(
                        "Rule not evaluated in v0.1 — manual check required. "
                        "Verify that firstPerson.firstPersonBone is set to the head bone."
                    ),
                    actual_value=None,
                    limit_value="head bone",
                )
            )

        elif rid == "vtube.eye_bones":
            # AUDIT-008 fix: eye bone evaluation requires inspecting humanoid bone list
            # for leftEye / rightEye entries specifically. In v0.1 structural mode we
            # emit an advisory WARNING instead of silently skipping.
            # TODO(forge-worker): check bone_names_lower for leftEye/rightEye entries
            # once the VRM humanoid bone reader fully enumerates all optional bones.
            violations.append(
                Violation(
                    rule_id=rid,
                    severity=ViolationSeverity.WARNING,
                    field_path=rule.extra.get("field_path", "humanoid.bones.leftEye"),
                    description=(
                        "Rule not evaluated in v0.1 — manual check required. "
                        "Verify that leftEye and/or rightEye bones are present for eye tracking."
                    ),
                    actual_value=None,
                    limit_value="leftEye or rightEye",
                )
            )

    passed = not any(v.severity == ViolationSeverity.ERROR for v in violations)
    return TargetResult(
        target=ComplianceTarget.VTUBE_STUDIO, passed=passed, violations=violations
    )


def check(
    vrm_path: Path,
    targets: list[str] | None = None,
    rules_dir: Path | None = None,
    vrchat_tier: str = "Good",
    annall: Any = None,
    session_id: Any = None,
) -> ComplianceReport:
    """Validate a .vrm file against compliance targets.

    Args:
        vrm_path:    Path to the .vrm file. Must exist.
        targets:     List of target names ("VRCHAT", "VTUBE_STUDIO"). None = all.
        rules_dir:   Override rules directory. Default: data/gate/.
        vrchat_tier: VRChat performance tier to check against. Default: "Good".
        annall:      Optional AnnallPort for event logging.
        session_id:  Session ID for Annáll events.

    Returns:
        ComplianceReport — always returned (never raises for compliance failures).

    Raises:
        GateError: On infrastructure failure (corrupt VRM, missing rules file, I/O).
    """
    start_time = time.monotonic()

    if not vrm_path.exists():
        raise GateError(f"VRM file not found: {vrm_path}")

    # Resolve which targets to check
    target_enums: list[ComplianceTarget]
    if targets is None:
        target_enums = list(ComplianceTarget)
    else:
        try:
            target_enums = [ComplianceTarget(t.upper()) for t in targets]
        except ValueError as exc:
            raise GateError(f"Unknown compliance target: {exc}") from exc

    _rules_dir = rules_dir or _DEFAULT_RULES_DIR

    # Parse VRM header
    try:
        header = read_vrm_header(vrm_path)
        vrm_data = extract_vrm_compliance_data(header)
    except VRMReadError as exc:
        raise GateError(f"Cannot parse VRM file: {exc}", cause=exc) from exc

    results: dict[str, TargetResult] = {}

    for target in target_enums:
        if target == ComplianceTarget.VRCHAT:
            rules_file = _rules_dir / "vrchat_rules.yaml"
            rules, raw_data = _load_rules(rules_file)
            result = _check_vrchat(vrm_data, rules, raw_data, tier=vrchat_tier)
            results[target.value] = result

        elif target == ComplianceTarget.VTUBE_STUDIO:
            rules_file = _rules_dir / "vtube_rules.yaml"
            rules, raw_data = _load_rules(rules_file)
            result = _check_vtube(vrm_data, rules, raw_data)
            results[target.value] = result

    overall_passed = all(r.passed for r in results.values())
    elapsed = time.monotonic() - start_time

    report = ComplianceReport(
        vrm_path=vrm_path,
        targets_checked=target_enums,
        passed=overall_passed,
        results=results,
        elapsed_seconds=elapsed,
    )

    # Log to Annáll if provided
    if annall is not None and session_id is not None:
        try:
            from seidr_smidja.annall.port import AnnallEvent

            total_violations = len(report.all_violations())
            annall.log_event(
                session_id,
                AnnallEvent.info(
                    "gate.checked",
                    {
                        "passed": overall_passed,
                        "violations_count": total_violations,
                        "targets": [t.value for t in target_enums],
                        "elapsed_seconds": elapsed,
                    },
                ),
            )
        except Exception:
            pass  # Annáll failure must never crash the Gate

    logger.info(
        "Gate check: %s | passed=%s | targets=%s | violations=%d | elapsed=%.2fs",
        vrm_path.name,
        overall_passed,
        [t.value for t in target_enums],
        len(report.all_violations()),
        elapsed,
    )

    return report


def list_rules(target: ComplianceTarget, rules_dir: Path | None = None) -> list[ComplianceRule]:
    """Return the compliance rules defined for a given target.

    Args:
        target:    The target to list rules for.
        rules_dir: Override rules directory.

    Returns:
        List of ComplianceRule objects.

    Raises:
        GateError: If the rule file cannot be read.
    """
    _rules_dir = rules_dir or _DEFAULT_RULES_DIR
    if target == ComplianceTarget.VRCHAT:
        rules_file = _rules_dir / "vrchat_rules.yaml"
    elif target == ComplianceTarget.VTUBE_STUDIO:
        rules_file = _rules_dir / "vtube_rules.yaml"
    else:
        raise GateError(f"Unknown target: {target}")

    rules, _ = _load_rules(rules_file)
    return rules
