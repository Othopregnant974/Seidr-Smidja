"""Oracle Eye render script — runs INSIDE Blender via --python.

Injected into a headless Blender process by the Oracle Eye render() function.
Loads a .vrm file, sets up cameras for each requested view, renders via Eevee,
and writes PNG files to the output directory.

Arguments (passed via argv after '--'):
    --vrm <path>       Path to the .vrm file to render
    --views <list>     Comma-separated list of view names (e.g., front,side,t_pose)
    --output <dir>     Directory to write rendered PNG files
    --width <int>      Render width in pixels (default 1024)
    --height <int>     Render height in pixels (default 1024)

Output:
    One PNG per view, named <view_name>.png in the output directory.

Exit codes:
    0 = all views rendered
    1 = argument error
    2 = VRM import error
    3 = camera/scene setup error
    4 = render error (partial renders may exist)

Requires: Blender 3.6+ with VRM Add-on for Blender installed.
Tests requiring this are marked @pytest.mark.requires_blender.
"""
from __future__ import annotations

import math
import os
import sys


def main() -> int:
    """Entry point — returns exit code."""
    argv = sys.argv
    try:
        sep_idx = argv.index("--")
        args = argv[sep_idx + 1:]
    except ValueError:
        print("[render_avatar] ERROR: No '--' separator found in argv.", file=sys.stderr)
        return 1

    vrm_path: str | None = None
    views_str: str = "front,three_quarter,side,face_closeup,t_pose"
    output_dir: str | None = None
    render_width = 1024
    render_height = 1024

    i = 0
    while i < len(args):
        if args[i] == "--vrm" and i + 1 < len(args):
            vrm_path = args[i + 1]
            i += 2
        elif args[i] == "--views" and i + 1 < len(args):
            views_str = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_dir = args[i + 1]
            i += 2
        elif args[i] == "--width" and i + 1 < len(args):
            render_width = int(args[i + 1])
            i += 2
        elif args[i] == "--height" and i + 1 < len(args):
            render_height = int(args[i + 1])
            i += 2
        else:
            i += 1

    if not vrm_path or not output_dir:
        print(
            f"[render_avatar] ERROR: Missing --vrm or --output. Got: vrm={vrm_path}, output={output_dir}",
            file=sys.stderr,
        )
        return 1

    views = [v.strip() for v in views_str.split(",") if v.strip()]
    print(f"[render_avatar] Rendering {len(views)} views: {views}")

    os.makedirs(output_dir, exist_ok=True)

    try:
        import bpy  # type: ignore[import]
    except ImportError:
        print("[render_avatar] ERROR: bpy not available — must run inside Blender.", file=sys.stderr)
        return 2

    # Clear scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Import VRM
    try:
        result = bpy.ops.import_scene.vrm(filepath=vrm_path)
        if "FINISHED" not in result:
            print(f"[render_avatar] ERROR: VRM import returned {result}", file=sys.stderr)
            return 2
        print(f"[render_avatar] VRM imported: {vrm_path}")
    except Exception as exc:
        print(f"[render_avatar] ERROR: VRM import failed: {exc}", file=sys.stderr)
        return 2

    # Configure render settings (Eevee)
    try:
        scene = bpy.context.scene
        scene.render.engine = "BLENDER_EEVEE"
        scene.render.resolution_x = render_width
        scene.render.resolution_y = render_height
        scene.render.image_settings.file_format = "PNG"
        scene.render.film_transparent = True  # Transparent background for compositing

        # Basic lighting: three-point soft setup
        _setup_lighting(bpy)
    except Exception as exc:
        print(f"[render_avatar] ERROR: Scene setup failed: {exc}", file=sys.stderr)
        return 3

    # Find avatar bounds for camera framing
    avatar_bounds = _get_avatar_bounds(bpy)
    errors_occurred = False

    # Render each requested view
    for view_name in views:
        try:
            _setup_camera_for_view(bpy, view_name, avatar_bounds)
            # AUDIT-009 fix: use pathlib.Path per ARCHITECTURE.md §VI project standard.
            # Blender's embedded Python ships pathlib — safe on all supported platforms.
            from pathlib import Path as _Path
            output_path = str(_Path(output_dir) / f"{view_name}.png")
            scene.render.filepath = output_path
            bpy.ops.render.render(write_still=True)
            print(f"[render_avatar] Rendered: {view_name} → {output_path}")
        except Exception as exc:
            print(f"[render_avatar] WARNING: Failed to render view '{view_name}': {exc}", file=sys.stderr)
            errors_occurred = True

    if errors_occurred:
        print("[render_avatar] Completed with some rendering errors.")
        return 4

    print("[render_avatar] All views rendered successfully.")
    return 0


