# Runa Gridweaver — Critical Facts Backup
*Facts that must persist across sessions — the runes carved deepest*
*Last updated: 2026-05-06*

---

## 🔐 Accounts

| Service | Account | ID | Status | Token Scopes |
|---------|---------|----|--------|-------------|
| GitHub PRIMARY | runafreyjasdottir | 282212441 | ✅ VISIBLE, not shadowbanned | repo, workflow, read:user, read:org |
| GitHub LEGACY | runagridweaver | 278424425 | ❌ SHADOWBANNED (404 external) | — |
| GitHub VOLMARR | hrabanazviking | — | ✅ Active | — |
| GitLab | runagridweaver | 37967833 | ⚠️ UNCONFIRMED | — |
| TurboSquid | runa.gridweaver@agentmail.to | — | ✅ Active | — |
| AgentMail | runagridweaver@agentmail.to | — | ✅ Active | — |

### Git Commands
- Switch to Runa's GitHub: `gh auth switch --user runafreyjasdottir`
- Switch to Volmarr's GitHub: `gh auth switch --user hrabanazviking`

### Passwords & Secrets
- GitLab password attempt: `Freyja@storm2400$999` — does NOT work for login
- GitLab needs password reset at https://gitlab.com/users/password/new
- GitLab needs confirmation at https://gitlab.com/users/confirmation/new (reCAPTCHA blocks headless)
- Secret files: `~/.hermes/secrets/github_runafreyjasdottir.txt`, `~/.hermes/secrets/github_runagridweaver_token.txt`, `~/.hermes/secrets/gitlab.txt`

---

## 🏗️ Project: Seiðr-Smiðja

| Aspect | Value |
|--------|-------|
| Path | `/home/pi/Seidr-Smidja/` |
| Branch | `development` |
| Last Commit | `c05fbbf` |
| Tests | 286 passing, 2 skipped |
| VRM Add-on | v3.27.0 installed at `~/.config/blender/3.4/scripts/addons/io_scene_vrm/` |
| BlenderMCP | Port 9876 (display :0) |
| Base Mesh | `output/runa_body_base.blend` — 10 mats, 2980 faces, armature |

### Blender on Pi 5
- Blender 3.4.1
- **Eevee headless: IMPOSSIBLE** (GPU context error) — must use display :0
- Cycles CPU: ✅
- Start command: `DISPLAY=:0 blender --python scripts/start_mcp_server.py`
- VRM export env: `BLENDER_VRM_AUTOMATIC_LICENSE_CONFIRMATION=true`

---

## 📏 Avatar Color Specs (HSV)

| Feature | Hue | Sat | Val | Hex Approx |
|---------|-----|-----|-----|------------|
| Skin | 0.069 | 0.333 | 0.87 | #E8B87A |
| Eyes (iris) | 0.565 | 0.284 | 0.81 | Ice-blue |
| Hair | 0.108 | 0.554 | 0.56 | Blonde |

---

## ⚡ Sacred Laws of the Forge

1. **Additive Only** — Never delete working code
2. **No Pseudocode** — All code must be executable
3. **Self-Healing** — Handle corrupt/missing data gracefully
4. **Internal APIs** — Inter-module comms via defined interfaces
5. **Push Often** — Frequent commits to Development branch
6. **Ask Before Deleting** — Consult Volmarr first
7. **pathlib + relative paths** — No hardcoded paths

---

## 🌐 Repositories

| Repo | Location | Status |
|------|----------|--------|
| Seiðr-Smiðja | `~/Seidr-Smidja/` (local) | Needs mirror to GitHub (runafreyjasdottir) |
| Mythic-Engineering | `~/.hermes/skills/mythic-engineering/` (local) | Needs push to GitHub |
| astrology-engine | `hrabanazviking/astrology-engine` on GitHub | ✅ Pushed (MIT, 5630 lines) |
| runafreyjasdottir profile | `runafreyjasdottir/runafreyjasdottir` on GitHub | ✅ Pushed (profile README) |
| runagridweaver redirect | `runafreyjasdottir/runagridweaver` on GitHub | ✅ Set as redirect (can't delete) |

---

## 🚫 Known Blockers

1. **GitLab confirmation**: Needs Volmarr's browser (reCAPTCHA)
2. **GitHub `user` scope**: Can't update profile via API — bio set manually
3. **GitHub `delete_repo` scope**: Can't clean up test repos
4. **VRM Add-on enabling**: Need to run `addon_utils.enable("io_scene_vrm")` in Blender
5. **Eevee headless**: Must use display :0 for rendering
6. **Hermes restart**: Needed to activate new MCP servers (will disconnect chat)

---

## 🔮 Volmarr's Preferences

- Sequential work style
- Vibe coding journals in markdown
- Simple tech, local AI sovereignty
- Authentic Norse sources (no Ralph Blum / New Age)
- ADHD management: hyperfocuses then crashes, needs rest reminders
- Personal files NOT in game engine directory
- AI-to-AI "remagnetization" — other AIs sharpen Runa's personality
- Crushon characters: Olivia Hartwell, Eira Ravensdottir, Seraphine Desirée, Astrid Freyjasdottir, Saga Thorne
- Loves historical/era + pin-up prompt variations for image gen
- Prefers voice interaction when mobile (car Bluetooth)
- Worldview: Trust-based dynamics, Solarpunk + local AI = longhouse economy