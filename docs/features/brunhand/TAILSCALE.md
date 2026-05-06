# Brúarhönd — Tailscale Setup
**Audience:** Operators (humans who set up the daemon on a VRoid host machine).
**Last updated:** 2026-05-06

---

## Why Tailscale

Brúarhönd's network design assumes Tailscale (or an equivalent encrypted overlay network) is the trust boundary between forge and daemon when they live on different machines.

- Tailscale's WireGuard tunnel provides E2E encryption between nodes — Brúarhönd does not need to ship its own VPN.
- Tailscale ACLs let you constrain which devices in your tailnet can reach the daemon's port — this is the **outer** layer of defense in depth (the bearer token is the inner layer).
- Tailscale's MagicDNS gives every device a stable hostname (`vroid-workstation.tailnet.ts.net`) — no IP juggling.

You can run Brúarhönd without Tailscale (e.g., on a LAN with HTTPS), but the daemon's default posture (bind to localhost only, refuse non-localhost binds without explicit `straumur.allow_remote_bind`-style config) is shaped around the Tailscale-as-trust-boundary assumption.

## Required Topology

- The forge machine and the VRoid host machine are both joined to the same Tailscale tailnet.
- The VRoid host runs the daemon (`python -m seidr_smidja.brunhand.daemon`).
- The forge calls the daemon via the VRoid host's Tailscale IP or MagicDNS hostname.

If you want multiple VRoid hosts, register each in `config/user.yaml` under `brunhand.hosts` on the forge machine.

## Recommended ACL — Default-Deny + Explicit Forge Access

Add this to your Tailscale admin's `acl.json` (or the equivalent in the admin UI):

```json
{
  "tagOwners": {
    "tag:forge": ["volmarr@example.com"],
    "tag:vroid-host": ["volmarr@example.com"]
  },
  "acls": [
    {
      "action": "accept",
      "src": ["tag:forge"],
      "dst": ["tag:vroid-host:8848"]
    }
  ]
}
```

Then tag your forge machine with `tag:forge` and your VRoid host with `tag:vroid-host`.

Result: only the forge machine can reach port 8848 on any vroid-host. All other tailnet devices cannot. All non-tailnet devices cannot.

## Recommended ACL — Single User, No Tags

If you don't want to use tags (single-user tailnet):

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["volmarr@example.com"],
      "dst": ["volmarr@example.com:8848"]
    }
  ]
}
```

Result: only your own user's devices can reach port 8848 on each other. Anyone you've shared the tailnet with cannot.

## Daemon Bind Configuration

By default the daemon binds to `127.0.0.1`, which is **unreachable from Tailscale**. To accept Tailscale connections, you must opt in.

### Option 1 — Bind the Tailscale IP (recommended)

Find the host's Tailscale IP:

```bash
tailscale ip -4
# 100.x.y.z
```

Set in `config/user.yaml` on the VRoid host:

```yaml
brunhand:
  daemon:
    bind_address: 100.x.y.z
    port: 8848
```

This binds *only* to the Tailscale interface. Localhost still works. Other LAN interfaces are not exposed.

### Option 2 — Bind 0.0.0.0 with explicit override (NOT recommended)

If you genuinely need to bind all interfaces (rare — typically because you don't have Tailscale and are using Tailscale-equivalent topology), set:

```yaml
brunhand:
  daemon:
    bind_address: 0.0.0.0
    allow_remote_bind: true
    port: 8848
```

The daemon refuses to bind non-localhost addresses unless `allow_remote_bind: true` is set, mirroring the Straumur REST bridge's defense pattern (D-005-style discipline).

## Bearer Token

Tailscale ACL alone is not sufficient. Even from approved devices, every Brúarhönd request must carry a valid bearer token in `Authorization: Bearer <token>`.

### Generating a token

```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Save it somewhere your forge can read it (env var, secret manager, or `~/.config/seidr-smidja/brunhand_tokens.yaml`).

### Daemon-side

```bash
export BRUNHAND_TOKEN="<the same token>"
python -m seidr_smidja.brunhand.daemon
```

Or set it in `config/user.yaml` under `brunhand.daemon.token` — but env var is preferred (avoids token-on-disk).

### Forge-side (per-host)

```yaml
brunhand:
  hosts:
    - name: vroid-workstation
      address: vroid-workstation.tailnet.ts.net
      port: 8848
      token_env: BRUNHAND_TOKEN_VROID_WORKSTATION   # or token_file: /path/to/token
```

## TLS

For Tailscale-internal traffic, HTTPS is recommended but not strictly required (Tailscale's tunnel is already E2E-encrypted). Two patterns:

### Self-signed certificate (simplest)

Generate a cert for the daemon's hostname:

```bash
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout brunhand.key \
  -out brunhand.crt \
  -days 365 \
  -subj "/CN=vroid-workstation.tailnet.ts.net"
```

Configure the daemon:

```yaml
brunhand:
  daemon:
    tls:
      cert_path: /path/to/brunhand.crt
      key_path: /path/to/brunhand.key
```

Configure the forge to trust the cert:

```yaml
brunhand:
  hosts:
    - name: vroid-workstation
      address: vroid-workstation.tailnet.ts.net
      port: 8848
      verify_tls: /path/to/brunhand.crt   # path to the daemon's public cert
      token_env: BRUNHAND_TOKEN_VROID_WORKSTATION
```

### Plain HTTP (Tailscale-encrypted only)

Acceptable on a Tailscale-internal connection because the tunnel is already encrypted. Set:

```yaml
brunhand:
  daemon:
    tls:
      enabled: false
```

Forge-side: omit `verify_tls`.

This is **not** acceptable on any non-Tailscale (raw LAN, internet) topology.

## Verification

From the forge machine:

```bash
seidr brunhand health vroid-workstation
# Expected: {"status": "ok", "version": "0.1.0", "os": "Windows", "screen": [1920, 1080], ...}
```

If health works but a real primitive fails, check:
- `seidr brunhand capabilities vroid-workstation` — are the primitives you want listed?
- Daemon-side log — is the bearer token validating?
- Forge-side Annáll — what error did the client log?

## Failure Modes Specific to Tailscale

- **Tailscale partition** (one machine offline) → `BrunhandConnectionError` with cause `dns/connect` from the client. The forge cannot reach the daemon's MagicDNS name. Wait for tailnet to reconverge or check `tailscale status` on both sides.
- **Wrong tag in ACL** → `BrunhandConnectionError` with cause `connection refused`. The Tailscale ACL is denying the connection at the network layer before the daemon ever sees it. Check `acl.json`.
- **Token rotation skew** → `BrunhandAuthError` (HTTP 401). Daemon and forge have different tokens. Re-export and restart on both sides.

## Cross-References

- `README.md` — feature overview and quickstart.
- `DATA_FLOW.md` — failure flows F1 (Tailscale partition), F2 (daemon unreachable), F3 (token invalid).
- `ARCHITECTURE.md` — authentication architecture, network model, TLS configuration.
- `../../docs/DECISIONS/D-010-brunhand-feature-genesis.md` — feature genesis decisions.
