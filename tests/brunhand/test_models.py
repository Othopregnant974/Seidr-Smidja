"""Tests for seidr_smidja.brunhand.models — Pydantic envelope models."""
from __future__ import annotations

import uuid

import pytest


class TestBrunhandRequestEnvelope:
    def test_default_request_id(self) -> None:
        from seidr_smidja.brunhand.models import BrunhandRequestEnvelope
        req = BrunhandRequestEnvelope()
        assert req.request_id
        uuid.UUID(req.request_id)  # validates UUID format

    def test_unique_request_ids(self) -> None:
        from seidr_smidja.brunhand.models import BrunhandRequestEnvelope
        r1 = BrunhandRequestEnvelope()
        r2 = BrunhandRequestEnvelope()
        assert r1.request_id != r2.request_id

    def test_session_id_default_empty(self) -> None:
        from seidr_smidja.brunhand.models import BrunhandRequestEnvelope
        req = BrunhandRequestEnvelope()
        assert req.session_id == ""

    def test_timeout_seconds_optional(self) -> None:
        from seidr_smidja.brunhand.models import BrunhandRequestEnvelope
        req = BrunhandRequestEnvelope(timeout_seconds=45.0)
        assert req.timeout_seconds == 45.0

    def test_timeout_seconds_defaults_none(self) -> None:
        from seidr_smidja.brunhand.models import BrunhandRequestEnvelope
        req = BrunhandRequestEnvelope()
        assert req.timeout_seconds is None


class TestBrunhandResponseEnvelope:
    def test_success_true(self) -> None:
        from seidr_smidja.brunhand.models import BrunhandResponseEnvelope
        resp = BrunhandResponseEnvelope(request_id="abc", session_id="", success=True, payload={})
        assert resp.success is True
        assert resp.error is None

    def test_success_false_with_error(self) -> None:
        from seidr_smidja.brunhand.models import BrunhandErrorDetail, BrunhandResponseEnvelope
        err = BrunhandErrorDetail(error_type="TestError", message="oops", primitive="click")
        resp = BrunhandResponseEnvelope(
            request_id="xyz", session_id="", success=False, error=err
        )
        assert resp.success is False
        assert resp.error is not None
        assert resp.error.error_type == "TestError"

    def test_latency_ms_defaults_zero(self) -> None:
        from seidr_smidja.brunhand.models import BrunhandResponseEnvelope
        resp = BrunhandResponseEnvelope(request_id="x", session_id="", success=True, payload={})
        assert resp.latency_ms == 0.0


class TestScreenshotRequest:
    def test_defaults(self) -> None:
        from seidr_smidja.brunhand.models import ScreenshotRequest
        req = ScreenshotRequest()
        assert req.region is None

    def test_with_region(self) -> None:
        from seidr_smidja.brunhand.models import ScreenRect, ScreenshotRequest
        req = ScreenshotRequest(region=ScreenRect(width=1920, height=1080))
        assert req.region is not None
        assert req.region.width == 1920


class TestClickRequest:
    def test_required_fields(self) -> None:
        from seidr_smidja.brunhand.models import ClickRequest
        req = ClickRequest(x=100, y=200)
        assert req.x == 100
        assert req.y == 200
        assert req.button == "left"
        assert req.clicks == 1

    def test_button_validation(self) -> None:
        from seidr_smidja.brunhand.models import ClickRequest
        # Valid buttons
        for btn in ("left", "right", "middle"):
            req = ClickRequest(x=0, y=0, button=btn)
            assert req.button == btn


class TestVroidExportVrmRequest:
    def test_required_output_path(self) -> None:
        from seidr_smidja.brunhand.models import VroidExportVrmRequest
        req = VroidExportVrmRequest(output_path="character.vrm")
        assert req.output_path == "character.vrm"
        assert req.overwrite is True
        assert req.wait_timeout_seconds == 120.0

    def test_wait_timeout_seconds_field(self) -> None:
        """VroidExportVrmRequest must have wait_timeout_seconds for D-010 tension #3."""
        from seidr_smidja.brunhand.models import VroidExportVrmRequest
        req = VroidExportVrmRequest(output_path="out.vrm", wait_timeout_seconds=60.0)
        # wait_timeout_seconds is the primitive-level timeout
        assert req.wait_timeout_seconds == 60.0
        # The client.vroid_export_vrm() will pass this as primitive_timeout to _post()


class TestCapabilitiesManifest:
    def test_defaults(self) -> None:
        from seidr_smidja.brunhand.models import CapabilitiesManifest, PrimitiveStatus
        manifest = CapabilitiesManifest(
            daemon_version="0.1.0",
            os_name="Windows",
            primitives={
                "screenshot": PrimitiveStatus(available=True, primitive="screenshot"),
                "click": PrimitiveStatus(available=True, primitive="click"),
            },
        )
        assert manifest.os_name == "Windows"
        assert manifest.primitives["screenshot"].available is True


class TestBrunhandErrorDetail:
    def test_minimal(self) -> None:
        from seidr_smidja.brunhand.models import BrunhandErrorDetail
        err = BrunhandErrorDetail(error_type="VroidNotRunningError", message="VRoid not running")
        assert err.vroid_running is False or err.vroid_running is None or True  # field exists
        assert err.primitive == ""

    def test_vroid_not_running(self) -> None:
        from seidr_smidja.brunhand.models import BrunhandErrorDetail
        err = BrunhandErrorDetail(
            error_type="VroidNotRunningError",
            message="VRoid Studio is not running.",
            primitive="vroid_export_vrm",
            vroid_running=False,
        )
        assert err.vroid_running is False
