"""Tests for seidr_smidja.loom.schema — AvatarSpec Pydantic v2 model."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from seidr_smidja.loom.schema import (
    AvatarSpec,
    BodySpec,
    ExpressionTarget,
    RGBColor,
)

# ─── RGBColor ─────────────────────────────────────────────────────────────────


class TestRGBColor:
    def test_valid_construction(self) -> None:
        c = RGBColor(r=0.5, g=0.5, b=0.5)
        assert c.r == 0.5
        assert c.g == 0.5
        assert c.b == 0.5

    def test_boundary_values(self) -> None:
        c = RGBColor(r=0.0, g=0.0, b=0.0)
        assert c.r == 0.0
        c2 = RGBColor(r=1.0, g=1.0, b=1.0)
        assert c2.r == 1.0

    def test_from_list(self) -> None:
        c = RGBColor.from_list([0.1, 0.2, 0.3])
        assert c.r == pytest.approx(0.1)
        assert c.g == pytest.approx(0.2)
        assert c.b == pytest.approx(0.3)

    def test_to_list(self) -> None:
        c = RGBColor(r=0.4, g=0.5, b=0.6)
        result = c.to_list()
        assert result == pytest.approx([0.4, 0.5, 0.6])

    def test_from_list_wrong_length(self) -> None:
        with pytest.raises(ValueError, match="3 channels"):
            RGBColor.from_list([0.1, 0.2])

    def test_out_of_range_low(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RGBColor(r=-0.1, g=0.0, b=0.0)

    def test_out_of_range_high(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RGBColor(r=1.1, g=0.0, b=0.0)

    def test_frozen(self) -> None:
        c = RGBColor(r=0.5, g=0.5, b=0.5)
        with pytest.raises(Exception):
            c.r = 0.9  # type: ignore[misc]


# ─── BodySpec ─────────────────────────────────────────────────────────────────


class TestBodySpec:
    def test_defaults(self) -> None:
        b = BodySpec()
        assert b.height_scale == 1.0
        assert b.head_scale == 1.0
        assert b.upper_body_scale == 1.0
        assert b.lower_body_scale == 1.0
        assert b.arm_length_scale == 1.0
        assert b.leg_length_scale == 1.0

    def test_custom_values(self) -> None:
        b = BodySpec(height_scale=1.05, leg_length_scale=0.9)
        assert b.height_scale == pytest.approx(1.05)
        assert b.leg_length_scale == pytest.approx(0.9)

    def test_out_of_range(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BodySpec(height_scale=3.0)  # max is 2.0

    def test_out_of_range_low(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BodySpec(height_scale=0.1)  # min is 0.5


# ─── ExpressionTarget ─────────────────────────────────────────────────────────


class TestExpressionTarget:
    def test_name_normalized_to_lowercase(self) -> None:
        et = ExpressionTarget(name="Joy", weight=0.5)
        assert et.name == "joy"

    def test_name_stripped(self) -> None:
        et = ExpressionTarget(name="  blink  ", weight=1.0)
        assert et.name == "blink"

    def test_empty_name_rejected(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ExpressionTarget(name="   ", weight=0.5)

    def test_weight_boundary(self) -> None:
        t0 = ExpressionTarget(name="joy", weight=0.0)
        t1 = ExpressionTarget(name="joy", weight=1.0)
        assert t0.weight == 0.0
        assert t1.weight == 1.0

    def test_weight_out_of_range(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ExpressionTarget(name="joy", weight=1.5)


# ─── AvatarSpec ───────────────────────────────────────────────────────────────


class TestAvatarSpec:
    def test_minimal_valid(self, minimal_spec_dict: dict[str, Any]) -> None:
        spec = AvatarSpec.from_dict(minimal_spec_dict)
        assert spec.avatar_id == "test_avatar_v1"
        assert spec.display_name == "Test Avatar"
        assert spec.base_asset_id == "vroid/sample_a"
        assert spec.spec_version == "1.0"

    def test_full_valid(self, full_spec_dict: dict[str, Any]) -> None:
        spec = AvatarSpec.from_dict(full_spec_dict)
        assert spec.avatar_id == "full_test_avatar"
        assert len(spec.expressions.targets) == 2
        assert len(spec.outfit.layers) == 1
        assert spec.metadata.license == "CC-BY-4.0"

    def test_unsupported_spec_version(self, minimal_spec_dict: dict[str, Any]) -> None:
        from pydantic import ValidationError

        data = dict(minimal_spec_dict)
        data["spec_version"] = "99.0"
        with pytest.raises(ValidationError, match="spec_version"):
            AvatarSpec.from_dict(data)

    def test_invalid_avatar_id_spaces(self, minimal_spec_dict: dict[str, Any]) -> None:
        from pydantic import ValidationError

        data = dict(minimal_spec_dict)
        data["avatar_id"] = "my avatar with spaces"
        with pytest.raises(ValidationError, match="avatar_id"):
            AvatarSpec.from_dict(data)

    def test_avatar_id_allows_hyphens_and_underscores(
        self, minimal_spec_dict: dict[str, Any]
    ) -> None:
        data = dict(minimal_spec_dict)
        data["avatar_id"] = "my-avatar_v1"
        spec = AvatarSpec.from_dict(data)
        assert spec.avatar_id == "my-avatar_v1"

    def test_missing_required_field(self, minimal_spec_dict: dict[str, Any]) -> None:
        from pydantic import ValidationError

        data = dict(minimal_spec_dict)
        del data["avatar_id"]
        with pytest.raises(ValidationError):
            AvatarSpec.from_dict(data)

    def test_missing_metadata(self, minimal_spec_dict: dict[str, Any]) -> None:
        from pydantic import ValidationError

        data = dict(minimal_spec_dict)
        del data["metadata"]
        with pytest.raises(ValidationError):
            AvatarSpec.from_dict(data)

    def test_extensions_hatch_round_trips(self, minimal_spec_dict: dict[str, Any]) -> None:
        data = dict(minimal_spec_dict)
        data["extensions"] = {"nse": {"bondmaid_id": "astrid"}, "custom": {"x": 42}}
        spec = AvatarSpec.from_dict(data)
        assert spec.extensions["nse"]["bondmaid_id"] == "astrid"
        assert spec.extensions["custom"]["x"] == 42

    def test_frozen(self, minimal_spec_dict: dict[str, Any]) -> None:
        spec = AvatarSpec.from_dict(minimal_spec_dict)
        with pytest.raises(Exception):
            spec.avatar_id = "new_id"  # type: ignore[misc]

    def test_defaults_are_applied(self, minimal_spec_dict: dict[str, Any]) -> None:
        """Minimal spec gets all sub-model defaults."""
        spec = AvatarSpec.from_dict(minimal_spec_dict)
        assert spec.body.height_scale == 1.0
        assert spec.face.eye_scale == 1.0
        assert spec.hair.physics_enabled is True
        assert spec.outfit.layers == []
        assert spec.expressions.targets == []

    def test_to_dict_round_trip(self, minimal_spec_dict: dict[str, Any]) -> None:
        spec = AvatarSpec.from_dict(minimal_spec_dict)
        d = spec.to_dict()
        assert d["avatar_id"] == spec.avatar_id
        # Round-trip
        spec2 = AvatarSpec.from_dict(d)
        assert spec2.avatar_id == spec.avatar_id
        assert spec2.metadata.author == spec.metadata.author

    def test_to_json(self, minimal_spec_dict: dict[str, Any]) -> None:
        spec = AvatarSpec.from_dict(minimal_spec_dict)
        j = spec.to_json()
        parsed = json.loads(j)
        assert parsed["avatar_id"] == spec.avatar_id

    def test_to_yaml(self, minimal_spec_dict: dict[str, Any]) -> None:
        spec = AvatarSpec.from_dict(minimal_spec_dict)
        y = spec.to_yaml()
        parsed = yaml.safe_load(y)
        assert parsed["avatar_id"] == spec.avatar_id

    def test_to_file_yaml(self, minimal_spec_dict: dict[str, Any], tmp_path: Path) -> None:
        spec = AvatarSpec.from_dict(minimal_spec_dict)
        out = tmp_path / "out.yaml"
        spec.to_file(out)
        assert out.exists()
        loaded = yaml.safe_load(out.read_text())
        assert loaded["avatar_id"] == spec.avatar_id

    def test_to_file_json(self, minimal_spec_dict: dict[str, Any], tmp_path: Path) -> None:
        spec = AvatarSpec.from_dict(minimal_spec_dict)
        out = tmp_path / "out.json"
        spec.to_file(out)
        assert out.exists()
        loaded = json.loads(out.read_text())
        assert loaded["avatar_id"] == spec.avatar_id

    def test_to_file_unsupported_extension(
        self, minimal_spec_dict: dict[str, Any], tmp_path: Path
    ) -> None:
        from seidr_smidja.loom.exceptions import LoomIOError

        spec = AvatarSpec.from_dict(minimal_spec_dict)
        with pytest.raises(LoomIOError, match="extension"):
            spec.to_file(tmp_path / "out.txt")
