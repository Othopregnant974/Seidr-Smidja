"""Annáll — the Record.

The memory, logging, and session-tracking layer. Annáll records every build
request, every render, every compliance result, and every agent invocation.

All callers interact exclusively through the AnnallPort abstract interface.
The SQLiteAnnallAdapter in annall/adapters/sqlite.py is the first concrete
implementation. Future adapters (Postgres, flat-file) implement the same port.

What has been forged is never forgotten.

Annáll never raises an exception to its callers for a logging failure — forge
operations must never fail because the record-keeper stumbled.

Public surface: see INTERFACE.md in this directory.
Port definition: see annall/port.py.
"""

# Re-export the port types so callers can do:
#   from seidr_smidja.annall import AnnallPort, AnnallEvent, SessionOutcome
from seidr_smidja.annall.factory import make_annall
from seidr_smidja.annall.port import (
    AnnallEvent,
    AnnallNotFoundError,
    AnnallPort,
    AnnallQueryError,
    SessionFilter,
    SessionID,
    SessionOutcome,
    SessionRecord,
    SessionSummary,
)

__all__ = [
    "AnnallPort",
    "AnnallEvent",
    "AnnallNotFoundError",
    "AnnallQueryError",
    "SessionFilter",
    "SessionID",
    "SessionOutcome",
    "SessionRecord",
    "SessionSummary",
    "make_annall",
]
