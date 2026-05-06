"""Tests for the Straumur REST bridge — H-018 coverage + H-004/H-005 security fixes."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

# Skip all tests if FastAPI is not installed
pytest.importorskip("fastapi", reason="FastAPI not installed — Straumur tests skipped")
pytest.importorskip("httpx", reason="httpx not installed — TestClient needs it")


@pytest.fixture
def test_client(tmp_path: Path):
    """Create a FastAPI TestClient backed by a null Annáll and a temp config."""
    from fastapi.testclient import TestClient

    from seidr_smidja.bridges.straumur.api import create_app

    cfg = {
        "annall": {"adapter": "null"},
        "output": {"root": str(tmp_path / "output")},
        "hoard": {
            "catalog_path": str(tmp_path / "data/hoard/catalog.yaml"),
            "bases_dir": str(tmp_path / "data/hoard/bases"),
        },
        "_project_root": str(tmp_path),
    }
    app = create_app(cfg)
    return TestClient(app)


@pytest.fixture
def test_client_with_hoard(tmp_path: Path, sample_vrm_fixture: Path):
    """TestClient with a real minimal Hoard for asset listing tests."""
    import shutil

    from fastapi.testclient import TestClient

    from seidr_smidja.bridges.straumur.api import create_app

    bases_dir = tmp_path / "data/hoard/bases"
    bases_dir.mkdir(parents=True)
    shutil.copy(sample_vrm_fixture, bases_dir / "SampleA.vrm")

    catalog_path = tmp_path / "data/hoard/catalog.yaml"
    catalog_data = {
        "format_version": "1",
        "bases": [
            {
                "asset_id": "vroid/sample_a",
                "display_name": "Sample A",
                "filename": "SampleA.vrm",
                "vrm_version": "0.0",
                "tags": ["sample"],
                "cached": True,
            }
        ],
    }
    catalog_path.write_text(yaml.dump(catalog_data), encoding="utf-8")

    cfg = {
        "annall": {"adapter": "null"},
        "output": {"root": str(tmp_path / "output")},
        "hoard": {
            "catalog_path": str(catalog_path),
            "bases_dir": str(bases_dir),
        },
        "_project_root": str(tmp_path),
    }
    app = create_app(cfg)
    return TestClient(app)


# ─── GET /v1/health ───────────────────────────────────────────────────────────


class TestHealthEndpoint:
    def test_health_returns_200(self, test_client) -> None:
        resp = test_client.get("/v1/health")
        assert resp.status_code == 200

    def test_health_body_has_status_ok(self, test_client) -> None:
        resp = test_client.get("/v1/health")
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_body_has_version(self, test_client) -> None:
        resp = test_client.get("/v1/health")
        data = resp.json()
        assert "version" in data


# ─── GET /v1/assets ───────────────────────────────────────────────────────────


class TestListAssetsEndpoint:
    def test_list_assets_returns_200(self, test_client_with_hoard) -> None:
        resp = test_client_with_hoard.get("/v1/assets")
        assert resp.status_code == 200

    def test_list_assets_returns_list(self, test_client_with_hoard) -> None:
        resp = test_client_with_hoard.get("/v1/assets")
        data = resp.json()
        assert isinstance(data, list)

    def test_list_assets_structure(self, test_client_with_hoard) -> None:
        resp = test_client_with_hoard.get("/v1/assets")
        data = resp.json()
        assert len(data) >= 1
        item = data[0]
        assert "asset_id" in item
        assert "display_name" in item
        assert "asset_type" in item
        assert "cached" in item

    def test_list_assets_type_filter(self, test_client_with_hoard) -> None:
        resp = test_client_with_hoard.get("/v1/assets?asset_type=vrm_base")
        assert resp.status_code == 200
        data = resp.json()
        for item in data:
            assert item["asset_type"] == "vrm_base"

    def test_list_assets_tag_filter(self, test_client_with_hoard) -> None:
        resp = test_client_with_hoard.get("/v1/assets?tag=sample")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1


# ─── POST /v1/avatars ─────────────────────────────────────────────────────────


class TestBuildAvatarEndpoint:
    def test_build_avatar_missing_spec_returns_error(self, test_client) -> None:
        """Posting an empty body should return a validation error."""
        resp = test_client.post("/v1/avatars", json={})
        # FastAPI pydantic validation returns 422 for missing required field 'spec'
        assert resp.status_code == 422

    def test_build_avatar_with_spec_calls_dispatch(self, test_client, tmp_path: Path) -> None:
        """POST /v1/avatars with a valid dict spec calls dispatch and returns JSON."""
        import importlib

        from seidr_smidja.bridges.core.dispatch import BuildResponse
        dispatch_module = importlib.import_module("seidr_smidja.bridges.core.dispatch")

        mock_response = BuildResponse(
            request_id="req-rest-test",
            success=True,
            elapsed_seconds=0.1,
        )

        with patch.object(dispatch_module, "dispatch", return_value=mock_response):
            resp = test_client.post(
                "/v1/avatars",
                json={
                    "spec": {
                        "spec_version": "1.0",
                        "avatar_id": "rest_test",
                        "display_name": "REST Test",
                        "base_asset_id": "vroid/sample_a",
                        "metadata": {"author": "Test", "license": "CC0-1.0"},
                    }
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert data["success"] is True

    def test_build_avatar_failure_response_returns_422(
        self, test_client, tmp_path: Path
    ) -> None:
        """When dispatch returns success=False, HTTP status should be 422."""
        import importlib

        from seidr_smidja.bridges.core.dispatch import BuildError, BuildResponse
        dispatch_module = importlib.import_module("seidr_smidja.bridges.core.dispatch")

        mock_response = BuildResponse(
            request_id="req-fail",
            success=False,
            errors=[BuildError(stage="loom", error_type="LoomError", message="bad spec")],
            elapsed_seconds=0.1,
        )

        with patch.object(dispatch_module, "dispatch", return_value=mock_response):
            resp = test_client.post(
                "/v1/avatars",
                json={"spec": {"base_asset_id": "test"}},
            )

        assert resp.status_code == 422


# ─── POST /v1/inspect ─────────────────────────────────────────────────────────


class TestInspectEndpoint:
    """H-004: inspect endpoint must reject paths outside allowed roots."""

    def test_inspect_non_vrm_extension_rejected(self, test_client) -> None:
        """vrm_path not ending in .vrm must return 400."""
        resp = test_client.post(
            "/v1/inspect",
            json={"vrm_path": "/etc/passwd"},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "vrm_path" in str(data).lower() or "vrm" in str(data).lower()

    def test_inspect_path_outside_allowed_roots_rejected(
        self, test_client, tmp_path: Path
    ) -> None:
        """vrm_path that escapes allowed roots must return 400."""
        resp = test_client.post(
            "/v1/inspect",
            json={"vrm_path": "/tmp/some_attacker_file.vrm"},
        )
        assert resp.status_code == 400

    def test_inspect_with_real_vrm_in_allowed_dir(
        self, test_client_with_hoard, tmp_path: Path, sample_vrm_fixture: Path
    ) -> None:
        """A .vrm in the hoard bases_dir should pass path validation and be inspected."""
        bases_dir = tmp_path / "data/hoard/bases"
        vrm_path = bases_dir / "SampleA.vrm"
        assert vrm_path.exists(), "sample VRM should exist in test hoard"

        resp = test_client_with_hoard.post(
            "/v1/inspect",
            json={"vrm_path": str(vrm_path)},
        )
        # Should either pass gate check (200) or fail gate check but still parse (200/500)
        # The key thing is it must NOT be 400 (path rejected)
        assert resp.status_code != 400

    def test_inspect_path_traversal_rejected(self, test_client) -> None:
        """Path traversal via ../../ must be rejected."""
        resp = test_client.post(
            "/v1/inspect",
            json={"vrm_path": "../../etc/sensitive.vrm"},
        )
        assert resp.status_code == 400


# ─── GET /v1/avatars/{session_id} ─────────────────────────────────────────────


class TestGetSessionEndpoint:
    def test_get_nonexistent_session_returns_404(self, test_client) -> None:
        """Requesting a session that doesn't exist must return 404."""
        resp = test_client.get("/v1/avatars/nonexistent-session-id-xyz")
        assert resp.status_code == 404

    def test_get_session_error_response_structure(self, test_client) -> None:
        """404 response must include a 'detail' field."""
        resp = test_client.get("/v1/avatars/fake-session-id")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data


