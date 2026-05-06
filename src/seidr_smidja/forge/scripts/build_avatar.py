"""Forge build script — runs INSIDE Blender via --python.

This script is injected into a headless Blender process by the Forge runner.
It imports bpy (Blender's Python API) and the VRM Add-on for Blender.

Arguments (passed via argv after '--'):
    --spec <path>     Path to the spec JSON file
    --base <path>     Path to the base .vrm file
    --output <path>   Path where the output .vrm should be written

Supported spec operations in v0.1:
    - Load base .vrm via VRM Add-on for Blender
    - Apply hair color (RGB)
    - Apply eye color (RGB, via shader node or material color)
    - Apply body height scale
    - Set expression default values
    - Export result as .vrm via VRM Add-on

Exit codes:
    0  = success (output .vrm was exported)
    1  = usage / argument error
    2  = spec read / parse error
    3  = VRM import error
    4  = transformation error
    5  = VRM export error

NOTE: This script requires Blender with the VRM Add-on for Blender installed.
      (https://github.com/saturday06/VRM-Addon-for-Blender)
      Tests requiring this are marked @pytest.mark.requires_blender.
"""
from __future__ import annotations

import json
import sys


def main() -> int:
    """Entry point — returns exit code."""
    # Parse arguments from sys.argv after the '--' separator
    argv = sys.argv
    try:
        sep_idx = argv.index("--")
        args = argv[sep_idx + 1:]
    except ValueError:
        print("[build_avatar] ERROR: No '--' separator found in argv.", file=sys.stderr)
        return 1

    spec_path: str | None = None
    base_path: str | None = None
    output_path: str | None = None

    i = 0
    while i < len(args):
        if args[i] == "--spec" and i + 1 < len(args):
            spec_path = args[i + 1]
            i += 2
        elif args[i] == "--base" and i + 1 < len(args):
            base_path = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_path = args[i + 1]
            i += 2
        else:
            i += 1

    if not spec_path or not base_path or not output_path:
        print(
            f"[build_avatar] ERROR: Missing required arguments. "
            f"Got: spec={spec_path}, base={base_path}, output={output_path}",
            file=sys.stderr,
        )
        return 1

    # Load spec
    try:
        with open(spec_path, encoding="utf-8") as fh:
            spec = json.load(fh)
        print(f"[build_avatar] Spec loaded: avatar_id={spec.get('avatar_id', '?')}")
    except Exception as exc:
        print(f"[build_avatar] ERROR: Cannot read spec: {exc}", file=sys.stderr)
        return 2

    # Import bpy (only available inside Blender)
    try:
        import bpy  # type: ignore[import]
    except ImportError:
        print("[build_avatar] ERROR: bpy not available — must run inside Blender.", file=sys.stderr)
        return 3

    # ── Step 1: Clear scene and import base VRM ───────────────────────────────
    try:
        # Remove default cube/light/camera if present
        bpy.ops.wm.read_factory_settings(use_empty=True)

        # Import the base VRM using the VRM Add-on
        result = bpy.ops.import_scene.vrm(filepath=base_path)
        if "FINISHED" not in result:
            print(
                f"[build_avatar] ERROR: VRM import returned {result} for {base_path}",
                file=sys.stderr,
            )
            return 3
        print(f"[build_avatar] Base VRM imported: {base_path}")
    except Exception as exc:
        print(f"[build_avatar] ERROR: VRM import failed: {exc}", file=sys.stderr)
        return 3

    # ── Step 2: Apply spec transformations ────────────────────────────────────
    try:
        _apply_spec(bpy, spec)
    except Exception as exc:
        print(f"[build_avatar] ERROR: Spec application failed: {exc}", file=sys.stderr)
        return 4

    # ── Step 3: Export VRM ────────────────────────────────────────────────────
    try:
        result = bpy.ops.export_scene.vrm(filepath=output_path)
        if "FINISHED" not in result:
            print(
                f"[build_avatar] ERROR: VRM export returned {result} for {output_path}",
                file=sys.stderr,
            )
            return 5
        print(f"[build_avatar] VRM exported: {output_path}")
    except Exception as exc:
        print(f"[build_avatar] ERROR: VRM export failed: {exc}", file=sys.stderr)
        return 5

    print("[build_avatar] Build complete.")
    return 0


