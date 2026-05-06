"""seidr_smidja.loom.loader — load_and_validate() — the Loom's public entry point.

Loads an AvatarSpec from a YAML/JSON file or a raw dict, validates it fully,
and returns a typed AvatarSpec. Any failure raises LoomValidationError or LoomIOError.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from seidr_smidja.loom.exceptions import LoomIOError, LoomValidationError, ValidationFailure
from seidr_smidja.loom.schema import AvatarSpec

logger = logging.getLogger(__name__)


def _pydantic_errors_to_failures(exc: ValidationError) -> list[ValidationFailure]:
    """Convert pydantic ValidationError into our ValidationFailure list."""
    failures: list[ValidationFailure] = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        reason = error["msg"]
        received = error.get("input")
        failures.append(
            ValidationFailure(field_path=field_path, reason=reason, received_value=received)
        )
    return failures


def load_spec(source: Path | dict[str, Any]) -> AvatarSpec:
    """Load and fully validate an AvatarSpec from a file path or raw dict.

    This is the primary entry point for the Loom domain.

    Args:
        source: A pathlib.Path to a .yaml/.yml/.json file, or a dict of spec data.

    Returns:
        A fully validated, typed AvatarSpec.

    Raises:
        LoomIOError:         If a Path is given but the file cannot be read/parsed.
        LoomValidationError: If the data fails schema validation.
    """
    raw: dict[str, Any]

    if isinstance(source, Path):
        raw = _load_file(source)
    elif isinstance(source, dict):
        raw = source
    else:
        raise LoomIOError(
            f"load_spec() expects a pathlib.Path or dict, got {type(source).__name__}"
        )

    return _validate(raw)


# Keep backwards-compatible alias used in some call sites
load_and_validate = load_spec


def _load_file(path: Path) -> dict[str, Any]:
    """Read and parse a YAML or JSON spec file into a raw dict."""
    if not path.exists():
        raise LoomIOError(f"Spec file not found: {path}")
    if not path.is_file():
        raise LoomIOError(f"Spec path is not a file: {path}")

    suffix = path.suffix.lower()
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LoomIOError(f"Cannot read spec file {path}: {exc}") from exc

    try:
        if suffix in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        elif suffix == ".json":
            data = json.loads(content)
        else:
            raise LoomIOError(
                f"Unsupported spec file extension '{suffix}'. Use .yaml, .yml, or .json."
            )
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise LoomIOError(f"Failed to parse spec file {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise LoomIOError(
            f"Spec file {path} did not parse to a dict (got {type(data).__name__})"
        )
    return data


def _validate(raw: dict[str, Any]) -> AvatarSpec:
    """Validate a raw dict against the AvatarSpec schema."""
    try:
        spec = AvatarSpec.from_dict(raw)
        logger.debug("Loom: spec validated successfully — avatar_id=%s", spec.avatar_id)
        return spec
    except ValidationError as exc:
        failures = _pydantic_errors_to_failures(exc)
        raise LoomValidationError(
            f"Avatar spec validation failed with {len(failures)} error(s).",
            failures=failures,
        ) from exc
    except Exception as exc:
        raise LoomValidationError(
            f"Unexpected error during spec validation: {exc}",
            failures=[
                ValidationFailure(
                    field_path="(root)",
                    reason=str(exc),
                    received_value=type(exc).__name__,
                )
            ],
        ) from exc
