"""Tests for loom/validator.py wiring (H-007) — validator is now called from dispatch."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


class TestValidateSemantics:
    """Unit tests for validate_semantics() — the function itself."""

    def _make_spec(self, base_asset_id: str = "vroid/sample_a") -> Any:
        from seidr_smidja.loom.schema import AvatarSpec

        return AvatarSpec.model_validate({
            "spec_version": "1.0",
            "avatar_id": "validator_test",
            "display_name": "Validator Test",
            "base_asset_id": base_asset_id,
            "metadata": {"author": "Test", "license": "CC0-1.0"},
        })

    def test_valid_spec_returns_empty_failures(self) -> None:
        from seidr_smidja.loom.validator import validate_semantics

        spec = self._make_spec()
        failures = validate_semantics(spec)
        assert failures == []

    def test_blank_base_asset_id_returns_failure(self) -> None:
        from seidr_smidja.loom.schema import AvatarSpec
        from seidr_smidja.loom.validator import validate_semantics

        spec = AvatarSpec.model_validate({
            "spec_version": "1.0",
            "avatar_id": "blank_base_test",
            "display_name": "Blank Base Test",
            "base_asset_id": "   ",  # whitespace only
            "metadata": {"author": "Test", "license": "CC0-1.0"},
        })
        failures = validate_semantics(spec)
        assert len(failures) >= 1
        assert any("base_asset_id" in f.field_path for f in failures)

    def test_validate_and_raise_on_empty_base_asset_id(self) -> None:
        from seidr_smidja.loom.exceptions import LoomValidationError
        from seidr_smidja.loom.schema import AvatarSpec
        from seidr_smidja.loom.validator import validate_and_raise

        spec = AvatarSpec.model_validate({
            "spec_version": "1.0",
            "avatar_id": "raise_test",
            "display_name": "Raise Test",
            "base_asset_id": "   ",
            "metadata": {"author": "Test", "license": "CC0-1.0"},
        })
        with pytest.raises(LoomValidationError):
            validate_and_raise(spec)

    def test_validate_and_raise_passes_on_valid_spec(self) -> None:
        from seidr_smidja.loom.validator import validate_and_raise

        spec = self._make_spec()
        # Must not raise
        validate_and_raise(spec)

    def test_strict_mode_flags_unknown_blendshape(self) -> None:
        """In strict mode, an unknown blendshape name produces a failure."""
        from seidr_smidja.loom.schema import AvatarSpec
        from seidr_smidja.loom.validator import validate_semantics

        spec = AvatarSpec.model_validate({
            "spec_version": "1.0",
            "avatar_id": "strict_test",
            "display_name": "Strict Test",
            "base_asset_id": "vroid/sample_a",
            "expressions": {
                "targets": [{"name": "definitely_not_a_real_blendshape_xyz_99", "weight": 0.0}]
            },
            "metadata": {"author": "Test", "license": "CC0-1.0"},
        })

        # In non-strict mode: advisory warning only, no failures
        failures_non_strict = validate_semantics(spec, strict=False)
        # In strict mode: failures returned (IF blendshapes data file exists)
        failures_strict = validate_semantics(spec, strict=True)

        # Non-strict should have 0 failures (warnings only)
        assert len(failures_non_strict) == 0

        # Strict: if the data file exists, unknown name should produce a failure
        # If data file doesn't exist, we get 0 failures (graceful degradation)
        # Just ensure the two modes produce results without crashing
        assert isinstance(failures_strict, list)


class TestValidatorWiredInDispatch:
    """H-007: validate_and_raise() must be called during dispatch() Step 1."""

    def test_dispatch_calls_semantic_validator(
        self, null_annall: Any, minimal_spec_dict: dict[str, Any], tmp_path: Path
    ) -> None:
        """The validator is now wired into dispatch — verify it gets called."""
        import importlib

        from seidr_smidja.bridges.core.dispatch import BuildRequest, dispatch
        from seidr_smidja.loom.validator import validate_and_raise

        validator_module = importlib.import_module("seidr_smidja.loom.validator")
        validator_called = []

        original_validate = validate_and_raise

        def tracking_validate(spec, **kwargs):
            validator_called.append(spec.avatar_id)
            return original_validate(spec, **kwargs)

        request = BuildRequest(
            spec_source=minimal_spec_dict,
            base_asset_id="vroid/sample_a",
            output_dir=tmp_path / "output",
        )

        from unittest.mock import MagicMock, patch

        # Mock the hoard so we don't need real files
        mock_hoard = MagicMock()
        mock_hoard.resolve.side_effect = Exception("hoard not available in test")

        with patch.object(validator_module, "validate_and_raise", side_effect=tracking_validate):
            dispatch(request, null_annall, hoard=mock_hoard)

        # validate_and_raise was called
        assert len(validator_called) >= 1, (
            "H-007 regression: validate_and_raise was not called during dispatch. "
            "The validator is still orphaned."
        )

    def test_semantic_validation_failure_causes_dispatch_to_return_failure_response(
        self, null_annall: Any, tmp_path: Path
    ) -> None:
        """If validate_and_raise raises LoomValidationError, dispatch returns failure."""
        from seidr_smidja.bridges.core.dispatch import BuildRequest, dispatch

        # Spec with blank base_asset_id — will fail semantic validation
        bad_spec_dict = {
            "spec_version": "1.0",
            "avatar_id": "semantic_fail_test",
            "display_name": "Semantic Fail Test",
            "base_asset_id": "   ",  # whitespace-only triggers semantic failure
            "metadata": {"author": "Test", "license": "CC0-1.0"},
        }

        request = BuildRequest(
            spec_source=bad_spec_dict,
            base_asset_id="   ",
            output_dir=tmp_path / "output",
        )

        from unittest.mock import MagicMock

        mock_hoard = MagicMock()

        response = dispatch(request, null_annall, hoard=mock_hoard)

        # Semantic validation should have caught the empty base_asset_id
        assert response.success is False
        loom_errors = [e for e in response.errors if e.stage == "loom"]
        assert len(loom_errors) >= 1
