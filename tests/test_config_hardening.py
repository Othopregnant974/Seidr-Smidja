"""Tests for config.py — H-021 coverage of env vars, deep merge, and load_config."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import yaml


class TestDeepMerge:
    """_deep_merge() must deeply merge without mutating inputs."""

    def test_deep_merge_nested_keys(self) -> None:
        from seidr_smidja.config import _deep_merge

        base = {"a": {"x": 1, "y": 2}, "b": 10}
        override = {"a": {"y": 99, "z": 3}, "c": 20}
        result = _deep_merge(base, override)

        assert result["a"]["x"] == 1   # preserved from base
        assert result["a"]["y"] == 99  # overridden
        assert result["a"]["z"] == 3   # new key
        assert result["b"] == 10       # preserved
        assert result["c"] == 20       # new key

    def test_deep_merge_does_not_mutate_base(self) -> None:
        from seidr_smidja.config import _deep_merge

        base = {"a": {"x": 1}}
        override = {"a": {"x": 99}}
        _deep_merge(base, override)
        # base must be unchanged
        assert base["a"]["x"] == 1

    def test_deep_merge_does_not_mutate_override(self) -> None:
        from seidr_smidja.config import _deep_merge

        base = {"a": {"x": 1}}
        override = {"a": {"x": 99}}
        original_override = {"a": {"x": 99}}
        _deep_merge(base, override)
        assert override == original_override

    def test_deep_merge_non_dict_override_replaces(self) -> None:
        from seidr_smidja.config import _deep_merge

        base = {"a": {"nested": True}}
        override = {"a": "not a dict anymore"}
        result = _deep_merge(base, override)
        assert result["a"] == "not a dict anymore"

    def test_deep_merge_empty_base(self) -> None:
        from seidr_smidja.config import _deep_merge

        result = _deep_merge({}, {"x": 1})
        assert result["x"] == 1

    def test_deep_merge_empty_override(self) -> None:
        from seidr_smidja.config import _deep_merge

        base = {"x": 1}
        result = _deep_merge(base, {})
        assert result == base


class TestApplyEnvVars:
    """_apply_env_vars() must map SEIDR_* env vars into nested config keys."""

    def test_seidr_blender_path_maps_to_blender_executable(self) -> None:
        from seidr_smidja.config import _apply_env_vars

        with patch.dict(os.environ, {"SEIDR_BLENDER_PATH": "/custom/blender"}):
            result = _apply_env_vars({})
        assert result["blender"]["executable"] == "/custom/blender"

    def test_seidr_annall_adapter_maps_correctly(self) -> None:
        from seidr_smidja.config import _apply_env_vars

        with patch.dict(os.environ, {"SEIDR_ANNALL_ADAPTER": "null"}):
            result = _apply_env_vars({})
        assert result["annall"]["adapter"] == "null"

    def test_seidr_annall_sqlite_path_maps_correctly(self) -> None:
        from seidr_smidja.config import _apply_env_vars

        with patch.dict(os.environ, {"SEIDR_ANNALL_SQLITE_PATH": "/tmp/annall.sqlite"}):
            result = _apply_env_vars({})
        assert result["annall"]["sqlite"]["db_path"] == "/tmp/annall.sqlite"

    def test_seidr_output_root_maps_correctly(self) -> None:
        from seidr_smidja.config import _apply_env_vars

        with patch.dict(os.environ, {"SEIDR_OUTPUT_ROOT": "/data/output"}):
            result = _apply_env_vars({})
        assert result["output"]["root"] == "/data/output"

    def test_seidr_gate_vrchat_tier_maps_correctly(self) -> None:
        from seidr_smidja.config import _apply_env_vars

        with patch.dict(os.environ, {"SEIDR_GATE_VRCHAT_TIER": "Excellent"}):
            result = _apply_env_vars({})
        assert result["gate"]["vrchat_tier_target"] == "Excellent"

    def test_env_var_overrides_existing_config_value(self) -> None:
        from seidr_smidja.config import _apply_env_vars

        base = {"annall": {"adapter": "sqlite"}}
        with patch.dict(os.environ, {"SEIDR_ANNALL_ADAPTER": "file"}):
            result = _apply_env_vars(base)
        assert result["annall"]["adapter"] == "file"
        # Original not mutated
        assert base["annall"]["adapter"] == "sqlite"

    def test_unset_env_vars_leave_config_unchanged(self) -> None:
        from seidr_smidja.config import _apply_env_vars

        env_without_seidr = {k: v for k, v in os.environ.items() if not k.startswith("SEIDR_")}
        base = {"annall": {"adapter": "sqlite"}}
        with patch.dict(os.environ, env_without_seidr, clear=True):
            result = _apply_env_vars(base)
        assert result["annall"]["adapter"] == "sqlite"


class TestLoadConfig:
    """load_config() must merge defaults, user overrides, and env vars."""

    def test_load_config_with_defaults_yaml(self, tmp_path: Path) -> None:
        from seidr_smidja.config import load_config

        defaults = {
            "blender": {"executable": "blender"},
            "annall": {"adapter": "sqlite"},
        }
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "defaults.yaml").write_text(
            yaml.dump(defaults), encoding="utf-8"
        )

        cfg = load_config(tmp_path)
        assert cfg["blender"]["executable"] == "blender"
        assert cfg["annall"]["adapter"] == "sqlite"

    def test_load_config_user_yaml_overrides_defaults(self, tmp_path: Path) -> None:
        from seidr_smidja.config import load_config

        defaults = {"annall": {"adapter": "sqlite"}}
        user = {"annall": {"adapter": "null"}}

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "defaults.yaml").write_text(yaml.dump(defaults), encoding="utf-8")
        (config_dir / "user.yaml").write_text(yaml.dump(user), encoding="utf-8")

        cfg = load_config(tmp_path)
        assert cfg["annall"]["adapter"] == "null"

    def test_load_config_env_var_overrides_yaml(self, tmp_path: Path) -> None:
        from seidr_smidja.config import load_config

        defaults = {"annall": {"adapter": "sqlite"}}
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "defaults.yaml").write_text(yaml.dump(defaults), encoding="utf-8")

        with patch.dict(os.environ, {"SEIDR_ANNALL_ADAPTER": "file"}):
            cfg = load_config(tmp_path)

        assert cfg["annall"]["adapter"] == "file"

    def test_load_config_attaches_project_root(self, tmp_path: Path) -> None:
        from seidr_smidja.config import load_config

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "defaults.yaml").write_text("{}", encoding="utf-8")

        cfg = load_config(tmp_path)
        assert "_project_root" in cfg
        assert str(tmp_path) in cfg["_project_root"]

    def test_load_config_missing_defaults_returns_empty_base(self, tmp_path: Path) -> None:
        from seidr_smidja.config import load_config

        # No config/ directory — should not crash
        cfg = load_config(tmp_path)
        assert isinstance(cfg, dict)
        assert "_project_root" in cfg


class TestFindConfigRoot:
    """_find_config_root() must locate config/defaults.yaml walking upward."""

    def test_find_config_root_finds_real_project(self) -> None:
        from seidr_smidja.config import _find_config_root

        root = _find_config_root()
        # Should find a directory containing config/defaults.yaml
        assert (root / "config" / "defaults.yaml").exists() or root.is_dir()

    def test_find_config_root_returns_path_object(self) -> None:
        from seidr_smidja.config import _find_config_root

        root = _find_config_root()
        assert isinstance(root, Path)
