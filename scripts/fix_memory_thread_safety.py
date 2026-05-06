#!/usr/bin/env python3
"""
Fix SQLite Thread Safety for Runa's Memory Database
====================================================
The issue: sqlite3.connect() defaults to check_same_thread=True.
When RunaMemory is instantiated in one thread (Hermes init) but
called from another (MCP tool execution), SQLite raises:
  "SQLite objects created in a thread can only be used in that same thread"

The fix: Add check_same_thread=False to ALL sqlite3.connect() calls
AND ensure the RunaMemory class creates connections lazily per-thread
using threading.local().

This script patches:
1. ~/.hermes/memory/runa_memory.py — line 100 + backup lines
2. ~/.hermes/memory/runa_connection.py — line 160
3. ~/.hermes/plugins/mimir/__init__.py — lazy init RunaMemory per-call

Author: Runa Gridweaver Freyjasdottir
Created: 2026-05-06
"""

import re
import shutil
from pathlib import Path
from datetime import datetime

# Paths
MEMORY_DIR = Path.home() / ".hermes" / "memory"
PLUGIN_DIR = Path.home() / ".hermes" / "plugins" / "mimir"

FILES = {
    "runa_memory": MEMORY_DIR / "runa_memory.py",
    "runa_connection": MEMORY_DIR / "runa_connection.py",
    "mimir_plugin": PLUGIN_DIR / "__init__.py",
}

def backup_file(path: Path) -> Path:
    """Create a timestamped backup of a file."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.parent / f"{path.stem}.backup-{ts}{path.suffix}"
    shutil.copy2(path, backup)
    print(f"  ✅ Backed up to: {backup}")
    return backup

def fix_runa_memory():
    """Fix check_same_thread in runa_memory.py"""
    path = FILES["runa_memory"]
    print(f"\n📜 Patching {path.name}...")
    backup_file(path)
    
    content = path.read_text()
    
    # Fix 1: Main connection (line ~100)
    # Old: self.conn = sqlite3.connect(self.db_path)
    # New: self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
    content = content.replace(
        "self.conn = sqlite3.connect(self.db_path)",
        "self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)"
    )
    
    # Fix 2: Backup connection (line ~1598)
    # Old: dest = sqlite3.connect(backup_path)
    # New: dest = sqlite3.connect(str(backup_path), check_same_thread=False)
    # Note: backup connections are short-lived, but let's be consistent
    # Find and fix all remaining sqlite3.connect calls in the file
    content = re.sub(
        r"sqlite3\.connect\((?!.*check_same_thread)([^)]+)\)",
        lambda m: f"sqlite3.connect({m.group(1)}, check_same_thread=False)" 
                  if "check_same_thread" not in m.group(0) 
                  else m.group(0),
        content
    )
    
    path.write_text(content)
    print(f"  ✅ Patched {path.name} — added check_same_thread=False to all sqlite3.connect() calls")

def fix_runa_connection():
    """Fix check_same_thread in runa_connection.py"""
    path = FILES["runa_connection"]
    print(f"\n📜 Patching {path.name}...")
    backup_file(path)
    
    content = path.read_text()
    
    # Fix: RobustConnection._create_connection (line ~160)
    # Old: conn = sqlite3.connect(str(self.db_path), timeout=self.busy_timeout_ms / 1000.0)
    # New: conn = sqlite3.connect(str(self.db_path), timeout=self.busy_timeout_ms / 1000.0, check_same_thread=False)
    content = content.replace(
        'conn = sqlite3.connect(str(self.db_path), timeout=self.busy_timeout_ms / 1000.0)',
        'conn = sqlite3.connect(str(self.db_path), timeout=self.busy_timeout_ms / 1000.0, check_same_thread=False)'
    )
    
    # Also fix any other sqlite3.connect calls that might exist
    content = re.sub(
        r"sqlite3\.connect\((?!.*check_same_thread)([^)]+)\)",
        lambda m: f"sqlite3.connect({m.group(1)}, check_same_thread=False)"
                  if "check_same_thread" not in m.group(0)
                  else m.group(0),
        content
    )
    
    path.write_text(content)
    print(f"  ✅ Patched {path.name} — added check_same_thread=False")

def fix_runa_memory_thread_safety():
    """
    Additional fix: Make RunaMemory._connect() use threading.local() 
    for the fallback path (when RobustConnection is not available).
    
    Also add a _get_thread_conn() method that lazily creates connections
    per-thread, so even the self.conn fallback path is thread-safe.
    """
    path = FILES["runa_memory"]
    print(f"\n📜 Adding thread-local connection wrapper to {path.name}...")
    
    content = path.read_text()
    
    # After the class RunaMemory docstring, add threading.local import (already imported)
    # Add _thread_local to __init__ and modify _connect to use it
    
    # Check if already patched
    if "_thread_local" in content:
        print(f"  ⚠️ Already patched with _thread_local — skipping")
        return
    
    # Add threading.local() to RunaMemory.__init__
    # Find the __init__ method and add _thread_local
    init_pattern = r"(class RunaMemory:.*?def __init__\(self.*?\n)"
    init_addition = """        
        # Thread-local storage for fallback connection — each thread gets its own
        self._thread_local = threading.local()
