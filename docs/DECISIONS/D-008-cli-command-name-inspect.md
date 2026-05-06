# D-008 — CLI Command Name: `seidr inspect` (Canonical)
**Status:** Accepted
**Date:** 2026-05-06
**Deciders:** Volmarr Wyrd, Runa Gridweaver Freyjasdóttir
**Phase:** Genesis closing — AUDIT-003 ratification

---

## Context

The Architect's original CLI contract in `src/seidr_smidja/bridges/INTERFACE.md` documented the existing-VRM-compliance command as `seidr check <vrm_file>`. The Forge Worker, while implementing the Rúnstafr CLI in `src/seidr_smidja/bridges/runstafr/cli.py`, registered the command as `seidr inspect <vrm_path>` — same purpose, different verb.

The Auditor flagged this in **AUDIT-003** (Medium) as a contract/implementation drift requiring Volmarr's ratification: was the rename intentional, and which name is canonical going forward?

The Auditor wrote `src/seidr_smidja/bridges/INTERFACE_AMENDMENT_2026-05-06.md` documenting the divergence and asking for the decision.

---

## Decision

**`seidr inspect` is the canonical command name.** The implementation in `bridges/runstafr/cli.py` stands. The contract documentation is reconciled to the implementation, not the other way around.

The semantic intent of `inspect` is preferred: neutral examination of a VRM file. `check` was considered and declined as more judgmental than the agent-facing semantics warrant; the Gate's pass/fail judgment is performed during `seidr build`, while `seidr inspect` is a non-mutating diagnostic.

This decision is **partial closure** of AUDIT-003. Two related sub-items remain open and are deferred to v0.1.1:

1. **`seidr list-assets`** — documented in INTERFACE.md but not implemented in the CLI. The REST bridge (Straumur) exposes the equivalent `GET /v1/assets`. Decision deferred: implement in CLI for parity, or remove from the contract. Carried forward as a v0.1.1 line item.

2. **`seidr bootstrap-hoard`** — implemented but undocumented in INTERFACE.md. Per the additive-only rule, the next INTERFACE revision should add it; meanwhile the amendment file documents it.

---

## Consequences

**What becomes possible:**
- The CLI command surface is now contractually settled for `inspect`. No further renaming churn for this command in v0.1.x.
- `bridges/INTERFACE.md` can be brought into alignment with the implementation in a future scheduled revision (additive, with the original line preserved per the additive-only rule).
- Skill manifests and agent documentation can confidently reference `seidr inspect` as the stable verb.

**What becomes constrained:**
- The verb `check` is no longer available for a different command without causing confusion. If a future feature needs that semantic, it should pick a new word (e.g. `verify`, `audit`).

**What must be revisited later:**
- `seidr list-assets` decision (implement in CLI vs. remove from contract). Tracked as v0.1.1 line item.
- `seidr bootstrap-hoard` formal addition to the INTERFACE contract.
- A general INTERFACE.md revision to fold all four amendment files into the canonical contract — done additively, not by deletion.

---

## References

- `src/seidr_smidja/bridges/INTERFACE.md` — original contract (preserved unchanged per additive-only rule).
- `src/seidr_smidja/bridges/INTERFACE_AMENDMENT_2026-05-06.md` — Auditor's amendment documenting the divergence; this ADR ratifies it.
- `src/seidr_smidja/bridges/runstafr/cli.py` — actual command registration.
- `docs/AUDIT_GENESIS.md` — AUDIT-003 finding.
- `docs/DEVLOG.md` — Phase 7 closing entry and 2026-05-06 ratification stamp.

---

*Ratified by Volmarr Wyrd on 2026-05-06, the day after the genesis ritual closed.*
