"""seidr_smidja.loom.schema — AvatarSpec Pydantic v2 model.

The Loom schema is the avatar's wyrd — the complete parametric description
of everything that can be specified before a single vertex moves.

Key invariants:
    - No import from Forge, Oracle Eye, Gate, Bridges, or Hoard.
    - The extensions field is opaque: stored faithfully, never inspected.
    - All color values are RGB tuples normalized to [0.0, 1.0].
    - Height and scale values are relative multipliers (1.0 = default).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ─── Sub-models ───────────────────────────────────────────────────────────────


class RGBColor(BaseModel):
    """A color value as normalized RGB floats in [0.0, 1.0]."""

    model_config = ConfigDict(frozen=True)

    r: float = Field(ge=0.0, le=1.0, description="Red channel [0.0–1.0]")
    g: float = Field(ge=0.0, le=1.0, description="Green channel [0.0–1.0]")
    b: float = Field(ge=0.0, le=1.0, description="Blue channel [0.0–1.0]")

    @classmethod
    def from_list(cls, values: list[float] | tuple[float, ...]) -> RGBColor:
        """Convenience: construct from a 3-element list/tuple."""
        if len(values) != 3:
            raise ValueError(f"RGB color must have exactly 3 channels, got {len(values)}")
        return cls(r=values[0], g=values[1], b=values[2])

    def to_list(self) -> list[float]:
        """Return as [r, g, b] list."""
        return [self.r, self.g, self.b]


class BodySpec(BaseModel):
    """Body proportions and skeletal parameters."""

    model_config = ConfigDict(frozen=True)

    height_scale: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Height multiplier relative to base mesh (0.5–2.0). 1.0 = base height.",
    )
    # Head-to-body ratio scale: 1.0 = default VRoid proportions
    head_scale: float = Field(
        default=1.0, ge=0.5, le=2.0, description="Head size scale relative to body."
    )
    # Upper/lower body proportions
    upper_body_scale: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Scale multiplier for torso (chest, shoulders, waist).",
    )
    lower_body_scale: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Scale multiplier for hips, thighs, and legs.",
    )
    # Arm/leg length multipliers
    arm_length_scale: float = Field(
        default=1.0, ge=0.5, le=2.0, description="Arm length scale."
    )
    leg_length_scale: float = Field(
        default=1.0, ge=0.5, le=2.0, description="Leg length scale."
    )


class FaceSpec(BaseModel):
    """Facial feature configuration."""

    model_config = ConfigDict(frozen=True)

    eye_color: RGBColor = Field(
        default_factory=lambda: RGBColor(r=0.3, g=0.5, b=0.8),
        description="Eye iris color as normalized RGB.",
    )
    eye_scale: float = Field(
        default=1.0, ge=0.5, le=2.0, description="Eye size scale multiplier."
    )
    # Nose scale (0 = flat, 1 = default, 2 = prominent)
    nose_scale: float = Field(
        default=1.0, ge=0.0, le=2.0, description="Nose scale multiplier."
    )
    # Mouth width scale
    mouth_width_scale: float = Field(
        default=1.0, ge=0.5, le=2.0, description="Mouth width scale multiplier."
    )
    # Skin tone (base mesh skin color multiplier)
    skin_color: RGBColor = Field(
        default_factory=lambda: RGBColor(r=1.0, g=0.88, b=0.79),
        description="Skin color tint as normalized RGB. 1,1,1 = no change.",
    )


class HairSpec(BaseModel):
    """Hair style and color parameters."""

    model_config = ConfigDict(frozen=True)

    color: RGBColor = Field(
        default_factory=lambda: RGBColor(r=0.1, g=0.07, b=0.05),
        description="Hair color as normalized RGB.",
    )
    # Style ID references a named style in the Hoard hair catalog (v0.1: informational only)
    style_id: str | None = Field(
        default=None,
        description="Optional hair style ID from the Hoard catalog. None = use base mesh default.",
    )
    length_scale: float = Field(
        default=1.0,
        ge=0.0,
        le=3.0,
        description="Hair length scale multiplier. 0 = short/cut, 1 = default, 3 = very long.",
    )
    # Enable/disable hair physics spring bones
    physics_enabled: bool = Field(
        default=True, description="Whether to keep hair spring-bone physics enabled."
    )


class OutfitLayer(BaseModel):
    """A single outfit layer (garment)."""

    model_config = ConfigDict(frozen=True)

    layer_id: str = Field(description="Outfit layer identifier (e.g., 'top', 'bottom', 'shoes').")
    mesh_id: str | None = Field(
        default=None,
        description="Optional Hoard mesh ID for this layer. None = use base mesh default.",
    )
    # Primary color for this layer's main material
    primary_color: RGBColor | None = Field(
        default=None, description="Primary color override. None = use mesh default."
    )
    secondary_color: RGBColor | None = Field(
        default=None, description="Secondary color override. None = use mesh default."
    )
    visible: bool = Field(default=True, description="Whether this layer is visible in the output.")


class OutfitSpec(BaseModel):
    """Outfit configuration — list of outfit layers."""

    model_config = ConfigDict(frozen=True)

    layers: list[OutfitLayer] = Field(
        default_factory=list,
        description="Ordered list of outfit layers. Empty = use all base mesh defaults.",
    )


class ExpressionTarget(BaseModel):
    """A single expression blendshape target and its weight."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Blendshape name (case-insensitive matching against known set).")
    weight: float = Field(
        ge=0.0, le=1.0, description="Default weight for this expression target [0.0–1.0]."
    )

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Expression target name must not be empty.")
        return v.strip().lower()


