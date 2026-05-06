"""Tests for seidr_smidja.brunhand.daemon.capabilities — probe_capabilities."""
from __future__ import annotations

from unittest.mock import patch

import pytest


class TestProbeCapabilities:
    def test_returns_manifest(self) -> None:
        from seidr_smidja.brunhand.daemon.capabilities import probe_capabilities
        from seidr_smidja.brunhand.models import CapabilitiesManifest
        manifest = probe_capabilities()
        assert isinstance(manifest, CapabilitiesManifest)

    def test_manifest_has_daemon_version(self) -> None:
        from seidr_smidja.brunhand.daemon.capabilities import probe_capabilities
        manifest = probe_capabilities()
        assert manifest.daemon_version != ""

    def test_manifest_has_os_name(self) -> None:
        from seidr_smidja.brunhand.daemon.capabilities import probe_capabilities
        import platform
        manifest = probe_capabilities()
        assert manifest.os_name != ""

    def test_screenshot_listed(self) -> None:
        from seidr_smidja.brunhand.daemon.capabilities import probe_capabilities
        manifest = probe_capabilities()
        assert "screenshot" in manifest.primitives

    def test_click_listed(self) -> None:
        from seidr_smidja.brunhand.daemon.capabilities import probe_capabilities
        manifest = probe_capabilities()
        assert "click" in manifest.primitives

    def test_vroid_primitives_listed(self) -> None:
        from seidr_smidja.brunhand.daemon.capabilities import probe_capabilities
        manifest = probe_capabilities()
        assert "vroid_export_vrm" in manifest.primitives
        assert "vroid_save_project" in manifest.primitives
        assert "vroid_open_project" in manifest.primitives

    def test_probed_at_is_set(self) -> None:
        from seidr_smidja.brunhand.daemon.capabilities import probe_capabilities
        manifest = probe_capabilities()
        assert manifest.probed_at != ""


class TestIsPrimitiveAvailable:
    def test_returns_bool(self) -> None:
        from seidr_smidja.brunhand.daemon.capabilities import is_primitive_available
        result = is_primitive_available("screenshot")
        assert isinstance(result, bool)

    def test_unknown_primitive_returns_false(self) -> None:
        from seidr_smidja.brunhand.daemon.capabilities import is_primitive_available
        result = is_primitive_available("nonexistent_primitive_xyz")
        assert result is False


class TestGetCachedManifest:
    def test_returns_same_instance(self) -> None:
        from seidr_smidja.brunhand.daemon.capabilities import get_cached_manifest
        m1 = get_cached_manifest()
        m2 = get_cached_manifest()
        assert m1 is m2

    def test_manifest_type(self) -> None:
        from seidr_smidja.brunhand.daemon.capabilities import get_cached_manifest
        from seidr_smidja.brunhand.models import CapabilitiesManifest
        manifest = get_cached_manifest()
        assert isinstance(manifest, CapabilitiesManifest)
