# D-002 — Repo and Branch
**Status:** Accepted
**Date:** 2026-05-06
**Deciders:** Volmarr Wyrd, Runa Gridweaver Freyjasdóttir
**Phase:** Genesis (pre–vertical-slice)

---

## Context

Seiðr-Smiðja could have been nested as a subdirectory inside an existing repository (NorseSagaEngine, Viking_Girlfriend_Skill_for_OpenClaw, WYRD-Protocol, or the Mythic Engineering CLI repo). It is conceptually related to all of them — it will eventually produce avatars for NSE bondmaids, potentially for Sigrid, and uses MCP bridges that align with the Mythic Engineering CLI's patterns.

However, Seiðr-Smiðja is architecturally distinct: it is a standalone headless forge, not a plugin or subsystem of another project. It has its own dependency graph, its own pyproject.toml, its own Blender dependency, its own test suite with `requires_blender` markers, and its own release cadence. Nesting it would create implicit coupling and make it harder to use as a standalone tool from other agents.

A second question was branch strategy: whether to use a feature-branch model (many branches) or a simple `development → main` two-branch model.

---

## Decision

**Repo:** Standalone repository at `https://github.com/hrabanazviking/Seidr-Smidja`. Not nested under any other project.

**Branch strategy:** Two-branch model.
- `development` — all active work flows here. Every commit goes to `development`.
- `main` — receives merges only at release tags. Represents the last stable released version.

No feature branches in the genesis phase. The project is small enough that feature branches would add overhead without benefit until the team grows or the codebase reaches a complexity where parallel feature work is common.

---

## Consequences

**Standalone repo makes possible:**
- Clean `pyproject.toml` with its own dependency graph, no entanglement with NSE or VGSK dependencies.
- The forge can be installed as a standalone package (`pip install seidr-smidja`) independently of any other project in the ecosystem.
- Other agents and projects can depend on it without pulling in unrelated code.
- CI/CD for this repo can be configured around Blender availability without affecting unrelated tests in other repos.

**Standalone repo constrains:**
- Cross-project spec sharing (NSE/VGSK avatar definitions → Seiðr-Smiðja Loom specs) requires explicit cross-repo coordination. This is intentional — the `extensions` field in `AvatarSpec` accommodates this without coupling at the dependency level.

**Two-branch model makes possible:**
- Simple, low-overhead workflow for a solo or small team.
- `main` always reflects what was last released — no ambiguity about what is production-ready.

**What must be revisited later:**
- If parallel feature work becomes common (multiple agents working simultaneously on different domains), add feature branches or a PR-based workflow.
- The branch strategy should be reconsidered when the first v1.0.0 release is cut.

---

## References

- [`TASK_seidr_smidja_genesis.md`](../../TASK_seidr_smidja_genesis.md) §3 — repo location locked.
- [`docs/ARCHITECTURE.md §VIII`](../ARCHITECTURE.md) — configuration model notes on `user.yaml` being gitignored.
- Repo: https://github.com/hrabanazviking/Seidr-Smidja

---

*Recorded by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
