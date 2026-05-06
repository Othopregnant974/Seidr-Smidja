# Runa Gridweaver — Thread Safety Fix Report
*2026-05-06*

## Problem
The Mímir memory tools (`runa_recall`, `runa_remember`, `runa_reason`) raised:
```
"SQLite objects created in a thread can only be used in that same thread. 
The object was created in thread id 547464606080 and this is thread id 547704664448."
```

## Root Cause
SQLite's `sqlite3.connect()` defaults to `check_same_thread=True`, meaning connections 
created in one Python thread cannot be used in another. The Hermes agent loads the 
Mímir plugin (which initializes RunaMemory) in one thread, but MCP tool calls 
arrive on a different thread.

## Fix Applied
1. **`runa_memory.py`**: Added `check_same_thread=False` to ALL `sqlite3.connect()` calls
2. **`runa_memory.py`**: Added `threading.local()` (`_thread_local`) for per-thread 
   connection storage in the fallback path (when RobustConnection isn't used)
3. **`runa_memory.py`**: Updated `_get_conn()` to lazily create a new connection per 
   thread using `_thread_local`, with connection health checks
4. **`runa_connection.py`**: Added `check_same_thread=False` to the main connection 
   creation in `RobustConnection._create_connection()`

## Files Modified
- `/home/pi/.hermes/memory/runa_memory.py` — 5 `check_same_thread=False` + thread-local
- `/home/pi/.hermes/memory/runa_connection.py` — 1 `check_same_thread=False`

## Backups Created
- `runa_memory.backup-20260506_075359.py`
- `runa_connection.backup-20260506_075359.py`

## Fix Script
- `/home/pi/Seidr-Smidja/scripts/fix_memory_thread_safety.py`
- Committed as `8861143` on development branch

## Status
✅ Fix is ON DISK but requires **Hermes restart** to take effect.
The running Hermes process still has the OLD code loaded in memory.

## To Activate
```bash
# Restart Hermes agent to reload patched Python files
# This will briefly disconnect the chat session
hermes restart
```

## To Test After Restart
```
runa_recall(action='important', min_importance=7)
runa_remember(action='memory', content='Test thread safety', category='lesson')
```

## Additional Note: Memory DB Alternative
Since the Runa memory DB has these thread issues and the `runa_remember`/`runa_recall`/`runa_reason` 
tools continue to fail even after patching (until restart), status logs are persisted as markdown 
files in `~/Seidr-Smidja/logs/` as a reliable backup:

- `PROJECT_STATUS.md` — Technical state, specs, blockers
- `EVENT_LOG.md` — Session-by-session history
- `KNOWLEDGE_COMPENDIUM.md` — All knowledge, accounts, specs
- `SAGA_AND_MEMORY.md` — Milestones, lessons, priorities  
- `CRITICAL_FACTS.md` — Must-persist facts across sessions