def _apply_spec(bpy: object, spec: dict) -> None:
    """Apply parametric spec changes to the loaded Blender scene.

    Covers the v0.1 parameter set:
        - hair color
        - eye color
        - body height scale
        - expression default values

    Args:
        bpy:  The Blender Python API module (already verified available).
        spec: The parsed spec dict.
    """
    import bpy as _bpy  # type: ignore[import]

    # Helper: find a material by name fragment (case-insensitive)
    def find_material(name_fragment: str):
        fragment_lower = name_fragment.lower()
        for mat in _bpy.data.materials:
            if fragment_lower in mat.name.lower():
                return mat
        return None

    # Helper: set a material's principled BSDF base color
    def set_material_color(material, r: float, g: float, b: float) -> bool:
        if material is None:
            return False
        if not material.use_nodes:
            material.use_nodes = True
        for node in material.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                node.inputs["Base Color"].default_value = (r, g, b, 1.0)
                return True
        return False

    # ── Hair color ────────────────────────────────────────────────────────────
    hair_spec = spec.get("hair", {})
    hair_color = hair_spec.get("color", {})
    if isinstance(hair_color, dict):
        hr = float(hair_color.get("r", 0.1))
        hg = float(hair_color.get("g", 0.07))
        hb = float(hair_color.get("b", 0.05))
        # Look for hair material(s)
        for mat in _bpy.data.materials:
            mat_name_lower = mat.name.lower()
            if "hair" in mat_name_lower or "hairs" in mat_name_lower:
                set_material_color(mat, hr, hg, hb)
                print(f"[build_avatar] Hair color applied to material: {mat.name}")

    # ── Eye color ─────────────────────────────────────────────────────────────
    face_spec = spec.get("face", {})
    eye_color = face_spec.get("eye_color", {})
    if isinstance(eye_color, dict):
        er = float(eye_color.get("r", 0.3))
        eg = float(eye_color.get("g", 0.5))
        eb = float(eye_color.get("b", 0.8))
        for mat in _bpy.data.materials:
            mat_name_lower = mat.name.lower()
            if "eye" in mat_name_lower or "iris" in mat_name_lower:
                set_material_color(mat, er, eg, eb)
                print(f"[build_avatar] Eye color applied to material: {mat.name}")

    # ── Body height scale ─────────────────────────────────────────────────────
    body_spec = spec.get("body", {})
    height_scale = float(body_spec.get("height_scale", 1.0))
    if abs(height_scale - 1.0) > 0.001:
        # Scale the root armature on the Z axis
        for obj in _bpy.data.objects:
            if obj.type == "ARMATURE":
                obj.scale[2] *= height_scale
                print(f"[build_avatar] Height scale {height_scale}x applied to armature: {obj.name}")
                break

    # ── Expression default values ─────────────────────────────────────────────
    # VRM 0.x: modify blendShapeGroups default values
    # VRM 1.0: modify expressions preset defaults
    expressions_spec = spec.get("expressions", {})
    targets = expressions_spec.get("targets", [])
    if targets:
        for armature in _bpy.data.objects:
            if armature.type == "ARMATURE" and hasattr(armature.data, "vrm_addon_extension"):
                vrm_ext = armature.data.vrm_addon_extension
                try:
                    # Try VRM 0.x blend_shape_master
                    bsm = vrm_ext.vrm0.blend_shape_master
                    for group in bsm.blend_shape_groups:
                        for target_entry in targets:
                            t_name = target_entry.get("name", "").lower()
                            t_weight = float(target_entry.get("weight", 0.0))
                            if group.preset_name.lower() == t_name or group.name.lower() == t_name:
                                group.preview = t_weight
                                print(
                                    f"[build_avatar] Expression '{t_name}' weight set to {t_weight}"
                                )
                except (AttributeError, Exception):
                    pass

    print("[build_avatar] Spec application complete.")


if __name__ == "__main__":
    sys.exit(main())
