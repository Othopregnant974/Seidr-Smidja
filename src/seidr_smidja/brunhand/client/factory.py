"""seidr_smidja.brunhand.client.factory — BrunhandClient construction helpers.

Provides make_client_from_config() which builds a BrunhandClient from a named
host entry in the brunhand.hosts config list, resolving token from env vars
or the token_path field.

Also provides make_session_from_config() which wraps the client in a
Tengslastig context manager ready for use.

INVARIANTS:
  - Config must contain a matching host entry by name — raises BrunhandConfigError
    if not found.
  - Token is never logged.
  - Returns a raw client (not a context manager) — caller is responsible for close().
    Use make_session_from_config() to get a Tengslastig context manager.

See: docs/features/brunhand/ARCHITECTURE.md §IV Factory
"""
from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def make_client_from_config(
    host_name: str,
    config: dict[str, Any],
    token_override: str | None = None,
) -> Any:
    """Build a BrunhandClient from the named host entry in config.

    Args:
        host_name:      The host name to look up in brunhand.hosts[].name.
        config:         Full loaded config dict (from load_config()).
        token_override: Optional token to use instead of the config/env value.

    Returns:
        A BrunhandClient instance. Caller is responsible for calling .close().

    Raises:
        BrunhandConfigError: If the host is not found or token cannot be resolved.
        ImportError: If httpx is not installed.
    """
    from seidr_smidja.brunhand.client.client import BrunhandClient
    from seidr_smidja.brunhand.exceptions import BrunhandConfigError

    brunhand_cfg = config.get("brunhand", {})
    hosts = brunhand_cfg.get("hosts", [])

    # Find the matching host entry
    host_entry: dict[str, Any] | None = None
    for entry in hosts:
        if isinstance(entry, dict) and entry.get("name") == host_name:
            host_entry = entry
            break

    if host_entry is None:
        raise BrunhandConfigError(
            f"No Brúarhönd host entry named '{host_name}' found in brunhand.hosts config. "
            f"Available names: {[e.get('name') for e in hosts if isinstance(e, dict)]}",
        )

    host = host_entry.get("host", "")
    if not host:
        raise BrunhandConfigError(
            f"Brúarhönd host entry '{host_name}' is missing the 'host' field.",
        )

    port = int(host_entry.get("port", brunhand_cfg.get("daemon", {}).get("port", 8848)))
    tls = host_entry.get("tls", True)
    verify_tls = host_entry.get("verify_tls", True)

    # Resolve token
    token = token_override or _resolve_token(host_entry, host_name)
    if not token:
        raise BrunhandConfigError(
            f"Brúarhönd host '{host_name}': cannot resolve bearer token. "
            "Set BRUNHAND_TOKEN env var, or configure token/token_path in host entry.",
        )

    client_cfg = brunhand_cfg.get("client", {})
    timeout = float(client_cfg.get("timeout_seconds", 30.0))
    request_timeout_buffer = float(client_cfg.get("request_timeout_buffer", 5.0))

    return BrunhandClient(
        host=host,
        token=token,
        port=port,
        tls=tls,
        timeout=timeout,
        verify_tls=verify_tls,
        config=config,
        request_timeout_buffer=request_timeout_buffer,
    )


@contextmanager
def make_session_from_config(
    host_name: str,
    config: dict[str, Any],
    token_override: str | None = None,
    agent_id: str = "",
    oracle_eye: Any = None,
    annall: Any = None,
    annall_session_id: str = "",
    run_id: str | None = None,
    output_dir: Any = None,
) -> Iterator[Any]:
    """Context manager that builds a Tengslastig session from config.

    Usage:
        with make_session_from_config("vroid-host", config) as session:
            result = session.screenshot()

    Args:
        host_name:         Name of the host entry in brunhand.hosts.
        config:            Full config dict from load_config().
        token_override:    Optional token override.
        agent_id:          Agent identity for Annáll events and requests.
        oracle_eye:        Optional oracle_eye module for Ljósbrú.
        annall:            Optional AnnallPort for telemetry.
        annall_session_id: External Annáll session ID (if none, opened internally).
        run_id:            Optional Mode C run_id.
        output_dir:        Optional output dir for Oracle Eye renders.

    Yields:
        A Tengslastig session.
    """
    from seidr_smidja.brunhand.client.session import Tengslastig

    client = make_client_from_config(host_name, config, token_override)
    try:
        session = Tengslastig(
            client=client,
            agent_id=agent_id,
            oracle_eye=oracle_eye,
            annall=annall,
            annall_session_id=annall_session_id,
            run_id=run_id,
            output_dir=output_dir,
        )
        with session:
            yield session
    finally:
        client.close()


def _resolve_token(host_entry: dict[str, Any], host_name: str) -> str:
    """Resolve bearer token from env var > host entry token > host entry token_path."""
    # 1. Environment variable: BRUNHAND_TOKEN_<HOSTNAME_UPPER> or BRUNHAND_TOKEN
    env_key_specific = f"BRUNHAND_TOKEN_{host_name.upper().replace('-', '_').replace('.', '_')}"
    token = os.environ.get(env_key_specific, "").strip()
    if token:
        return token

    token = os.environ.get("BRUNHAND_TOKEN", "").strip()
    if token:
        return token

    # 2. Inline token in host entry (not recommended for production)
    inline = host_entry.get("token", "").strip()
    if inline:
        logger.warning(
            "Brúarhönd: using inline bearer token from config for host '%s'. "
            "Consider using BRUNHAND_TOKEN env var instead.",
            host_name,
        )
        return inline

    # 3. token_path file
    token_path = host_entry.get("token_path", "").strip()
    if token_path:
        try:
            p = Path(token_path).expanduser()
            token = p.read_text(encoding="utf-8").strip()
            if token:
                return token
        except Exception as exc:
            logger.warning(
                "Brúarhönd: cannot read token_path '%s' for host '%s': %s",
                token_path, host_name, exc,
            )

    return ""