# ─── App factory + H-014 cache test ──────────────────────────────────────────


class TestAppFactory:
    def test_create_app_returns_fastapi_instance(self) -> None:
        """create_app() must return a FastAPI application."""
        from fastapi import FastAPI

        from seidr_smidja.bridges.straumur.api import create_app

        app = create_app({"annall": {"adapter": "null"}})
        assert isinstance(app, FastAPI)

    def test_annall_adapter_cached_not_recreated_per_request(
        self, test_client
    ) -> None:
        """H-014: The annall adapter must be created once, not per-request."""
        factory_call_count = 0

        original_make_annall = None
        try:
            from seidr_smidja.annall import factory as annall_factory
            original_make_annall = annall_factory.make_annall
        except ImportError:
            pytest.skip("annall.factory not available")

        def counting_make_annall(*args, **kwargs):
            nonlocal factory_call_count
            factory_call_count += 1
            return original_make_annall(*args, **kwargs)

        from fastapi.testclient import TestClient

        import seidr_smidja.annall.factory as factory_module
        from seidr_smidja.bridges.straumur.api import create_app

        cfg = {"annall": {"adapter": "null"}}
        app = create_app(cfg)
        client = TestClient(app)

        with patch.object(factory_module, "make_annall", side_effect=counting_make_annall):
            # Make two requests that both use annall
            client.get("/v1/health")
            client.get("/v1/health")

        # factory should not be called on subsequent requests (cached after first)
        # The initial construction may have happened before our patch
        assert factory_call_count <= 1, (
            f"H-014 regression: make_annall called {factory_call_count} times across requests"
        )
