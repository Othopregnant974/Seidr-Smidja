"""Forge texture tint script — applies Runa's colors to TurboSquid textures.

Runs OUTSIDE Blender (uses Pillow + NumPy) to modify PBR texture images
based on the avatar spec. This is called BEFORE the Blender build script,
so the modified textures are available when Blender imports the FBX.

The TurboSquid model has PBR texture images connected to every material's
Principled BSDF Base Color. Simply setting default_value on the BSDF node
has no effect during VRM/glTF export — the connected texture wins.

Instead, we tint the texture images directly using HSV color shifts:
    - Skin: shift H/S/V toward golden-tan (0.08, 0.55, 0.88)
    - Eyes: shift toward ice-blue
    - Hair: shift toward blonde

This preserves the original texture detail (wrinkles, pores, shading)
while achieving the desired color palette.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("[tint_textures] ERROR: Pillow and NumPy required. pip install Pillow numpy")
    sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# Color targets (HSV, 0-1 range)
# ──────────────────────────────────────────────────────────────────────────────
SKIN_HSV = (0.08, 0.55, 0.88)  # warm golden-tan
EYE_HSV = (0.55, 0.70, 0.82)  # ice-blue
HAIR_HSV = (0.10, 0.60, 0.56)  # warm blonde
NAIL_HSV = (0.95, 0.25, 0.75)  # subtle pink-nude
LIP_HSV = (0.97, 0.45, 0.70)   # natural lip tint

# Material name → HSV target mapping
MATERIAL_TINT_MAP = {
    "skin_head": SKIN_HSV,
    "skin_body": SKIN_HSV,
    "skin_arm": SKIN_HSV,
    "skin_leg": SKIN_HSV,
    "eye_l": EYE_HSV,
    "eye_r": EYE_HSV,
    "iris": EYE_HSV,
    "hair": HAIR_HSV,
    "scalp": HAIR_HSV,
    "nail": NAIL_HSV,
    "lip": LIP_HSV,
}


def hsv_shift_image(img: Image.Image, target_h: float, target_s: float,
                     target_v: float, blend: float = 0.6) -> Image.Image:
    """Shift an image's dominant hue/saturation/value toward a target HSV.

    Uses a luminance-preserving blend: keeps the original value (brightness)
    pattern but shifts hue and saturation toward the target. This preserves
    texture detail while achieving the desired color palette.

    Args:
        img:    PIL Image (RGB or RGBA)
        target_h: Target hue (0-1)
        target_s: Target saturation (0-1)
        target_v: Target value/brightness (0-1)
        blend:   Blend factor (0=original, 1=full target)
    """
    img = img.convert("RGBA")
    arr = np.array(img, dtype=np.float32) / 255.0

    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]

    # Convert to HSV
    maxc = np.maximum(np.maximum(rgb[:, :, 0], rgb[:, :, 1]), rgb[:, :, 2])
    minc = np.minimum(np.minimum(rgb[:, :, 0], rgb[:, :, 1]), rgb[:, :, 2])
    diff = maxc - minc

    # Hue
    hue = np.zeros_like(maxc)
    mask_r = (maxc == rgb[:, :, 0]) & (diff > 0)
    mask_g = (maxc == rgb[:, :, 1]) & (diff > 0)
    mask_b = (maxc == rgb[:, :, 2]) & (diff > 0)
    hue[mask_r] = ((rgb[:, :, 1][mask_r] - rgb[:, :, 2][mask_r]) / diff[mask_r]) % 6
    hue[mask_g] = ((rgb[:, :, 2][mask_g] - rgb[:, :, 0][mask_g]) / diff[mask_g]) + 2
    hue[mask_b] = ((rgb[:, :, 0][mask_b] - rgb[:, :, 1][mask_b]) / diff[mask_b]) + 4
    hue = hue / 6.0  # Normalize to 0-1

    # Saturation
    sat = np.where(maxc > 0, diff / maxc, 0.0)

    # Value
    val = maxc

    # Blend toward target
    # For skin: shift hue and saturation more aggressively, preserve value pattern
    # For eyes: full replacement
    new_hue = hue * (1 - blend) + target_h * blend
    new_sat = sat * (1 - blend) + target_s * blend
    # Value: keep the original value pattern for texture detail, 
    # but shift average toward target
    val_mean = np.mean(val[val > 0.01]) if np.any(val > 0.01) else target_v
    val_scale = target_v / val_mean if val_mean > 0 else 1.0
    new_val = val * val_scale
    new_val = np.clip(new_val, 0, 1)

    # Convert back to RGB
    new_hue = new_hue % 1.0
    new_sat = np.clip(new_sat, 0, 1)

    # HSV to RGB
    c = new_val * new_sat
    x = c * (1 - np.abs((new_hue * 6) % 2 - 1))
    m = new_val - c

    rgb_new = np.zeros_like(rgb)

    h6 = new_hue * 6
    mask = (h6 >= 0) & (h6 < 1)
    rgb_new[:, :, 0] = np.where(mask, c, rgb_new[:, :, 0])
    rgb_new[:, :, 1] = np.where(mask, x, rgb_new[:, :, 1])
    rgb_new[:, :, 2] = np.where(mask, m, rgb_new[:, :, 2])

    mask = (h6 >= 1) & (h6 < 2)
    rgb_new[:, :, 0] = np.where(mask, x, rgb_new[:, :, 0])
    rgb_new[:, :, 1] = np.where(mask, c, rgb_new[:, :, 1])

    mask = (h6 >= 2) & (h6 < 3)
    rgb_new[:, :, 1] = np.where(mask, c, rgb_new[:, :, 1])
    rgb_new[:, :, 2] = np.where(mask, x, rgb_new[:, :, 2])

    mask = (h6 >= 3) & (h6 < 4)
    rgb_new[:, :, 0] = np.where(mask, m, rgb_new[:, :, 0])
    rgb_new[:, :, 1] = np.where(mask, x, rgb_new[:, :, 1])
    rgb_new[:, :, 2] = np.where(mask, c, rgb_new[:, :, 2])

    mask = (h6 >= 4) & (h6 < 5)
    rgb_new[:, :, 0] = np.where(mask, x, rgb_new[:, :, 0])
    rgb_new[:, :, 2] = np.where(mask, c, rgb_new[:, :, 2])

    mask = (h6 >= 5) & (h6 < 6)
    rgb_new[:, :, 0] = np.where(mask, c, rgb_new[:, :, 0])
    rgb_new[:, :, 2] = np.where(mask, x, rgb_new[:, :, 2])

    rgb_new[:, :, 0] += m
    rgb_new[:, :, 1] += m
    rgb_new[:, :, 2] += m

    arr_out = np.zeros_like(arr)
    arr_out[:, :, :3] = np.clip(rgb_new * 255, 0, 255)
    arr_out[:, :, 3] = alpha * 255

    return Image.fromarray(arr_out.astype(np.uint8), "RGBA")


def main() -> int:
    """Entry point — returns exit code."""
    argv = sys.argv
    try:
        sep_idx = argv.index("--")
        args = argv[sep_idx + 1:]
    except ValueError:
        print("[tint_textures] ERROR: No '--' separator found in argv.", file=sys.stderr)
        return 1

    spec_path: str | None = None
    base_path: str | None = None
    output_dir: str | None = None

    i = 0
    while i < len(args):
        if args[i] == "--spec" and i + 1 < len(args):
            spec_path = args[i + 1]
            i += 2
        elif args[i] == "--base" and i + 1 < len(args):
            base_path = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_dir = args[i + 1]
            i += 2
        else:
            i += 1

    if not base_path or not output_dir:
        print("[tint_textures] ERROR: --base and --output required.", file=sys.stderr)
        return 1

    # Load spec for color overrides
    spec = {}
    if spec_path:
        try:
            with open(spec_path, encoding="utf-8") as fh:
                spec = json.load(fh)
        except Exception as exc:
            print(f"[tint_textures] WARNING: Cannot read spec: {exc}")

    # Find texture directory (next to the FBX or in a textures/ subdirectory)
    base_dir = Path(base_path).parent
    texture_dirs = [
        base_dir / "textures",
        base_dir / "Textures",
        base_dir / "material",
        base_dir / "Material",
        base_dir / "maps",
        base_dir / "Maps",
        base_dir,
    ]

    texture_dir = None
    for d in texture_dirs:
        if d.exists():
            image_files = list(d.glob("*.png")) + list(d.glob("*.jpg")) + list(d.glob("*.tga"))
            if image_files:
                texture_dir = d
                break

    if texture_dir is None:
        print("[tint_textures] WARNING: No texture directory found")
        return 0

    print(f"[tint_textures] Using texture directory: {texture_dir}")
    print(f"[tint_textures] Found {len(list(texture_dir.glob('*.png')) + list(texture_dir.glob('*.jpg')))} texture files")

    # Create tinted texture output directory
    output_path = Path(output_dir) / "tinted_textures"
    output_path.mkdir(parents=True, exist_ok=True)

    # Override HSV targets from spec if provided
    face_spec = spec.get("face", {})
    skin_color = face_spec.get("skin_color", {})
    if isinstance(skin_color, dict):
        # Convert RGB (0-1) to HSV for skin tint override
        r, g, b = float(skin_color.get("r", 0.87)), float(skin_color.get("g", 0.70)), float(skin_color.get("b", 0.58))
        SKIN_HSV = _rgb_to_hsv(r, g, b)
        # Update the tint map
        for key in ("skin_head", "skin_body", "skin_arm", "skin_leg"):
            MATERIAL_TINT_MAP[key] = SKIN_HSV

    eye_color = face_spec.get("eye_color", {})
    if isinstance(eye_color, dict):
        r, g, b = float(eye_color.get("r", 0.58)), float(eye_color.get("g", 0.72)), float(eye_color.get("b", 0.81))
        EYE_HSV = _rgb_to_hsv(r, g, b)
        for key in ("eye_l", "eye_r", "iris"):
            MATERIAL_TINT_MAP[key] = EYE_HSV

    hair_spec = spec.get("hair", {})
    hair_color = hair_spec.get("color", {})
    if isinstance(hair_color, dict):
        r, g, b = float(hair_color.get("r", 0.56)), float(hair_color.get("g", 0.45)), float(hair_color.get("b", 0.25))
        HAIR_HSV = _rgb_to_hsv(r, g, b)
        for key in ("hair", "scalp"):
            MATERIAL_TINT_MAP[key] = HAIR_HSV

    # Process each texture file
    tinted_count = 0
    for tex_file in sorted(texture_dir.glob("*.png")) + sorted(texture_dir.glob("*.jpg")) + sorted(texture_dir.glob("*.tga")):
        tex_name_lower = tex_file.name.lower()

        # Determine which material category this texture belongs to
        target_hsv = None
        blend_factor = 0.6
        for keyword, hsv_target in MATERIAL_TINT_MAP.items():
            if keyword in tex_name_lower:
                target_hsv = hsv_target
                break

        # Also check for common texture naming patterns
        if target_hsv is None:
            if any(kw in tex_name_lower for kw in ("albedo", "diffuse", "color", "basecolor", "base_color")):
                # Heuristic: check which material group the texture serves
                if any(kw in tex_name_lower for kw in ("skin", "body", "head", "arm", "leg", "face")):
                    target_hsv = SKIN_HSV
                elif any(kw in tex_name_lower for kw in ("eye", "iris", "cornea")):
                    target_hsv = EYE_HSV
                elif any(kw in tex_name_lower for kw in ("hair", "scalp")):
                    target_hsv = HAIR_HSV

        if target_hsv is None:
            # No tint needed for this texture — just copy it
            out_file = output_path / tex_file.name
            if not out_file.exists():
                import shutil
                shutil.copy2(tex_file, out_file)
            continue

        # Apply HSV tint
        try:
            img = Image.open(tex_file)
            tinted = hsv_shift_image(img, *target_hsv, blend=blend_factor)
            out_file = output_path / tex_file.name
            # Always save as PNG for consistency
            out_file = out_file.with_suffix(".png")
            tinted.save(str(out_file), "PNG")
            tinted_count += 1
            print(f"[tint_textures] Tinted: {tex_file.name} → {out_file.name}")
        except Exception as exc:
            print(f"[tint_textures] WARNING: Failed to tint {tex_file.name}: {exc}")

    # Also copy non-albedo textures (normals, roughness, AO, etc.)
    for tex_file in sorted(texture_dir.glob("*.png")) + sorted(texture_dir.glob("*.jpg")) + sorted(texture_dir.glob("*.tga")):
        out_file = output_path / tex_file.name
        if not out_file.exists():
            import shutil
            shutil.copy2(tex_file, out_file)

    print(f"[tint_textures] Tinted {tinted_count} textures, output in {output_path}")
    return 0


def _rgb_to_hsv(r: float, g: float, b: float) -> tuple[float, float, float]:
    """Convert RGB (0-1) to HSV (0-1)."""
    import colorsys
    return colorsys.rgb_to_hsv(r, g, b)


if __name__ == "__main__":
    sys.exit(main())