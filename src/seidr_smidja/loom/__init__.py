"""Loom — the Norn-Loom.

The parametric avatar specification layer. The Loom holds and validates the
avatar's full description — body proportions, face shape, hair, outfit,
materials, blendshape values, expressions, license metadata — in YAML or JSON.

Every avatar begins here as a weaving of intent before a single polygon moves.
The wyrd is woven before the iron is struck.

Public surface: see INTERFACE.md in this directory.
"""

from seidr_smidja.loom.exceptions import LoomIOError, LoomValidationError, ValidationFailure
from seidr_smidja.loom.loader import load_and_validate, load_spec
from seidr_smidja.loom.schema import (
    AvatarMetadata,
    AvatarSpec,
    BodySpec,
    ExpressionSpec,
    ExpressionTarget,
    FaceSpec,
    HairSpec,
    OutfitLayer,
    OutfitSpec,
    RGBColor,
)

__all__ = [
    "AvatarSpec",
    "AvatarMetadata",
    "BodySpec",
    "ExpressionSpec",
    "ExpressionTarget",
    "FaceSpec",
    "HairSpec",
    "OutfitLayer",
    "OutfitSpec",
    "RGBColor",
    "LoomIOError",
    "LoomValidationError",
    "ValidationFailure",
    "load_spec",
    "load_and_validate",
]
