"""
Annáll — the Record.

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
