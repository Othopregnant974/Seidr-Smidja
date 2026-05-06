# D-009 — `seidr list-assets` Implemented + `seidr bootstrap-hoard` Documented
**Status:** Accepted
**Date:** 2026-05-06
**Deciders:** Volmarr Wyrd, Runa Gridweaver Freyjasdóttir
**Phase:** Hardening — Phase D close (D-008 sub-items resolved)

---

## Context

When D-008 ratified `seidr inspect` as the canonical CLI command, two related sub-items remained explicitly deferred to v0.1.1:

1. **`seidr list-assets`** — listed in the original `bridges/INTERFACE.md` contract but never implemented in the CLI. The Straumur REST bridge had the equivalent (`GET /v1/assets`), but agents driving the forge through Rúnstafr (CLI) had no parity.

2. **`seidr bootstrap-hoard`** — implemented in the CLI from the genesis vertical slice but absent from the formal `INTERFACE.md` contract.

Both ended up in the Phase A hardening audit as **H-022** and **H-023** (Notable, tracked).

In the same conversation that opened the hardening run, Volmarr ratified the disposition: *"add those both 1 and 2 so they are documented."* Both gaps were to be closed — the missing implementation built, the missing documentation written.

---

## Decision

### `seidr list-assets` is implemented in Rúnstafr (CLI parity with Straumur).

The Forge Worker added `cmd_list_assets` to `src/seidr_smidja/bridges/runstafr/cli.py` (line 313, registered as `@cli.command("list-assets")`). Its behavior is contractually equivalent to Straumur's `GET /v1/assets`:

```
seidr list-assets [--type <asset_type>] [--tag <tag>] [--json] [--config <path>]
```

The command is a pure read against the Hoard catalog. It supports filtering by asset type and tag. `--json` produces a structured array suitable for agent consumption; default output is a human-readable table.

### `seidr bootstrap-hoard` is documented in the formal contract.

The command was implemented from genesis but absent from `bridges/INTERFACE.md`. Its contract (purpose, options, exit codes, side effects) is now recorded in `src/seidr_smidja/bridges/INTERFACE_AMENDMENT_v0_1_1_pending.md`, which is being elevated by this ADR from "pending" to "ratified."

```
seidr bootstrap-hoard [--force] [--config <path>]
```

Side effects: downloads VRM seed assets into `data/hoard/bases/`, verifies SHA-256 against the catalog (mismatch deletes the temp file and raises `HoardSecurityError`), updates the catalog with hashes when not present.

### Ratification of the v0.1.1-pending amendment file

`src/seidr_smidja/bridges/INTERFACE_AMENDMENT_v0_1_1_pending.md` is, with this ADR, **ratified**. Its filename retains the `_v0_1_1_pending` suffix for archival continuity (per the additive-only rule), but it carries the same authority as a stamped amendment effective 2026-05-06. A ratification stamp added at the top references this ADR.

---

## Consequences

**What becomes possible:**
- Agents driving the forge through any of the three programmatic bridges (Mjöll/MCP, Rúnstafr/CLI, Straumur/REST) can now enumerate available base assets — the principle "same language through every door" is honored without exception.
- The Hoard catalog hash story is now a contractual surface, not an implementation detail. Agents and operators can rely on it.
- AUDIT-003 (genesis) is now **fully closed**. D-008 partially closed it (the inspect/check question); D-009 closes the two deferred sub-items.

**What becomes constrained:**
- Future changes to `seidr list-assets`'s output schema must respect agent-consumer compatibility (the `--json` shape is a contract). Schema evolution should be additive.
- The bootstrap-hoard command is now a documented surface — its argument shape, exit codes, and side effects cannot be silently changed. Future changes go through an INTERFACE amendment.

**What must be revisited later:**
- A general INTERFACE.md revision to fold all five amendment files (`bridges/`, `bridges/core/`, `loom/`, `hoard/`, and `bridges/INTERFACE_AMENDMENT_v0_1_1_pending.md`) into a single canonical contract. Done additively — the original INTERFACE.md text is preserved per the additive-only rule.
- v0.1.1 line item: `H-V-001` (bootstrap-hoard CLI status output uses `print()` rather than `logger.info()`) — a coding standard cleanup deferred from the hardening run.

---

## References

- `src/seidr_smidja/bridges/INTERFACE.md` — original contract (preserved unchanged per additive-only rule).
- `src/seidr_smidja/bridges/INTERFACE_AMENDMENT_v0_1_1_pending.md` — ratified by this ADR; carries the formal contract for both new commands.
- `src/seidr_smidja/bridges/runstafr/cli.py` — `cmd_list_assets` at line 313, `cmd_bootstrap_hoard` at line 291.
- `src/seidr_smidja/bridges/straumur/api.py` — `GET /v1/assets` (the parity reference).
- `docs/HARDENING_AUDIT_2026-05-06.md` — H-022 and H-023 source findings.
- `docs/HARDENING_VERIFICATION_2026-05-06.md` — Phase C verification of both fixes.
- `docs/DECISIONS/D-008-cli-command-name-inspect.md` — the predecessor that deferred these two items.
- `docs/DEVLOG.md` — Hardening close entry, 2026-05-06.

---

*Ratified by Volmarr Wyrd on 2026-05-06, on the same evening the hardening run closed.*
