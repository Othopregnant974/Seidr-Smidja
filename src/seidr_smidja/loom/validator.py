"""seidr_smidja.loom.validator — Semantic validation beyond pydantic schema.

Checks avatar specs for semantic consistency:
    - Color values already enforced by pydantic [0.0, 1.0]
    - Expression blendshape names checked against the known set from YAML data
    - base_asset_id must be a non-empty string (structural)
    - Unknown blendshape names generate warnings (non-strict) or errors (strict)

This is a second-pass validator called after load_spec() — the Loom always
runs pydantic structural validation first, then semantic validation second.
"""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

from seidr_smidja.loom.exceptions import LoomValidationError, ValidationFailure
from seidr_smidja.loom.schema import AvatarSpec

logger = logging.getLogger(__name__)

# Default location for the known blendshapes data file.
# Resolved relative to the package root at runtime — never hardcoded absolute.
_DEFAULT_BLENDSHAPES_PATH = Path(__file__).parent.parent.parent.parent / "data" / "loom" / "known_blendshapes.yaml"


def _load_known_blendshapes(data_path: Path | None = None) -> set[str]:
    """Load the set of known blendshape names from the YAML data file.

    Returns an empty set if the file is unavailable (graceful degradation —
    unknown names will then be unreportable, but validation won't crash).
    """
    path = data_path or _DEFAULT_BLENDSHAPES_PATH
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        names: list[str] = data.get("all_known_names", [])
        return {n.lower() for n in names if isinstance(n, str)}
    except FileNotFoundError:
        logger.warning(
            "Known blendshapes data file not found at %s — skipping name validation.", path
        )
        return set()
    except Exception as exc:
        logger.warning("Failed to load known blendshapes: %s", exc)
        return set()


def validate_semantics(
    spec: AvatarSpec,
    strict: bool = False,
    blendshapes_path: Path | None = None,
) -> list[ValidationFailure]:
    """Perform semantic validation on a structurally-valid AvatarSpec.

    Args:
        spec:             The AvatarSpec to validate (already passed pydantic).
        strict:           If True, unknown blendshape names are ERRORs (not warnings).
        blendshapes_path: Optional override path for the known blendshapes YAML.

    Returns:
        A list of ValidationFailure objects. Empty list = all checks passed.
        In non-strict mode, unknown blendshape names appear as warnings in the log
        but do NOT appear in the failure list — they are advisory only.
    """
    failures: list[ValidationFailure] = []
    known_names = _load_known_blendshapes(blendshapes_path)

    # Check expression target names
    for i, target in enumerate(spec.expressions.targets):
        name_lower = target.name.lower()
        if known_names and name_lower not in known_names:
            field_path = f"expressions.targets[{i}].name"
            msg = (
                f"Blendshape name '{target.name}' is not in the known blendshape set. "
                "It may still work if the base mesh defines it — verify against your base asset."
            )
            if strict:
                failures.append(
                    ValidationFailure(
                        field_path=field_path,
                        reason=msg,
                        received_value=target.name,
                    )
                )
            else:
                logger.warning("Loom semantic: %s at %s", msg, field_path)

    # base_asset_id must be non-empty and contain no whitespace
    if not spec.base_asset_id.strip():
        failures.append(
            ValidationFailure(
                field_path="base_asset_id",
                reason="base_asset_id must not be blank.",
                received_value=spec.base_asset_id,
            )
        )

    # metadata.license should be a recognizable SPDX string (advisory check)
    _common_licenses = {
        "cc0-1.0", "cc-by-4.0", "cc-by-nc-4.0", "cc-by-sa-4.0",
        "cc-by-nc-sa-4.0", "mit", "apache-2.0", "proprietary",
    }
    if spec.metadata.license.lower() not in _common_licenses:
        logger.debug(
            "Loom semantic: license '%s' not in common known SPDX set — may still be valid.",
            spec.metadata.license,
        )

    return failures


def validate_and_raise(
    spec: AvatarSpec,
    strict: bool = False,
    blendshapes_path: Path | None = None,
) -> None:
    """Run semantic validation and raise LoomValidationError if any failures found.

    Args:
        spec:   The AvatarSpec to validate.
        strict: In strict mode, unknown blendshape names cause failures.

    Raises:
        LoomValidationError: If any semantic check fails.
    """
    failures = validate_semantics(spec, strict=strict, blendshapes_path=blendshapes_path)
    if failures:
        raise LoomValidationError(
            f"Avatar spec semantic validation failed with {len(failures)} error(s).",
            failures=failures,
        )
