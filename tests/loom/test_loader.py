"""Tests for seidr_smidja.loom.loader — load_spec() and friends."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from seidr_smidja.loom.exceptions import LoomIOError, LoomValidationError
from seidr_smidja.loom.loader import load_and_validate, load_spec


class TestLoadSpecFromDict:
    def test_valid_minimal_dict(self, minimal_spec_dict: dict[str, Any]) -> None:
        spec = load_spec(minimal_spec_dict)
        assert spec.avatar_id == "test_avatar_v1"

    def test_valid_full_dict(self, full_spec_dict: dict[str, Any]) -> None:
        spec = load_spec(full_spec_dict)
        assert spec.avatar_id == "full_test_avatar"

    def test_invalid_dict_raises_loom_validation_error(self) -> None:
        bad = {"spec_version": "1.0"}  # missing required fields
        with pytest.raises(LoomValidationError) as exc_info:
            load_spec(bad)
        assert exc_info.value.failures  # non-empty failure list

    def test_validation_error_has_field_paths(self) -> None:
        bad = {"spec_version": "99.9", "avatar_id": "ok", "display_name": "X",
               "base_asset_id": "y", "metadata": {"author": "A"}}
        with pytest.raises(LoomValidationError) as exc_info:
            load_spec(bad)
        failure_fields = [f.field_path for f in exc_info.value.failures]
        assert any("spec_version" in fp for fp in failure_fields)

    def test_wrong_type_raises_loom_io_error(self) -> None:
        with pytest.raises(LoomIOError):
            load_spec("not a path or dict")  # type: ignore[arg-type]


class TestLoadSpecFromFile:
    def test_yaml_file(self, minimal_spec_yaml_file: Path) -> None:
        spec = load_spec(minimal_spec_yaml_file)
        assert spec.avatar_id == "test_avatar_v1"

    def test_json_file(self, minimal_spec_dict: dict[str, Any], tmp_path: Path) -> None:
        p = tmp_path / "spec.json"
        p.write_text(json.dumps(minimal_spec_dict), encoding="utf-8")
        spec = load_spec(p)
        assert spec.avatar_id == "test_avatar_v1"

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(LoomIOError, match="not found"):
            load_spec(tmp_path / "nonexistent.yaml")

    def test_directory_path(self, tmp_path: Path) -> None:
        with pytest.raises(LoomIOError, match="not a file"):
            load_spec(tmp_path)

    def test_malformed_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yaml"
        p.write_text("{bad yaml: : :", encoding="utf-8")
        with pytest.raises(LoomIOError, match="parse"):
            load_spec(p)

    def test_malformed_json(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(LoomIOError, match="parse"):
            load_spec(p)

    def test_unsupported_extension(self, tmp_path: Path) -> None:
        p = tmp_path / "spec.toml"
        p.write_text("key = 'value'", encoding="utf-8")
        with pytest.raises(LoomIOError, match="extension"):
            load_spec(p)

    def test_yaml_not_a_dict(self, tmp_path: Path) -> None:
        p = tmp_path / "list.yaml"
        p.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(LoomIOError, match="dict"):
            load_spec(p)

    def test_load_and_validate_alias(self, minimal_spec_dict: dict[str, Any]) -> None:
        """load_and_validate should be identical to load_spec."""
        spec1 = load_spec(minimal_spec_dict)
        spec2 = load_and_validate(minimal_spec_dict)
        assert spec1.avatar_id == spec2.avatar_id


class TestLoomValidationError:
    def test_str_representation(self) -> None:
        from seidr_smidja.loom.exceptions import ValidationFailure

        failures = [
            ValidationFailure(field_path="avatar_id", reason="must be slug", received_value="bad id")
        ]
        err = LoomValidationError("Oops", failures=failures)
        assert "Oops" in str(err)

    def test_empty_failures(self) -> None:
        err = LoomValidationError("Oops", failures=[])
        assert err.failures == []
