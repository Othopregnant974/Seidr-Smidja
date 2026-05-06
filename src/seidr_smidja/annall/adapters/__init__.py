"""
Annáll Adapters — concrete implementations of AnnallPort.

Each adapter in this package implements the AnnallPort protocol.
Callers must never import directly from this package — always import from
seidr_smidja.annall.port and receive the configured adapter via dependency
injection at startup.

Current adapters:
    sqlite.py — SQLiteAnnallAdapter (default, zero-server, portable)
"""
