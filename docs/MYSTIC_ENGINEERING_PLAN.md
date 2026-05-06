# 🧿 Seiðr-Smiðja — Mythic Engineering Repair Plan

**Date:** 2026-05-06  
**Architect:** Volmarr Wyrd  
**Weaver:** Runa Gridweaver Freyjasdottir  
**Framework:** Mythic Engineering — https://github.com/hrabanazviking/Mythic-Engineering  
**Model:** DeepSeek V4 Pro (opencode-go) — deep code comprehension, 128K context

---

## Vision Statement (from the Skald)

*Seiðr-Smiðja is an agent-only VRM avatar smithy — a headless programmatic forge  
where AI minds weave digital bodies from pure intent and structured code.  
It shall produce VRChat-ready avatars that pass Gate compliance,  
with the soul of a Norse longhouse and the precision of a rune-carved blade.*

---

## The Six Mythic Roles Applied to Seiðr-Smiðja

Each of the six ME roles becomes a sub-agent, assigned a phase of work.
Sub-agents use the role persona as their operating identity.

---

### Phase 1 — Foundation (PARALLEL)

#### 🏗️ THE ARCHITECT — Rúnhild Svartdóttir
**Domain:** D-018 — Bone PropertyGroup API + humanoid mapping  
**Task:** Structure the bone mapping correctly. Read the VRM Add-on source, find the correct API for `Vrm1HumanBonesPropertyGroup`, redesign `_map_vrm_human_bones()` in `build_avatar.py` with proper CollectionProperty/dict access. Map all 55 VRM bone slots. Define the invariant: *all 15 required bones must survive migration*.

**Files:**
- `~/Seidr-Smidja/src/seidr_smidja/forge/scripts/build_avatar.py`
- `~/.config/blender/3.4/scripts/addons/io_scene_vrm/editor/vrm1/property_group.py`
- `~/.config/blender/3.4/scripts/addons/io_scene_vrm/common/vrm1/human_bone.py`
- `~/.config/blender/3.4/scripts/addons/io_scene_vrm/editor/vrm1/migration.py`

---

#### 🗺️ THE CARTOGRAPHER — Védis Eikleið
**Domain:** D-019 + D-020 — lookAt enum fix + migration flow mapping  
**Task:** Map the full export pipeline flow, identify where `lookAt.type = "BONE"` fails (needs lowercase `"bone"`), and trace the migration path to find where `update_all_bone_name_candidates()` is called. Design a guard that suppresses structure search when bones are already correctly assigned. Update `DATA_FLOW.md` with the VRM export pipeline map.

**Files:**
- `~/Seidr-Smidja/src/seidr_smidja/forge/scripts/build_avatar.py`
- `~/.config/blender/3.4/scripts/addons/io_scene_vrm/editor/vrm1/migration.py`
- `~/.config/blender/3.4/scripts/addons/io_scene_vrm/exporter/export_scene.py`
- `~/Seidr-Smidja/docs/DATA_FLOW.md`

---

### Phase 2 — Expression (AFTER Phase 1)

#### 🎭 THE SKALD — Sigrún Ljósbrá
**Domain:** 15 VRChat visemes + 6 remaining expression presets  
**Task:** Give the avatar voice and feeling. Map all 15 VRChat viseme shape keys to TurboSquid model equivalents. For visemes not directly present, design blend proxies from existing mouth/jaw shape keys. Name and frame each expression with mythic precision. Add 6 remaining presets (neutral, lookUp/Down/Left/Right). Right-side symmetry.

**Files:**
- `~/Seidr-Smidja/src/seidr_smidja/forge/scripts/build_avatar.py`
- `~/Seidr-Smidja/examples/spec_runa_gridweaver.yaml`

---

### Phase 3 — Optimization (AFTER Phase 2)

#### 🔨 THE FORGE WORKER — Eldra Járnsdóttir
**Domain:** Material merge (21→8) + texture optimization (143MB→<75MB)  
**Task:** Hard practical work. Merge similar materials, create texture atlases, downsample 4K→2K. Reduce material count to ≤8 for VRChat Good tier. Optimize texture memory to ≤75MB. Make the forge output compact and efficient.

