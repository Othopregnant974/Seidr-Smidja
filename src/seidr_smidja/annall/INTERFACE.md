# Annáll — Interface Contract
**Last updated:** 2026-05-06
**Domain:** Annáll — the Record
**Keeper:** Rúnhild Svartdóttir (Architect)

---

## Purpose

Annáll is the memory, logging, and session-tracking layer. It records every forge event — build requests, renders, compliance results, agent invocations, and errors. All callers interact exclusively through the `AnnallPort` abstract interface. The concrete adapter (SQLite at v0.1) is never imported directly by any caller.

---

## The `AnnallPort` Interface

The `AnnallPort` is defined as a Python `Protocol` in `annall/port.py`. Any class that implements these five methods is a conforming adapter.

---

### `open_session(metadata: dict) -> SessionID`

Opens a new session record for a forge operation.

- **Input:** `metadata` — arbitrary dict with keys such as `agent_id`, `bridge_type`, `request_id`, `timestamp`.
- **Output:** `SessionID` — an opaque string identifier for this session.
- **Errors:** Never raises. On storage failure, logs to stderr and returns a fallback in-memory session ID.

---

### `log_event(session_id: SessionID, event: AnnallEvent) -> None`

Appends a structured event to an open session.

- **Input:**
  - `session_id` — a `SessionID` returned by `open_session`.
  - `event` — an `AnnallEvent` dataclass (see below).
- **Output:** None.
- **Errors:** Never raises. On storage failure, logs to stderr silently and continues.

---

### `close_session(session_id: SessionID, outcome: SessionOutcome) -> None`

Closes a session and records its final outcome.

- **Input:**
  - `session_id` — the session to close.
  - `outcome` — a `SessionOutcome` dataclass with fields: `success: bool`, `summary: str`, `elapsed_seconds: float`.
- **Output:** None.
- **Errors:** Never raises.

---

### `query_sessions(filter: SessionFilter) -> list[SessionSummary]`

Retrieves summary records for past sessions matching a filter.

- **Input:** `filter` — a `SessionFilter` dataclass with optional fields: `agent_id: str | None`, `since: datetime | None`, `success: bool | None`, `limit: int | None`.
- **Output:** `list[SessionSummary]` — ordered newest-first. Each `SessionSummary` carries: `session_id`, `agent_id`, `bridge_type`, `started_at`, `ended_at`, `success`, `summary`.
- **Errors:**
  - `AnnallQueryError` — raised if the storage backend is unavailable. This is the only method that propagates storage errors to callers, because query callers (agent history tools) expect a real result.

---

### `get_session(session_id: SessionID) -> SessionRecord`

Retrieves the full record for a single session, including all logged events.

- **Input:** `session_id` — the session to retrieve.
- **Output:** `SessionRecord` — includes all `AnnallEvent` objects logged to this session plus the `SessionSummary`.
- **Errors:**
  - `AnnallNotFoundError` — if the session_id does not exist.
  - `AnnallQueryError` — if the backend is unavailable.

---

## Key Data Structures

### `AnnallEvent` (dataclass)

```
event_type: str           # e.g. "loom.validated", "forge.started", "gate.failed"
payload: dict             # Event-specific detail; schema varies by event_type
timestamp: datetime
severity: str             # "info" | "warning" | "error"
```

### `SessionFilter` (dataclass)

```
agent_id: str | None
since: datetime | None
success: bool | None
limit: int | None         # Default 100 if None
```

### `AnnallQueryError` (exception)

```
message: str
cause: Exception | None
```

---

## Invariants

1. All callers import from `seidr_smidja.annall.port` — never from `annall.adapters.sqlite` or any concrete adapter.
2. `open_session`, `log_event`, and `close_session` never raise to their callers. Forge operations must not fail because the record-keeper stumbled.
3. The database file is always located through the configuration layer — never at a hardcoded path.
4. The adapter is injected as a dependency at startup — never imported as a module-level global.

---

## Dependencies

- None within the forge domain. Depends only on its configured storage backend.

---

*Rúnhild Svartdóttir, Architect — 2026-05-06*
