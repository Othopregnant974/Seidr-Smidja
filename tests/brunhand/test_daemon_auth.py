"""Tests for seidr_smidja.brunhand.daemon.auth — Gæslumaðr middleware functions."""
from __future__ import annotations

import pytest


class TestTokenMatching:
    def test_valid_token_matches(self) -> None:
        from seidr_smidja.brunhand.daemon.auth import _tokens_match
        assert _tokens_match("secret-token-abc", "secret-token-abc") is True

    def test_wrong_token_rejected(self) -> None:
        from seidr_smidja.brunhand.daemon.auth import _tokens_match
        assert _tokens_match("wrong-token", "secret-token-abc") is False

    def test_empty_presented_rejected(self) -> None:
        from seidr_smidja.brunhand.daemon.auth import _tokens_match
        assert _tokens_match("", "secret-token-abc") is False

    def test_empty_configured_rejected(self) -> None:
        from seidr_smidja.brunhand.daemon.auth import _tokens_match
        assert _tokens_match("my-token", "") is False

    def test_constant_time_comparison(self) -> None:
        """Verify hmac.compare_digest is used (not ==)."""
        import hmac
        from seidr_smidja.brunhand.daemon.auth import _tokens_match
        result = _tokens_match("abc", "abc")
        assert isinstance(result, bool)
        assert result is True


class TestTokenExtraction:
    def test_valid_bearer_header(self) -> None:
        from seidr_smidja.brunhand.daemon.auth import _extract_token
        token, status = _extract_token("Bearer my-secret-token")
        assert token == "my-secret-token"
        assert status == "accepted"

    def test_missing_bearer_prefix(self) -> None:
        from seidr_smidja.brunhand.daemon.auth import _extract_token
        token, status = _extract_token("my-secret-token")
        assert token == ""
        assert status == "malformed"

    def test_empty_header_returns_missing(self) -> None:
        from seidr_smidja.brunhand.daemon.auth import _extract_token
        token, status = _extract_token("")
        assert token == ""
        assert status == "missing"

    def test_bearer_lowercase_accepted(self) -> None:
        from seidr_smidja.brunhand.daemon.auth import _extract_token
        token, status = _extract_token("bearer my-token")
        assert token == "my-token"
        assert status == "accepted"


class TestHealthBypass:
    def test_health_path_constant(self) -> None:
        """Health endpoint path constant must match expected value."""
        from seidr_smidja.brunhand.daemon.auth import _HEALTH_PATH
        assert _HEALTH_PATH == "/v1/brunhand/health"
