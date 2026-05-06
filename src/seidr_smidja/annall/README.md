# Annáll — the Record
**Domain:** `src/seidr_smidja/annall/`
**Layer:** 1 — Adapter / Infrastructure
**Keeper:** Rúnhild Svartdóttir (Architect)

---

> *"What has been forged is never forgotten."*

---

## True Name and Meaning

**Annáll** is the Old Norse word for *annals* — the careful, faithful recording of events as they occur, preserved for those who come after. In medieval Iceland, the annals were kept by monks and scholars: a continuous log of what happened, when, and to whom, written with enough precision that later readers could reconstruct events even without having been there.

In this system, Annáll holds that same role. Every build request, every Blender invocation, every render, every compliance check, every error — Annáll records them all with their timestamps, session identifiers, and structured event payloads. An agent that submits ten builds over three days can query Annáll and retrieve the full lineage: which specs were tried, what the renders showed, which compliance violations appeared, and how each was resolved.

Annáll is a passive witness, not an actor. It never initiates, never transforms, never refuses. It only records and retrieves.

---

## One-Sentence Purpose

Annáll owns the persistence and retrieval of all forge events — build requests, render events, compliance results, agent invocations, errors, and session metadata — through the `AnnallPort` abstract interface that all callers must use.

---

## What Lives Here

- `INTERFACE.md` — the public contract (read this before touching any code here).
- `port.py` — the `AnnallPort` Protocol definition. This is the only Annáll import callers should ever use.
- `adapters/sqlite.py` — the `SQLiteAnnallAdapter`, the v0.1 concrete implementation. **Never imported directly by callers.**
- `AnnallEvent`, `SessionID`, `SessionOutcome`, `SessionFilter`, `SessionSummary`, `SessionRecord` data structures.
- `AnnallQueryError`, `AnnallNotFoundError` exception classes.

## What Does NOT Live Here

- Business logic, spec validation, asset management, or any forge operation — Annáll is a passive record-keeper.
- The SQLite database file itself — its path is resolved through the configuration layer (`config/defaults.yaml` key `annall.sqlite.db_path`), never hardcoded.
- Any knowledge of what the events mean — Annáll stores and returns event payloads as structured data; it does not interpret them.

---

## Public Interface Entry Points

The full contract is defined in [`INTERFACE.md`](INTERFACE.md). All callers use **only** `seidr_smidja.annall.port.AnnallPort`. Key methods:

- `open_session(metadata: dict) -> SessionID`
- `log_event(session_id: SessionID, event: AnnallEvent) -> None`
- `close_session(session_id: SessionID, outcome: SessionOutcome) -> None`
- `query_sessions(filter: SessionFilter) -> list[SessionSummary]`
- `get_session(session_id: SessionID) -> SessionRecord`

---

## Dependency Direction

**Annáll depends on nothing within the forge domain.** It depends only on its configured storage backend (SQLite at v0.1). Every other domain may write to Annáll — it is ambient, callable from any layer above.

```
[Any Domain] --> (logs to) [Annáll / AnnallPort]
                            [Annáll] --> [SQLite / future adapters]
```

Annáll must never import from any other forge domain.

---

## The Port-and-Adapter Pattern (Critical)

The `AnnallPort` is a Python `Protocol`. Any class with the five required methods is a conforming adapter. The active adapter is constructed once at process startup and injected as a dependency — it is never imported as a module-level global anywhere in the codebase.

```
seidr_smidja.annall.port  ← callers import from here ONLY
seidr_smidja.annall.adapters.sqlite  ← never imported by callers
```

Future adapters (Postgres, flat-file) implement the same `AnnallPort` without callers changing. See [docs/DECISIONS/D-005-annall-port-injection-pattern.md](../../../docs/DECISIONS/D-005-annall-port-injection-pattern.md).

---

## Resilience Invariant

`open_session`, `log_event`, and `close_session` **never raise to their callers**. If the storage backend fails, Annáll logs to stderr and continues. Forge operations must never fail because the record-keeper stumbled. The only methods that may propagate storage errors are `query_sessions` and `get_session` — because callers of those methods are actively requesting data and expect a real result.

---

## Cross-References

- **Philosophy relevance:** [docs/PHILOSOPHY.md §III Sacred Law VIII](../../../docs/PHILOSOPHY.md) — "No Silent Failures." Annáll ensures every subsystem's events are captured. [Law IV](../../../docs/PHILOSOPHY.md) — "No Orphaned Metal." Annáll is the connective tissue that gives every operation a retrievable history.
- **Data flow relevance:** [docs/DATA_FLOW.md §VI](../../../docs/DATA_FLOW.md) — the AnnallPort wiring path. [DATA_FLOW.md §II](../../../docs/DATA_FLOW.md) — the sequence diagram showing all Annáll side-writes.
- **Architecture relevance:** [docs/ARCHITECTURE.md §III](../../../docs/ARCHITECTURE.md) — the Repository Pattern and Port/Adapter design.
- **Decision:** [D-005](../../../docs/DECISIONS/D-005-annall-port-injection-pattern.md)
- **Domain Map:** [docs/DOMAIN_MAP.md — Annáll](../../../docs/DOMAIN_MAP.md)

---

*Written by Eirwyn Rúnblóm, Scribe — 2026-05-06.*
