# Bridges — Interface Amendment
**Amendment date:** 2026-05-06
**Amends:** `INTERFACE.md` (same directory)
**Reason:** Auditor finding AUDIT-003 — CLI command names diverge from documented contract; undocumented command present.
**Author:** Sólrún Hvítmynd (Auditor), for Eirwyn Rúnblóm (Scribe) to ratify in Phase 7.

---

## Correction: Rúnstafr CLI Command Names

The INTERFACE.md documents the following commands:
```
seidr check <vrm_file> [--targets <target,...>]
seidr list-assets [--type <type>] [--tag <tag>]
```

The actual registered commands are:

### `seidr inspect <vrm_path>` (not `seidr check`)
Registered at `bridges/runstafr/cli.py:210` as `@cli.command("inspect")`.
Runs the Gate compliance check on an existing `.vrm` file.
Options: `--targets`, `--json`, `--config`.

The command was registered as `inspect` rather than `check`. Confirm with Volmarr whether this rename is intentional. If so, INTERFACE.md should be updated to reflect `seidr inspect`. If not, the implementation should be renamed.

### `seidr bootstrap-hoard` (undocumented)
Registered at `bridges/runstafr/cli.py:288`.
Downloads seed VRM assets into the Hoard.
Options: `--force`, `--config`.
This command is not listed in INTERFACE.md. It is a valid, wired command.

### `seidr list-assets` — NOT IMPLEMENTED in CLI
The INTERFACE.md documents `seidr list-assets [--type <type>] [--tag <tag>]` but this command does not exist in the CLI implementation. The REST bridge (`Straumur`) exposes an equivalent `GET /v1/assets` endpoint.

Resolution options (Forge Worker to decide with Volmarr):
- Implement `seidr list-assets` in the CLI (matching `GET /v1/assets` behavior).
- Remove `seidr list-assets` from the INTERFACE.md contract if it is not needed for v0.1.

---

## Claude Code Skill: SKILL.md vs manifest.yaml

INTERFACE.md line 99: `bridges/skills/claude_code/manifest.yaml`
Actual file: `bridges/skills/claude_code/SKILL.md`

The Claude Code skill is documented as a Markdown file (`SKILL.md`) rather than a YAML manifest. This is intentional: Claude Code agents invoke the forge via the `seidr` CLI (Rúnstafr), not via a YAML skill adapter. The SKILL.md provides human and agent-readable instructions for CLI invocation patterns. The filename should be reflected correctly in INTERFACE.md.

---

*This amendment is additive. The existing `INTERFACE.md` is not modified.*
*Scribe should fold this into the next INTERFACE.md revision when one is made.*
