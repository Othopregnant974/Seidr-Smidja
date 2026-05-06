"""seidr_smidja.hoard.port — HoardPort Protocol and companion data structures.

Defines the abstract interface that all Hoard adapters implement.
The LocalHoardAdapter is the v0.1 implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class AssetFilter:
    """Filter criteria for list_assets()."""

    asset_type: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class AssetMeta:
    """Metadata record for a Hoard asset, as returned by list_assets()."""

    asset_id: str
    display_name: str
    asset_type: str
    tags: list[str]
    vrm_version: str
    file_size_bytes: int | None
    cached: bool


@runtime_checkable
class HoardPort(Protocol):
    """The abstract interface for the Hoard. All adapters implement these methods."""

    def resolve(self, asset_id: str) -> Path:
        """Resolve an asset_id to a local filesystem path.

        The returned path is guaranteed to exist at the moment of return.

        Raises:
            AssetNotFoundError: If the asset is not in the catalog or not locally cached.
            AssetFetchError:    If a remote fetch was attempted and failed.
        """
        ...

    def list_assets(self, filter: AssetFilter | None = None) -> list[AssetMeta]:
        """Return metadata for all assets matching the filter.

        Raises:
            HoardError: On catalog read failure.
        """
        ...

    def catalog_path(self) -> Path:
        """Return the path to the catalog YAML file."""
        ...