def _get_avatar_bounds(bpy) -> dict:
    """Compute approximate avatar bounding box."""
    min_z = 0.0
    max_z = 1.65
    try:
        for obj in bpy.data.objects:
            if obj.type in ("MESH", "ARMATURE"):
                bounds = [obj.matrix_world @ v.co for v in (obj.bound_box or [])]
                if bounds:
                    zs = [v.z for v in bounds]
                    min_z = min(min_z, min(zs))
                    max_z = max(max_z, max(zs))
    except Exception:
        pass
    height = max_z - min_z
    center_z = (min_z + max_z) / 2.0
    return {
        "min_z": min_z,
        "max_z": max_z,
        "height": height,
        "center_z": center_z,
    }


def _setup_lighting(bpy) -> None:
    """Add a simple three-point lighting setup."""
    import bpy as _bpy

    light_data = [
        ("Key_Light", (3.0, -3.0, 4.0), 800.0),
        ("Fill_Light", (-3.0, -2.0, 2.0), 300.0),
        ("Back_Light", (0.0, 3.0, 4.0), 200.0),
    ]
    for name, location, energy in light_data:
        if name not in _bpy.data.lights:
            light = _bpy.data.lights.new(name=name, type="POINT")
            light.energy = energy
            obj = _bpy.data.objects.new(name, light)
            obj.location = location
            _bpy.context.scene.collection.objects.link(obj)


def _setup_camera_for_view(bpy, view_name: str, bounds: dict) -> None:
    """Create and position a camera for the given view."""
    import bpy as _bpy

    height = bounds.get("height", 1.65)
    center_z = bounds.get("center_z", 0.825)
    dist = height * 1.8  # Base distance from avatar

    # Camera location and rotation per view
    view_configs: dict[str, dict] = {
        "front":              {"location": (0.0, -dist, center_z),       "rotation": (math.pi / 2, 0.0, 0.0)},
        "three_quarter":      {"location": (dist * 0.7, -dist * 0.7, center_z), "rotation": (math.pi / 2, 0.0, math.pi / 4)},
        "side":               {"location": (dist, 0.0, center_z),         "rotation": (math.pi / 2, 0.0, math.pi / 2)},
        "face_closeup":       {"location": (0.0, -dist * 0.4, bounds.get("max_z", 1.65) - height * 0.1),
                               "rotation": (math.pi / 2, 0.0, 0.0)},
        "t_pose":             {"location": (0.0, -dist * 1.4, center_z),  "rotation": (math.pi / 2, 0.0, 0.0)},
        "expression_smile":   {"location": (0.0, -dist * 0.35, bounds.get("max_z", 1.65) - height * 0.08),
                               "rotation": (math.pi / 2, 0.0, 0.0)},
        "expression_sad":     {"location": (0.0, -dist * 0.35, bounds.get("max_z", 1.65) - height * 0.08),
                               "rotation": (math.pi / 2, 0.0, 0.0)},
        "expression_surprised": {"location": (0.0, -dist * 0.35, bounds.get("max_z", 1.65) - height * 0.08),
                                  "rotation": (math.pi / 2, 0.0, 0.0)},
    }

    cfg = view_configs.get(view_name, view_configs["front"])

    # Remove existing camera if any
    for obj in list(_bpy.data.objects):
        if obj.type == "CAMERA":
            _bpy.data.objects.remove(obj, do_unlink=True)

    # Create new camera
    cam_data = _bpy.data.cameras.new(name="RenderCam")
    cam_data.lens = 50.0  # Standard 50mm
    cam_obj = _bpy.data.objects.new("RenderCam", cam_data)
    cam_obj.location = cfg["location"]
    cam_obj.rotation_euler = cfg["rotation"]
    _bpy.context.scene.collection.objects.link(cam_obj)
    _bpy.context.scene.camera = cam_obj


if __name__ == "__main__":
    sys.exit(main())