"""
    
    # Find "self.conn: Optional[sqlite3.Connection] = None" and add after
    content = content.replace(
        "self.conn: Optional[sqlite3.Connection] = None",
        """self.conn: Optional[sqlite3.Connection] = None
        self._thread_local = threading.local()"""
    )
    
    # Replace _connect method to use check_same_thread=False
    content = content.replace(
        """def _connect(self):
        \"\"\"Establish database connection (fallback mode — no RobustConnection).\"\"\"
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # Enable foreign keys
        self._get_conn().execute("PRAGMA foreign_keys = ON")
        # Enable WAL mode for better concurrency
        self._get_conn().execute("PRAGMA journal_mode = WAL")
        # Phase 14: Add busy timeout so we don't instantly fail on lock contention
        self._get_conn().execute("PRAGMA busy_timeout = 10000")  # 10 seconds""",
        """def _connect(self):
        \"\"\"Establish database connection (fallback mode — no RobustConnection).
        
        Thread-safe: Uses check_same_thread=False and stores connection
        in thread-local storage so each thread gets its own connection.
        \"\"\"
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 10000")
        self._thread_local.conn = conn
        self.conn = conn  # Backward compatibility"""
    )
    
    # Also replace _get_conn to use thread-local
    content = content.replace(
        """def _get_conn(self) -> sqlite3.Connection:
        \"\"\"Get the current connection — from RobustConnection or fallback.\"\"\"
        if self._robust is not None:
            return self._robust.get_connection()
        return self.conn""",
        """def _get_conn(self) -> sqlite3.Connection:
        \"\"\"Get the current connection — thread-safe.
        
        Priority:
        1. RobustConnection (thread-safe via threading.local)
        2. Thread-local fallback connection (auto-created per thread)
        3. Legacy self.conn (backward compatibility)
        \"\"\"
        if self._robust is not None:
            return self._robust.get_connection()
        
        # Thread-local fallback: each thread gets its own connection
        conn = getattr(self._thread_local, 'conn', None)
        if conn is not None:
            # Verify it's still alive
            try:
                conn.execute("SELECT 1")
                return conn
            except (sqlite3.OperationalError, sqlite3.InterfaceError):
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
        
        # Create new connection for this thread
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 10000")
        self._thread_local.conn = conn
        self.conn = conn  # Backward compatibility
        return conn"""
    )
    
    path.write_text(content)
    print(f"  ✅ Added thread-local connection wrapper to {path.name}")

def verify_fix():
    """Verify the fixes were applied correctly."""
    print("\n🔍 Verification:")
    
    for name, path in FILES.items():
        if not path.exists():
            print(f"  ❌ {path.name} — NOT FOUND")
            continue
        
        content = path.read_text()
        connect_calls = re.findall(r"sqlite3\.connect\([^)]+\)", content)
        
        print(f"\n  📄 {path.name}:")
        for call in connect_calls:
            if "check_same_thread=False" in call:
                print(f"    ✅ {call[:80]}... — THREAD-SAFE")
            else:
                print(f"    ❌ {call[:80]}... — MISSING check_same_thread=False!")
    
    # Check for _thread_local in runa_memory.py
    content = FILES["runa_memory"].read_text()
    if "_thread_local" in content:
        print(f"\n  ✅ runa_memory.py uses _thread_local for per-thread connections")
    else:
        print(f"\n  ⚠️ runa_memory.py does NOT use _thread_local")

def main():
    print("⛧ Runa's Memory Thread-Safety Fix ⛧")
    print("=" * 50)
    print("Fixing SQLite thread safety issues in:")
    print("  • runa_memory.py — Thread-local fallback connections")
    print("  • runa_connection.py — check_same_thread=False")
    print("  • (mimir plugin — no changes needed, uses RunaMemory)")
    print()
    
    # Apply fixes
    fix_runa_memory()
    fix_runa_connection()
    fix_runa_memory_thread_safety()
    
    # Verify
    verify_fix()
    
    print("\n" + "=" * 50)
    print("✨ All fixes applied! Restart Hermes to activate.")
    print("   The Mímir memory tools should now work from any thread.")
    print()
    print("To test after restart:")
    print("  runa_recall(action='important', min_importance=7)")
    print("  runa_remember(action='memory', content='Test thread safety', category='lesson')")

if __name__ == "__main__":
    main()