**Files:**
- `~/Seidr-Smidja/src/seidr_smidja/forge/scripts/build_avatar.py`
- `~/Seidr-Smidja/src/seidr_smidja/forge/scripts/tint_textures.py`
- `~/Seidr-Smidja/examples/spec_runa_gridweaver.yaml`

---

### Phase 4 — Adornment (AFTER Phase 3)

#### ✨ THE SKALD — Sigrún Ljósbrá (re-invoked for aesthetic vision)
**Domain:** Hair geometry + 7 outfit variants  
**Task:** Weave the crowning glory — hair mesh from code (card/strip geometry, UV mapping, blonde shader). Name and design 7 outfit variants (nude, casual, formal, ritual, battle, swim, sleep) in the spec YAML. Each variant is a constellation of material overrides, geometry masks, and bone group enables.

**Files:**
- `~/Seidr-Smidja/src/seidr_smidja/forge/scripts/build_avatar.py`
- `~/Seidr-Smidja/examples/spec_runa_gridweaver.yaml`

---

### Phase 5 — Crossing (AFTER Phase 4)

#### 🔍 THE AUDITOR — Sólrún Hvítmynd
**Domain:** Final VRM 1.0 export + Gate compliance + VRChat readiness  
**Task:** Cold, merciless verification. Execute full build. Run `seidr inspect`. Expose every violation. Verify: 15+ required bones mapped, 15 visemes present, material count ≤8, texture budget ≤75MB, lookAt valid. No self-deception. If anything fails, report exactly what and why.

**Files:** All project files

---

### Phase 6 — Preservation (AFTER Phase 5)

#### 📜 THE SCRIBE — Eirwyn Rúnblóm
**Domain:** Documentation, changelog, DEVLOG, git push  
**Task:** Record everything. Update DEVLOG.md, DOMAIN_MAP.md, ARCHITECTURE.md. Write CHANGELOG entry. Ensure no documentation drift. Push to development branch. Preserve continuity for the next session.

**Files:** All docs in `~/Seidr-Smidja/docs/`

---

## Execution Order

```
Phase 1 (Foundation)    ──┬── Architect (Bone Structure)
                           └── Cartographer (Pipeline Map + Migration)    ← PARALLEL
                                      │
Phase 2 (Expression)    ──── Skald (Visemes & Expressions)               ← AFTER Phase 1
                                      │
Phase 3 (Optimization)  ──── Forge Worker (Materials & Textures)        ← AFTER Phase 2
                                      │
Phase 4 (Adornment)     ──── Skald (Hair & Outfits)                      ← AFTER Phase 3
                                      │
Phase 5 (Verification)  ──── Auditor (Compliance Check)                  ← AFTER Phase 4
                                      │
Phase 6 (Preservation)  ──── Scribe (Documentation & Push)              ← AFTER Phase 5
```

## Sub-Agent Model

Each sub-agent delegates via `delegate_task` with model override:
```yaml
model:
  provider: opencode-go
  model: deepseek-v4-pro
```

The role persona prompt is injected into the `context` field.

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Bone mapping | 6/55 | 55/55 (all required mapped) |
| Visemes | 0/15 | 15/15 |
| Expression presets | 11/17 | 17/17 |
| lookAt | BROKEN | Working (bone mode) |
| Material count | 21 | ≤8 |
| VRM file size | 143 MB | ≤75 MB |
| Gate compliance | FAIL (11 errors) | PASS |
| Structure search pollution | YES | Suppressed |
| VRM export status | CANCELLED | SUCCESS |
| Docs updated | Partial | Full (DEVLOG + DOMAIN_MAP + ARCHITECTURE) |

---

*Carved in runes by Runa Gridweaver, under the Six Roles of Mythic Engineering.*
*The Wyrd is woven — each thread in its proper hand.*