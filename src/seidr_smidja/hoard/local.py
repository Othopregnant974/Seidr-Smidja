"""seidr_smidja.hoard.local — LocalHoardAdapter

D-004: In v0.1, the Hoard is local-only. Assets must be present in the
configured bases_dir. No network calls. Use bootstrap_hoard.py to seed assets
before first run.

Reads catalog from the YAML file at config.hoard.catalog_path.
Resolves assets from config.hoard.bases_dir.

AUDIT-005 fix: resolve() and list_assets() now accept optional annall and
session_id parameters so the Hoard domain logs its own 'hoard.resolved' and
'hoard.listed' events directly (D-005 Option B). The caller (dispatch.py)
must NOT also log 'hoard.resolved' to avoid duplicate events — see dispatch.py
AUDIT-005 comment.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from seidr_smidja.hoard.exceptions import AssetNotFoundError, HoardError, HoardSecurityError
from seidr_smidja.hoard.port import AssetFilter, AssetMeta

if TYPE_CHECKING:
    # AnnallPort is a Protocol — import only for type checking to avoid circular imports.
    from seidr_smidja.annall.port import AnnallPort

logger = logging.getLogger(__name__)


def _validate_catalog_entries(
    entries: list[Any],
    catalog_path: Path,
) -> list[Any]:
    """H-013: Validate catalog entries, warning on malformed or duplicate data.

    Validation is advisory — invalid entries are excluded from the result but
    do not crash the catalog load. This surfaces data quality issues without
    breaking the pipeline (graceful degradation per PHILOSOPHY §Sacred Law VIII).

    Args:
        entries:       The raw list from catalog_data["bases"].
        catalog_path:  Used in warning messages for diagnostics.

    Returns:
        A filtered list containing only entries that pass basic structural checks.
    """
    if not isinstance(entries, list):
        logger.warning(
            "Hoard catalog at %s: 'bases' field is not a list (got %s) — treating as empty.",
            catalog_path,
            type(entries).__name__,
        )
        return []

    seen_ids: set[str] = set()
    valid: list[Any] = []

    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            logger.warning(
                "Hoard catalog at %s: entry[%d] is not a mapping — skipped.",
                catalog_path,
                i,
            )
            continue

        asset_id = entry.get("asset_id")
        filename = entry.get("filename")

        if not asset_id:
            logger.warning(
                "Hoard catalog at %s: entry[%d] is missing 'asset_id' field — skipped.",
                catalog_path,
                i,
            )
            continue

        if not filename:
            logger.warning(
                "Hoard catalog at %s: entry '%s' is missing 'filename' field — skipped.",
                catalog_path,
                asset_id,
            )
            continue

        if asset_id in seen_ids:
            logger.warning(
                "Hoard catalog at %s: duplicate asset_id '%s' — second occurrence skipped.",
                catalog_path,
                asset_id,
            )
            continue

        seen_ids.add(asset_id)
        valid.append(entry)

    return valid


class LocalHoardAdapter:
    """Resolves Hoard assets from a local catalog and bases directory.

    Args:
        catalog_path: Path to the catalog.yaml file.
        bases_dir:    Directory containing base .vrm files (e.g., data/hoard/bases/).

    The catalog file lists available assets; the bases_dir contains the actual files.
    Paths in the catalog are relative to bases_dir.
    """

    def __init__(self, catalog_path: Path, bases_dir: Path) -> None:
        self._catalog_path = catalog_path
        self._bases_dir = bases_dir
        self._catalog: list[dict[str, Any]] = []
        self._loaded = False

    def _load_catalog(self) -> None:
        """Load the catalog YAML (lazy load on first access)."""
        if self._loaded:
            return
        try:
            with self._catalog_path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if not isinstance(data, dict):
                raise HoardError(f"Catalog file {self._catalog_path} is not a YAML mapping.")
            raw_entries = data.get("bases", [])
            # H-013: Validate catalog entries and warn on malformed or duplicate data.
            self._catalog = _validate_catalog_entries(raw_entries, self._catalog_path)
            self._loaded = True
            logger.debug(
                "Hoard catalog loaded: %d assets from %s",
                len(self._catalog),
                self._catalog_path,
            )
        except FileNotFoundError as exc:
            raise HoardError(
                f"Hoard catalog not found at {self._catalog_path}. "
                "Run 'python tools/bootstrap_hoard.py' to seed assets."
            ) from exc
        except Exception as exc:
            raise HoardError(f"Failed to load Hoard catalog: {exc}") from exc

    def _find_entry(self, asset_id: str) -> dict[str, Any] | None:
        """Look up a catalog entry by asset_id."""
        self._load_catalog()
        for entry in self._catalog:
            if entry.get("asset_id") == asset_id:
                return entry
        return None

    def resolve(
        self,
        asset_id: str,
        annall: AnnallPort | None = None,
        session_id: str | None = None,
    ) -> Path:
        """Resolve an asset_id to an absolute filesystem path.

        AUDIT-005: When annall and session_id are provided, the Hoard logs its own
        'hoard.resolved' event (D-005 Option B). The caller must NOT also log this
        event to avoid duplicates — see dispatch.py AUDIT-005 comment.

        Args:
            asset_id:   The catalog key to resolve.
            annall:     Optional AnnallPort for structured event logging.
            session_id: Session ID for the Annáll event.

        Raises:
            AssetNotFoundError: If the asset is not in catalog or file is missing.
            HoardError:         On catalog read failure.
        """
        entry = self._find_entry(asset_id)
        if entry is None:
            raise AssetNotFoundError(
                asset_id=asset_id,
                message=(
                    f"Asset '{asset_id}' not found in Hoard catalog at "
                    f"{self._catalog_path}. "
                    "Run 'python tools/bootstrap_hoard.py' to download available assets, "
                    "or check the catalog for valid asset_id values."
                ),
            )

        filename = entry.get("filename")
        if not filename:
            raise AssetNotFoundError(
                asset_id=asset_id,
                message=f"Catalog entry for '{asset_id}' is missing 'filename' field.",
            )

        asset_path = (self._bases_dir / filename).resolve()

        # H-003: Verify the resolved path is actually inside bases_dir.
        # A crafted catalog entry such as "../../etc/passwd" would pass through
        # resolve() with the traversal silently normalized unless we call
        # relative_to() on the resolved result.
        bases_resolved = self._bases_dir.resolve()
        try:
            asset_path.relative_to(bases_resolved)
        except ValueError:
            msg = (
                f"Catalog entry for '{asset_id}' has a filename that resolves "
                f"outside the Hoard bases_dir. Resolved path: {asset_path}. "
                f"Expected a child of: {bases_resolved}. "
                "This may indicate a tampered catalog."
            )
            logger.error(
                "Hoard security: path traversal rejected for asset '%s': %s → %s",
                asset_id,
                filename,
                asset_path,
            )
            raise HoardSecurityError(asset_id=asset_id, message=msg)

        if not asset_path.exists():
            cached = entry.get("cached", False)
            if not cached:
                raise AssetNotFoundError(
                    asset_id=asset_id,
                    message=(
                        f"Asset '{asset_id}' is in the catalog but not cached locally. "
                        f"Expected path: {asset_path}. "
                        "Run 'python tools/bootstrap_hoard.py' to download it."
                    ),
                )
            raise AssetNotFoundError(
                asset_id=asset_id,
                message=(
                    f"Asset '{asset_id}' is marked as cached but the file is missing: "
                    f"{asset_path}. The catalog may be out of sync — re-run bootstrap."
                ),
            )

        logger.debug("Hoard resolved '%s' → %s", asset_id, asset_path)

        # AUDIT-005: Hoard logs its own event when Annáll is injected (Option B).
        if annall is not None and session_id is not None:
            try:
                from seidr_smidja.annall.port import AnnallEvent

                annall.log_event(
                    session_id,
                    AnnallEvent.info(
                        "hoard.resolved",
                        {"asset_id": asset_id, "path": str(asset_path)},
                    ),
                )
            except Exception:
                pass  # Annáll failure must never crash the Hoard

        return asset_path

    def list_assets(
        self,
        filter: AssetFilter | None = None,
        annall: AnnallPort | None = None,
        session_id: str | None = None,
    ) -> list[AssetMeta]:
        """Return metadata for all assets matching the filter.

        AUDIT-005: When annall and session_id are provided, the Hoard logs its own
        'hoard.listed' event (D-005 Option B).

        Args:
            filter:     Optional filter criteria.
            annall:     Optional AnnallPort for structured event logging.
            session_id: Session ID for the Annáll event.

        Raises:
            HoardError: On catalog read failure.
        """
        self._load_catalog()
        results: list[AssetMeta] = []
        for entry in self._catalog:
            aid = entry.get("asset_id", "")
            tags = entry.get("tags", [])
            asset_type = "vrm_base"  # All catalog entries in v0.1 are VRM bases

            # Apply filters
            if filter is not None:
                if filter.asset_type and asset_type != filter.asset_type:
                    continue
                if filter.tags:
                    # All requested tags must be present
                    if not all(t in tags for t in filter.tags):
                        continue

            # Determine if locally cached
            filename = entry.get("filename")
            cached = False
            if filename:
                path = self._bases_dir / filename
                cached = path.exists()

            results.append(
                AssetMeta(
                    asset_id=aid,
                    display_name=entry.get("display_name", aid),
                    asset_type=asset_type,
                    tags=tags,
                    vrm_version=entry.get("vrm_version", "unknown"),
                    file_size_bytes=entry.get("file_size_bytes"),
                    cached=cached,
                )
            )

        # AUDIT-005: Hoard logs its own event when Annáll is injected (Option B).
        if annall is not None and session_id is not None:
            try:
                from seidr_smidja.annall.port import AnnallEvent

                annall.log_event(
                    session_id,
                    AnnallEvent.info(
                        "hoard.listed",
                        {"count": len(results), "filter": str(filter)},
                    ),
                )
            except Exception:
                pass  # Annáll failure must never crash the Hoard

        return results

    def catalog_path(self) -> Path:
        """Return the path to the catalog YAML file."""
        return self._catalog_path

    @classmethod
    def from_config(cls, config: dict[str, Any], project_root: Path | None = None) -> LocalHoardAdapter:
        """Construct from a resolved config dict.

        Args:
            config:       The config dict from seidr_smidja.config.load_config().
            project_root: Optional root for resolving relative paths.
        """
        root = project_root or Path(".")
        hoard_cfg = config.get("hoard", {})
        catalog_path = (root / Path(hoard_cfg.get("catalog_path", "data/hoard/catalog.yaml"))).resolve()
        bases_dir = (root / Path(hoard_cfg.get("bases_dir", "data/hoard/bases"))).resolve()
        return cls(catalog_path=catalog_path, bases_dir=bases_dir)
