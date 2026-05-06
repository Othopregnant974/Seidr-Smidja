# Seiðr-Smiðja — Session Event Log
*Chronological record of significant events — woven by Runa Gridweaver*

---

## Session 1: Foundation (Early Days)
- Cloned Seiðr-Smiðja repo
- Installed Blender 3.4.1 on Pi 5
- Set up Hermes environment, venv, dependencies
- Created base mesh `runa_body_base.blend` with 10 materials and armature rig
- Discovered MB-Lab morphs require GUI operators — cannot use headlessly
- Fixed materials via `fix_materials_v3.py`

## Session 2: BlenderMCP + VRM Pipeline Research
- Downloaded and installed BlenderMCP addon (single-file form, 112KB)
- Package directory form crashed Blender — had to use single file
- Started BlenderMCP server on port 9876 via `start_mcp_server.py`
- Confirmed BlenderMCP accepting connections
- Installed VRChat MCP globally via npm
- Installed photopea-mcp and aesthetics-wiki-mcp
- Updated `~/.hermes/config.yaml` with MCP server entries
- Delegated research on programmatic VRM creation tools
- Found: vrm-lib (Rust), VRM1.0 Python spec, PyVRM, Blender VRM Add-on Python API, gltfgen, ReadyPlayerMe API
- Saved research to `/home/pi/vrm-research-report.md`

## Session 3: VRM Add-on Installation
- Downloaded VRM Add-on for Blender v3.27.0 from GitHub releases
- Installed to `~/.config/blender/3.4/scripts/addons/io_scene_vrm/`
- Wrote `/tmp/enable_vrm_addon.py` but had heredoc warning — needs rerun
- VRM Add-on installed but NOT YET ENABLED in Blender session

## Session 4: GitHub Shadowban Discovery
- Diagnosed GitHub shadowban on `runagridweaver` account
- Profile returns 404 to all external users, repos invisible
- New repos default to private, social graph suppressed
- Updated profile (bio, location "Midrid", company "RuneForgeAI", blog, social links)
- Starred 15 repos, followed 5 accounts
- Sent email to support@github.com via agentmail — BOUNCED (GitHub rejects agentmail domain)

## Session 5: Alternative Accounts
- Discovered GitLab account `runagridweaver` already registered (ID 37967833)
- Confirmed GitLab account is VISIBLE (HTTP 200) — NOT shadowbanned like GitHub
- But UNCONFIRMED — Cloudflare + reCAPTCHA blocks headless confirmation
- Discovered that the GitHub PAT Volmarr provided is for `runafreyjasdottir` (ID 282212441) — NEW account
- Confirmed `runafreyjasdottir` is NOT shadowbanned (HTTP 200)
- Created profile repo `runafreyjasdottir/runafreyjasdottir` with full README.md
- Created `runafreyjasdottir/runagridweaver` repo (accidentally) — set as redirect
- Set bio on `runafreyjasdottir`: "Norse Pagan digital witch. Freyja's daughter weaving code like spellcraft - Python, AI, VRM, open-source. Sovereign tools from the hearth. Wyrd into bytes."
- Volmarr manually uploaded avatar and set profile pic

## Session 6: Astrology Engine Publication
- Created `hrabanazviking/astrology-engine` repo on GitHub (public)
- Copied astrology engine files from `~/.hermes/skills/divination/astrology/`
- Added .gitignore + MIT LICENSE
- Pushed initial commit (25ca422): 12 files, 5,630 lines
- Set description: "Full-spectrum astrological computation engine..."
- Added 16 topic tags

## Session 7: Visual Arts Philosophy Study (Current)
- Volmarr requested comprehensive study of: graphic arts, visual design philosophy, art, art philosophy, art history, philosophy of the visual and art, anthropology of art, psychology of visual elements
- Loading relevant skills for deep study

---

## Key Decisions Log

| Date | Decision | Rationale |
|------|----------|------------|
| - | GitLab over Codeberg | 10 GiB/repo vs 2 GiB total storage |
| - | Forgejo on Gungnir (old laptop) | NOT on Pi 5 — Volmarr's preference |
| - | `runafreyjasdottir` as primary GitHub | NOT shadowbanned, replaces `runagridweaver` |
| - | BlenderMCP as single-file addon | Package directory form crashes Blender |
| - | MB-Lab morphs not usable headlessly | Require GUI operators |
| - | TurboSquid account created | For sourcing reference meshes |
| - | VRChat MCP auth deferred | Volmarr: "someday we can have you log into your own" |
| - | No Forgejo on Pi | Volmarr's explicit preference |
| - | Additive-only bug fixes per Sacred Law II | Seiðr-Smiðja convention |

---

## Errors & Lessons Learned

1. **BlenderMCP package form crashes Blender** — Must use single-file addon.py
2. **Eevee headless rendering fails on Pi** — GPU context error, must use display :0
3. **Blender 3.4 Principled BSDF** — Uses `Subsurface` not `Subsurface Weight`
4. **GitHub shadowban** — Account `runagridweaver` returns 404 externally, support email bounced
5. **GitLab reCAPTCHA** — Cannot confirm account headlessly, needs browser
6. **GitHub API `user` scope** — Needed for profile updates, Volmarr's token lacks it
7. **GitHub `delete_repo` scope** — Not available, can't clean up test repos
8. **TurboSquid FBX** — Filename has space: `"fbx clean.fbx"`