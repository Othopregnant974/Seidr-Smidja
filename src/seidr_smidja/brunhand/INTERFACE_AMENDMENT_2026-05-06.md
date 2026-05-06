# Brúarhönd — Interface Amendment
**Amendment date:** 2026-05-06
**Amends:** `INTERFACE.md`, `daemon/INTERFACE.md`, `client/INTERFACE.md`
**Reason:** Brúarhönd Phase 6 audit (B-013, B-014) — clarifications to security posture and primitive surface contract.
**Status:** **RATIFIED 2026-05-06.** Filed at the close of the Brúarhönd v0.1 feature ritual.
**Author:** Runa Gridweaver Freyjasdóttir, in the discipline of Eirwyn Rúnblóm (Scribe), closing Phase 7.

---

## 1. Bearer Token in YAML — Operator Warning (B-013)

The daemon's bearer token may be loaded from any of three sources, in priority order:

1. `BRUNHAND_TOKEN` environment variable (recommended).
2. `--token` command-line flag at daemon startup (acceptable for ephemeral hosts).
3. `brunhand.daemon.token` literal value in `config/user.yaml` (NOT RECOMMENDED).

**The third option carries operational risk.** A token-in-YAML lives on disk wherever the config file lives — accidental git commits, file backups, screen recordings, and shared screenshots can all leak it. The token is the inner layer of Brúarhönd's defense in depth (Tailscale ACL is the outer layer); leaking it through casual file-share gives an attacker who has reached the tailnet a clear path to GUI control of the host.

The daemon currently emits a `WARNING` log at startup when an inline YAML token is detected. **Operators should treat the warning as actionable.** Migrate to env var or stdin-prompt as soon as practical.

A future `--accept-inline-token` opt-in flag (currently a v0.1.1 line item) will make the daemon refuse to start with an inline YAML token unless the operator explicitly acknowledges the risk.

**Cross-references:**
- `docs/features/brunhand/TAILSCALE.md` — bearer token section.
- `docs/features/brunhand/AUDIT_BRUNHAND_2026-05-06.md` — finding B-013.

---

## 2. Hotkey Surface Contract — Pass-Through Without Allow-List (B-014)

The `hotkey` primitive (`POST /v1/brunhand/hotkey`) accepts an arbitrary key combination and presses it on the daemon's host. **The daemon does NOT maintain a forbidden-hotkey allow/deny list in v0.1.** This is an explicit and documented design choice: the hand has the same authority on the keyboard as the agent driving it.

**Implications operators must understand:**

- The agent CAN press `Ctrl+Alt+Del` (Windows secure attention sequence — typically intercepted by the OS and not actionable, but recorded).
- The agent CAN press `Alt+F4` (close active window) — including closing VRoid Studio mid-operation.
- The agent CAN press `Win+L` (Windows lock screen) — locking out the operator until they re-authenticate.
- The agent CAN press OS-level shortcuts that affect the entire desktop (e.g., `Cmd+Tab` on macOS, `Super+W` on Linux), losing VRoid Studio focus.
- The agent CAN press `F11` (fullscreen toggle), `Print Screen`, accessibility shortcuts, and any other key combination the OS recognizes.

**Why no allow-list in v0.1:**

A static allow-list would either be too permissive (allows dangerous combos to slip through) or too restrictive (blocks legitimate flows operators didn't anticipate). VRoid Studio's UI uses a wide range of standard and platform-specific shortcuts; an exhaustive allow-list would require a per-VRoid-Studio-version layout map (the same translation layer that v0.2 will introduce).

**Recommended operator discipline:**

- Run the daemon on a machine where the desktop session is dedicated to VRoid work.
- Use Tailscale ACL to limit which devices can reach the daemon.
- Use the bearer token to limit which agent identities can issue commands.
- Watch the daemon-side Annáll for unexpected hotkey patterns.
- Treat the Brúarhönd hand as having full keyboard authority equivalent to a person sitting at the machine.

**v0.2 candidates:** layout-aware allow-lists; opt-in forbidden-hotkey deny-lists; daemon-side dry-run mode that records intended keypresses without executing them.

**Cross-references:**
- `daemon/INTERFACE.md` — hotkey endpoint section.
- `docs/features/brunhand/AUDIT_BRUNHAND_2026-05-06.md` — finding B-014.
- `docs/features/brunhand/PHILOSOPHY_ADDENDUM.md` — The Hand Has Honest Limits.

---

## 3. Tengslastig `owns_client` Parameter (Phase 6.5 addition)

The `Tengslastig` (session container) constructor gained an `owns_client: bool = False` parameter in Phase 6.5 (B-011 fix). When `True`, `__exit__` calls `client.close()`. When `False` (default), the caller is responsible for the client's lifecycle.

This default protects existing factory paths (`make_session_from_config`) which already manage client lifecycle. Direct construction `Tengslastig(client=BrunhandClient(...), ...)` should pass `owns_client=True` to avoid leaking the httpx connection pool.

**Cross-reference:** `docs/features/brunhand/AUDIT_BRUNHAND_2026-05-06.md` — finding B-011.

---

*This amendment is additive. The original INTERFACE files are not modified. Future contract evolution should fold these clarifications into the canonical surface during a planned INTERFACE.md revision.*
