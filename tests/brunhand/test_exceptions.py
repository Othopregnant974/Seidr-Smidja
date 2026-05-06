"""Tests for seidr_smidja.brunhand.exceptions — exception hierarchy."""
from __future__ import annotations


class TestBrunhandError:
    def test_base_attributes(self) -> None:
        from seidr_smidja.brunhand.exceptions import BrunhandError
        exc = BrunhandError("test message", host="myhost", primitive="click")
        assert exc.message == "test message"
        assert exc.host == "myhost"
        assert exc.primitive == "click"
        assert exc.request_id == ""
        assert exc.session_id == ""

    def test_repr_does_not_include_token(self) -> None:
        from seidr_smidja.brunhand.exceptions import BrunhandError
        exc = BrunhandError("bad token rejected")
        r = repr(exc)
        # Should NOT include any token-like string
        assert "Bearer" not in r
        assert "token" not in r.lower() or "request_id" in r

    def test_is_exception(self) -> None:
        from seidr_smidja.brunhand.exceptions import BrunhandError
        exc = BrunhandError("test")
        assert isinstance(exc, Exception)


class TestBrunhandAuthError:
    def test_is_brunhand_error(self) -> None:
        from seidr_smidja.brunhand.exceptions import BrunhandAuthError, BrunhandError
        exc = BrunhandAuthError("token rejected", host="h", primitive="p")
        assert isinstance(exc, BrunhandError)

    def test_attributes(self) -> None:
        from seidr_smidja.brunhand.exceptions import BrunhandAuthError
        exc = BrunhandAuthError("401 Unauthorized", host="vroid-win")
        assert exc.host == "vroid-win"


class TestBrunhandConnectionError:
    def test_cause_attribute(self) -> None:
        from seidr_smidja.brunhand.exceptions import BrunhandConnectionError
        exc = BrunhandConnectionError("connect failed", cause="tls", host="h")
        assert exc.cause == "tls"
        assert "tls" in repr(exc)

    def test_default_cause(self) -> None:
        from seidr_smidja.brunhand.exceptions import BrunhandConnectionError
        exc = BrunhandConnectionError("connect failed")
        assert exc.cause == "unknown"


class TestBrunhandPrimitiveError:
    def test_vroid_running_attribute(self) -> None:
        from seidr_smidja.brunhand.exceptions import BrunhandPrimitiveError
        exc = BrunhandPrimitiveError("failed", vroid_running=False)
        assert exc.vroid_running is False

    def test_defaults(self) -> None:
        from seidr_smidja.brunhand.exceptions import BrunhandPrimitiveError
        exc = BrunhandPrimitiveError("failed")
        assert exc.vroid_running is True
        assert exc.screen_accessible is True
        assert exc.permission_denied is False
        assert exc.stack_summary is None


class TestVroidNotRunningError:
    def test_is_primitive_error(self) -> None:
        from seidr_smidja.brunhand.exceptions import BrunhandPrimitiveError, VroidNotRunningError
        exc = VroidNotRunningError()
        assert isinstance(exc, BrunhandPrimitiveError)

    def test_vroid_running_false(self) -> None:
        from seidr_smidja.brunhand.exceptions import VroidNotRunningError
        exc = VroidNotRunningError()
        assert exc.vroid_running is False

    def test_custom_message(self) -> None:
        from seidr_smidja.brunhand.exceptions import VroidNotRunningError
        exc = VroidNotRunningError("VRoid Studio not found", host="vroid-host")
        assert "VRoid Studio" in str(exc)
        assert exc.host == "vroid-host"


class TestBrunhandCapabilityError:
    def test_primitive_name_attribute(self) -> None:
        from seidr_smidja.brunhand.exceptions import BrunhandCapabilityError
        exc = BrunhandCapabilityError(
            "not available", primitive_name="click",
            platform="linux", available_primitives=["screenshot"],
        )
        assert exc.primitive_name == "click"
        assert exc.platform == "linux"
        assert "screenshot" in exc.available_primitives


class TestBrunhandProtocolError:
    def test_status_code(self) -> None:
        from seidr_smidja.brunhand.exceptions import BrunhandProtocolError
        exc = BrunhandProtocolError("bad response", raw_status_code=500, raw_body_preview="error text")
        assert exc.raw_status_code == 500
        assert exc.raw_body_preview == "error text"


class TestBrunhandTimeoutError:
    def test_is_brunhand_error(self) -> None:
        from seidr_smidja.brunhand.exceptions import BrunhandError, BrunhandTimeoutError
        exc = BrunhandTimeoutError("timed out", host="h")
        assert isinstance(exc, BrunhandError)
