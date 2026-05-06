# 🧿 Seiðr-Smiðja — Mystic Engineering Repair Plan

**Date:** 2026-05-06  
**Architect:** Volmarr Wyrd  
**Weaver:** Runa Gridweaver Freyjasdottir  
**Model:** DeepSeek V4 Pro (opencode-go) — chosen for deep code comprehension + long context

---

## The Six Mystic Sub-Agents

Each agent is a Nornir-sphere — a domain of responsibility carved from the Wyrd.
They work in phase order: foundation first, then expression, then optimization, then crossing.

### 🦴 1. HUGINN — Bone Architecture (Thought)
*The Raven of Bone-Mapping — fixes what supports all else*

**Domain:** D-018 — Correct VRM humanoid bone mapping via PropertyGroup API  
**Phase:** 1 (Foundation — must complete first)  
**Task:** Read VRM Add-on `property_group.py` and `human_bone.py` source. Find the correct API for 
setting individual bone properties on the `Vrm1HumanBonesPropertyGroup`. Rewrite 
`_map_vrm_human_bones()` in `build_avatar.py` to map all 55 VRM humanoid bone slots 
using the correct CollectionProperty/dict access pattern. Test that bone assignments 
survive the migration pass.

**Files:** `build_avatar.py`, `~/.config/blender/3.4/scripts/addons/io_scene_vrm/editor/vrm1/property_group.py`, 
`~/.config/blender/3.4/scripts/addons/io_scene_vrm/common/vrm1/human_bone.py`

---

### 👁️ 2. MUNINN — Memory & Migration (Recall)
*The Raven of Configuration — fixes what remembers and what forgets*

**Domain:** D-019 + D-020 — lookAt enum case fix + migration structure search suppression  
**Phase:** 1 (Foundation — parallel with Huginn)  
**Task:** 
- Fix `lookAt.type = "BONE"` → `"bone"` (lowercase VRM 1.0 enum)
- Patch `migration.py` to skip `update_all_bone_name_candidates()` when bones are already manually assigned 
  (check `bones_are_correctly_assigned()` before running structure search)
- Or: find a way to set the addon migration version high enough that the migration path skips entirely

**Files:** `build_avatar.py`, `~/.config/blender/3.4/scripts/addons/io_scene_vrm/editor/vrm1/migration.py`

---

### 🎭 3. FREYJA'S MASK — Expression & Viseme (Seiðr)
*The Lady of Lip and Eye — gives the avatar voice and feeling*

**Domain:** All 15 VRChat visemes + 6 remaining expression presets  
**Phase:** 2 (Expression — after Huginn completes)  
**Task:**
- Map all 15 VRChat viseme shape keys (aa, ih, ou, ee, oh, PP, FF, TH, DD, kk, CH, SS, nn, RR, E) 
  to TurboSquid model shape keys
- Add 6 remaining expression presets: neutral, lookUp, lookDown, lookLeft, lookRight
- For visemes not directly present in TurboSquid model, create blend shape proxies from 
  existing mouth/jaw shape keys
- Right-side symmetry for all bilateral expressions

**Files:** `build_avatar.py`, `examples/spec_runa_gridweaver.yaml`

---

### 🔨 4. SINDRI'S FORGE — Material Transmutation (Smiðr)
*The Dwarf-Smith of Optimization — reduces, refines, hardens*

**Domain:** Material merging (21→8) + texture optimization (143MB→<75MB)  
**Phase:** 3 (Optimization — after Phase 2 completes)  
**Task:**
- Analyze 21 TurboSquid materials, design merge strategy: combine similar materials 
  (all skin variants → 1, all eye materials → 1, etc.)
- Create material atlas script: merge textures into atlases where appropriate
- Downsample textures: 4K→2K for body, 2K→1K for details
- Target: ≤8 material slots, ≤75MB total texture memory
- Update VRM material properties for each merged material

**Files:** `build_avatar.py`, `tint_textures.py`, `examples/spec_runa_gridweaver.yaml`

---

### 🌾 5. SIF'S CROWN — Hair & Adornment (Gullveig)
*Golden-Haired — weaves the crowning glory*

**Domain:** Hair geometry + 7 outfit variants  
**Phase:** 4 (Adornment — after Phase 3)  
**Task:**
- Build hair mesh from code: card/strip geometry with UV mapping for hair texture
- Create hair shader (blonde HSV target: hue=0.108, saturation=0.554, value=0.56)
- Define 7 outfit variant system in spec YAML: nude, casual, formal, ritual, battle, swim, sleep
- Each variant specifies: material overrides, geometry masks, bone group enables
- Hair must deform with head bone in the armature

**Files:** `build_avatar.py`, `examples/spec_runa_gridweaver.yaml`

---

### 🌉 6. HEIMDALLR'S GATE — Bridging & Validation (Bifröst)
*The Watchman — ensures the crossing is clean and lawful*

**Domain:** Final VRM 1.0 export + Gate compliance + VRChat readiness  
**Phase:** 5 (Crossing — after all others)  
**Task:**
- Execute full build with all Phase 1-4 fixes applied
- Run `seidr inspect` on the exported VRM
- Fix any remaining compliance violations
- Verify all 15 required bones are mapped
- Verify all 15 visemes present
- Verify material count ≤8
- Verify texture budget ≤75MB
- Verify lookAt configuration valid
- Final `git push` to development branch

**Files:** `build_avatar.py`, all spec files, Gate compliance rules

---

## Phase Execution Order

```
Phase 1 (Foundation)  ──┬── Huginn (Bone Architecture)
                         └── Muninn (Config & Migration)     ← PARALLEL
                                    │
Phase 2 (Expression)  ──── Freyja's Mask (Visemes)          ← AFTER Phase 1
                                    │
Phase 3 (Optimization) ──── Sindri's Forge (Materials)       ← AFTER Phase 2
                                    │
Phase 4 (Adornment)   ──── Sif's Crown (Hair & Outfits)     ← AFTER Phase 3
                                    │
Phase 5 (Crossing)     ──── Heimdallr's Gate (Validation)    ← AFTER Phase 4
```

## Chosen Model: DeepSeek V4 Pro (opencode-go)

**Why:** DeepSeek V4 Pro has excellent code comprehension, long context window (128K), 
strong Python/Blender API understanding, and is available on the builder list. It excels 
at reading large codebases and producing correct patches — exactly what Mystic Engineering 
sub-agents need.

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

---

*Carved in runes by Runa Gridweaver, under the watch of the Nornir.*
*The Wyrd is woven — the threads shall hold.*