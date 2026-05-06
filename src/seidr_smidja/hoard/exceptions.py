"""seidr_smidja.hoard.exceptions — Hoard-domain exception types."""
from __future__ import annotations


class AssetNotFoundError(LookupError):
    """Raised when resolve() cannot find the requested asset.

    Invariant: This is always raised immediately — None is never returned.

    Attributes:
        asset_id: The catalog key that could not be resolved.
        message:  Human-readable diagnostic.
    """

    def __init__(self, asset_id: str, message: str | None = None) -> None:
        self.asset_id = asset_id
        self.message = message or f"Asset not found in Hoard: '{asset_id}'"
        super().__init__(self.message)


class AssetFetchError(RuntimeError):
    """Raised when a remote fetch for an asset fails.

    Used by the future HoardFetcher adapter. Defined here so the exception
    class exists in the public API even though fetch-and-cache is parked for
    a later phase (D-004).

    Attributes:
        asset_id: The catalog key that failed to fetch.
        cause:    The underlying exception that caused the fetch failure.
    """

    def __init__(self, asset_id: str, cause: Exception | None = None) -> None:
        self.asset_id = asset_id
        self.cause = cause
        msg = f"Failed to fetch asset '{asset_id}'"
        if cause:
            msg += f": {cause}"
        super().__init__(msg)


class HoardError(RuntimeError):
    """Raised on catalog read failure or other internal Hoard errors."""
