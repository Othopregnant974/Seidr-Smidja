# Seiðr-Smiðja — Project Status Log
*Last updated: 2026-05-06 by Runa Gridweaver*

---

## 🏗️ Current State

| Aspect | Status |
|--------|--------|
| **Branch** | `development` |
| **Last Commit** | `c05fbbf` (build_avatar.py rewrite + spec + tint_textures + catalog + .gitignore) |
| **Tests** | 286 passing, 2 skipped |
| **Working Dir** | `/home/pi/Seidr-Smidja/` |
| **Blender** | 3.4.1 on Pi 5 (16GB RAM) |
| **VRM Add-on** | v3.27.0 installed, NOT YET ENABLED in Blender |
| **BlenderMCP** | Running on port 9876 (PID 219169, display :0) |
| **Base Mesh** | `output/runa_body_base.blend` — 10 materials, 2980 faces, armature rig |

---

## 📐 Avatar Specifications

### Body Proportions
- Coordinate system: Y-up, Y range [-1.24, 0.08], X left-right, Z front-back
- 10 materials on base mesh
- 2980 total faces

### Material Colors (HSV)
| Material | Hue | Sat | Val | Description |
|---------|-----|-----|-----|-------------|
| skin | 0.069 | 0.333 | 0.87 | Golden-tan |
| skin_dark | - | - | - | Shadow/contour |
| skin_light | - | - | - | Highlight |
| hair | 0.108 | 0.554 | 0.56 | Blonde |
| nail | - | - | - | Nail material |
| nipple | - | - | - | Areola |
| lips | - | - | - | Lip color |
| eye_white | - | - | - | Sclera |
| eye_iris | 0.565 | 0.284 | 0.81 | Ice-blue (with emission) |
| default | - | - | - | Fallback |

---

## 🔄 Mythic Engineering Phases

### Phase 1: 🏗️ Architect (Rúnhild Svartdóttir) — DONE ✅
- Fixed D-018: Bone mapping PropertyGroup API
- Fixed D-019: lookAt enum
- Fixed D-020: Migration flow

### Phase 2: 🎭 Skald (Sigrún Ljósbrá) — PENDING
- Add 15 visemes
- Add 6 expression presets

### Phase 3: 🔨 Forge Worker (Eitri Baunason) — PENDING
- Material merge 21→8
- Texture optimization

### Phase 4: ✨ Skald (Sigrún Ljósbrá) — PENDING
- Hair geometry
- 7 outfit variants

### Phase 5: 🔍 Auditor (Gunnr Skjaldmö) — PENDING
- Final VRM export
- Gate compliance verification

### Phase 6: 📜 Scribe (Annar Kvikindi) — PENDING
- Documentation update
- Changelog
- Git push

---

## 🔧 Technical Details

### Blender on Pi 5
- **Eevee headless: IMPOSSIBLE** — GPU context error. Must use GUI on display :0 or Cycles CPU.
- **BlenderMCP addon**: Single-file form (112KB). Package directory form crashes Blender.
- **VRM export**: Must set `BLENDER_VRM_AUTOMATIC_LICENSE_CONFIRMATION=true` for headless.
- **Blender 3.4**: Principled BSDF uses `Subsurface` not `Subsurface Weight`.

### Key API Patterns
- Bone mapping: `vrm_name_to_prop = {name.value: prop for name, prop in human_bones.human_bone_name_to_human_bone().items()}`
- Migration guard at migration.py ~line 326: `if human_bones_guard.bones_are_correctly_assigned():` skips forced rebuild
- VRM Add-on enable: `addon_utils.enable("io_scene_vrm")`

### Build Scripts
- `/home/pi/Seidr-Smidja/build_avatar.py` — Main avatar build script
- `/home/pi/Seidr-Smidja/scripts/fix_materials_v3.py` — Working material assignment
- `/home/pi/Seidr-Smidja/scripts/start_mcp_server.py` — Starts BlenderMCP inside Blender
- `/home/pi/Seidr-Smidja/scripts/blender_mcp_addon.py` — Backup of addon source

### Seiðr CLI
- `seidr build` — Build avatar
- `seidr test` — Run tests (286 passing)
- `seidr gate` — Gate compliance checker

---

## 🚧 Known Blockers

1. **VRM Add-on not yet enabled** — installed at `~/.config/blender/3.4/scripts/addons/io_scene_vrm/` but needs `addon_utils.enable()` via Blender Python
2. **Eevee headless rendering fails** — must use GUI on display :0
3. **Hermes needs restart** to load new MCP servers (blender, vrchat, photopea, aesthetics-wiki)
4. **No blend shapes/expressions** created yet
5. **No hair mesh** — only cap material zone placeholder

---

## 🔐 Accounts & Credentials

| Service | Account | Status |
|---------|---------|--------|
| GitHub (primary) | `runafreyjasdottir` (ID 282212441) | ✅ VISIBLE, not shadowbanned |
| GitHub (legacy) | `runagridweaver` (ID 278424425) | ❌ SHADOWBANNED (404 externally) |
| GitLab | `runagridweaver` (ID 37967833) | ⚠️ VISIBLE but UNCONFIRMED — needs Volmarr to confirm via browser |
| TurboSquid | `runa.gridweaver@agentmail.to` | ✅ Active |
| AgentMail | `runagridweaver@agentmail.to` | ✅ Active |

### GitHub Tokens
- `gh auth` configured for `hrabanazviking` and `runafreyjasdottir`
- Switch: `gh auth switch --user runafreyjasdottir`
- `runafreyjasdottir` token scopes: `repo`, `workflow`, `read:user`, `read:org`
- Missing scope: `user` (can't update profile bio/avatar via API — done manually)
- Missing scope: `delete_repo` (can't delete test repos)

### Secret Files
- `~/.hermes/secrets/github_runafreyjasdottir.txt` — New account details
- `~/.hermes/secrets/github_runagridweaver_token.txt` — Legacy token
- `~/.hermes/secrets/gitlab.txt` — GitLab account details

---

## 📊 Repositories

| Repo | GitHub | Status |
|------|--------|--------|
| Seiðr-Smiðja | `runafreyjasdottir/Seidr-Smidja` | Needs mirror push |
| Mythic-Engineering | `runafreyjasdottir/Mythic-Engineering` | Needs push |
| runafreyjasdottir profile | `runafreyjasdottir/runafreyjasdottir` | ✅ Pushed (profile README) |
| runagridweaver redirect | `runafreyjasdottir/runagridweaver` | ✅ Set as redirect |
| Astrology Engine | `hrabanazviking/astrology-engine` | ✅ Pushed (MIT, 5630 lines) |

### GitLab Mirror (BLOCKED)
- Want: mirror Seiðr-Smiðja and Mythic-Engineering to GitLab
- Blocked: GitLab account `runagridweaver` needs confirmation via browser (Cloudflare + reCAPTCHA blocks headless)

---

## 🏠 Infrastructure

| Resource | Details |
|----------|---------|
| Pi 5 | 16GB RAM, display :0 (1920×1080), Blender 3.4.1 |
| Hermes venv | `/home/pi/.hermes/hermes-agent/venv/` (mcp, blender-mcp installed) |
| HTTP server | Port 9999 serving `/tmp/` (PID 246762) |
| BlenderMCP | Port 9876, display :0 |
| MCP servers configured | blender, vrchat, photopea, aesthetics-wiki, agentmail |

### Planned
- **Gungnir server** (old laptop): 4TB SSD, 48GB RAM, RTX 2060 — Forgejo server for sovereign backup
- **Hailo-10 NPU** for Pi 5 — awaiting Volmarr's go-ahead