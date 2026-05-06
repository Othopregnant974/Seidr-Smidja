"""Hoard — the Asset Hoard.

The library of base materials: VRoid Studio template .vrm files, hair meshes,
outfit meshes, texture sets, and preset collections.

The Hoard is read-only during a build. It lends assets; it never alters them.
What the Hoard gives, the Forge transforms.

Public surface: see INTERFACE.md in this directory.
"""

from seidr_smidja.hoard.exceptions import AssetFetchError, AssetNotFoundError, HoardError
from seidr_smidja.hoard.local import LocalHoardAdapter
from seidr_smidja.hoard.port import AssetFilter, AssetMeta, HoardPort

__all__ = [
    "AssetFilter",
    "AssetMeta",
    "HoardPort",
    "AssetFetchError",
    "AssetNotFoundError",
    "HoardError",
    "LocalHoardAdapter",
]
