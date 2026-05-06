# Seiðr-Smiðja — Claude Code Skill

This document describes how a Claude Code agent (or any agent using the Claude Code
CLI pattern) invokes the Seiðr-Smiðja forge through the Rúnstafr CLI bridge.

---

## Setup (one time)

```bash
# Install the package
pip install seidr-smidja

# Seed the Hoard with base VRM assets (required before first build)
python tools/bootstrap_hoard.py

# Verify installation
python tools/verify_install.py

# Set Blender path (required for actual builds; not needed for inspect/list-assets)
export SEIDR_BLENDER_PATH="/path/to/blender"
# Windows:
# $env:SEIDR_BLENDER_PATH = "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
```

---

## Primary Rite — Build an Avatar

```bash
# Build from a spec file (produces .vrm + renders in output/)
seidr build examples/spec_minimal.yaml --out output/ --json

# Build with explicit views and targets
seidr build my_spec.yaml --out output/ --views front,side,face_closeup --targets VRCHAT --json
```

**JSON output fields:**
```json
{
  "success": true,
  "vrm_path": "output/my_avatar_v1.vrm",
  "render_paths": {
    "front": "output/front.png",
    "side": "output/side.png"
  },
  "compliance_passed": true,
  "session_id": "uuid",
  "elapsed_seconds": 42.3,
  "errors": []
}
```

---

## Inspect an Existing VRM

```bash
seidr inspect output/my_avatar.vrm --json
```

---

## List Available Base Assets

```bash
seidr list-assets
```

---

## Version Check

```bash
seidr version
```

---

## Spec File Format

See `examples/spec_minimal.yaml` for the simplest valid spec.
See `examples/spec_full.yaml` for all supported fields.

Key required fields:
```yaml
spec_version: "1.0"
avatar_id: "my_avatar_v1"
display_name: "My Avatar"
base_asset_id: "vroid/sample_a"
metadata:
  author: "Agent Name"
```

---

## Feedback Loop Pattern

1. Write `spec.yaml` with initial parameters.
2. Run `seidr build spec.yaml --out output/ --json`
3. Examine `render_paths` — view the PNG images.
4. If renders reveal issues: update `spec.yaml` (hair color, eye color, proportions).
5. Repeat from step 2.

The Annáll record (`session_id`) preserves the lineage of each iteration.

---

## Error Codes

| Exit Code | Meaning |
|---|---|
| 0 | Full success |
| 1 | Build or compliance failure (see JSON errors array) |
| 2 | Invalid arguments |
| 3 | Internal error |

---

## MCP Alternative

If using MCP directly (e.g., via the Mjöll bridge):
```bash
# Start MCP server
python -m seidr_smidja.bridges.mjoll

# Tools available:
# seidr.build_avatar  — full forge pipeline
# seidr.inspect_vrm   — Gate compliance check only
```

---

*Seiðr-Smiðja v0.1 — Forge Worker Eldra Járnsdóttir*