class ExpressionSpec(BaseModel):
    """Named expression blendshape targets and their default weights."""

    model_config = ConfigDict(frozen=True)

    targets: list[ExpressionTarget] = Field(
        default_factory=list,
        description="Expression blendshape targets. Empty = use base mesh defaults.",
    )


class AvatarMetadata(BaseModel):
    """License and authorship metadata for the avatar."""

    model_config = ConfigDict(frozen=True)

    author: str = Field(description="Avatar author name.")
    license: str = Field(
        default="CC0-1.0",
        description="SPDX license identifier for the avatar output (e.g., 'CC0-1.0', 'CC-BY-4.0').",
    )
    contact_url: str | None = Field(
        default=None, description="Optional URL for author contact or attribution."
    )
    commercial_use: bool = Field(
        default=False,
        description="Whether commercial use of the avatar output is permitted.",
    )
    redistribution: bool = Field(
        default=True, description="Whether redistribution of the avatar output is permitted."
    )
    credit_notation: str | None = Field(
        default=None, description="Optional credit notation string to embed in VRM metadata."
    )
    # Platform tags identify intended deployment platforms
    platform_tags: list[str] = Field(
        default_factory=list,
        description="Intended platform deployment tags (e.g., ['vrchat', 'vtube_studio']).",
    )


# ─── Top-level AvatarSpec ────────────────────────────────────────────────────


_SUPPORTED_SPEC_VERSIONS = {"1.0"}


class AvatarSpec(BaseModel):
    """The complete parametric avatar specification — the wyrd woven before the strike.

    This is the canonical Loom output: a validated, typed description of every
    avatar parameter. The Forge receives this and translates it into mesh, bone,
    material, and expression.

    Invariants:
        - spec_version must be in the supported set.
        - avatar_id must be a non-empty slug (no spaces, URL-safe).
        - extensions is opaque and round-trips faithfully.
    """

    model_config = ConfigDict(frozen=True)

    spec_version: str = Field(description="Spec format version. Currently: '1.0'.")
    avatar_id: str = Field(description="Stable unique identifier slug (e.g., 'my_avatar_v1').")
    display_name: str = Field(description="Human/agent-readable avatar name.")
    base_asset_id: str = Field(description="Key into the Hoard catalog for the base .vrm mesh.")
    body: BodySpec = Field(default_factory=BodySpec)
    face: FaceSpec = Field(default_factory=FaceSpec)
    hair: HairSpec = Field(default_factory=HairSpec)
    outfit: OutfitSpec = Field(default_factory=OutfitSpec)
    expressions: ExpressionSpec = Field(default_factory=ExpressionSpec)
    metadata: AvatarMetadata
    # Extension hatch: opaque, preserved faithfully, never inspected by the Loom.
    extensions: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Opaque extension fields. Namespaced by consumer "
            "(e.g., extensions.nse, extensions.vgsk). "
            "The Loom preserves this faithfully without reading it."
        ),
    )

    @field_validator("spec_version")
    @classmethod
    def check_spec_version(cls, v: str) -> str:
        if v not in _SUPPORTED_SPEC_VERSIONS:
            raise ValueError(
                f"Unsupported spec_version '{v}'. "
                f"Supported versions: {sorted(_SUPPORTED_SPEC_VERSIONS)}"
            )
        return v

    @field_validator("avatar_id")
    @classmethod
    def check_avatar_id(cls, v: str) -> str:
        import re

        if not v.strip():
            raise ValueError("avatar_id must not be empty.")
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError(
                f"avatar_id '{v}' must be a slug: only letters, digits, underscores, hyphens."
            )
        return v

    # ── Serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict representation (suitable for JSON/YAML serialization)."""
        return self.model_dump()

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json(indent=2)

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        return yaml.dump(self.to_dict(), allow_unicode=True, default_flow_style=False)

    def to_file(self, path: Path) -> None:
        """Write to file. Format determined by extension (.yaml/.yml → YAML, .json → JSON).

        Raises:
            LoomIOError: On I/O failure or unsupported extension.
        """
        from seidr_smidja.loom.exceptions import LoomIOError

        suffix = path.suffix.lower()
        try:
            if suffix in (".yaml", ".yml"):
                content = self.to_yaml()
            elif suffix == ".json":
                content = self.to_json()
            else:
                raise LoomIOError(f"Unsupported file extension '{suffix}'. Use .yaml or .json.")
            path.write_text(content, encoding="utf-8")
        except LoomIOError:
            raise
        except OSError as exc:
            raise LoomIOError(f"Failed to write spec to {path}: {exc}") from exc

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AvatarSpec:
        """Parse and validate from a raw dict.

        Raises:
            pydantic.ValidationError — structural/type errors.
        """
        return cls.model_validate(data)
