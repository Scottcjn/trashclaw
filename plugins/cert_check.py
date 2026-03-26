"""
Cert Check Plugin for TrashClaw

Check TLS certificate expiry, issuer, and validity for a domain.
Pure stdlib (ssl + socket), no openssl CLI needed.

Plugin contract:
  TOOL_DEF = dict with name, description, parameters (OpenAI function schema)
  run(**kwargs) -> str  (called with the parsed arguments)
"""

import ssl
import socket
from datetime import datetime, timezone

TOOL_DEF = {
    "name": "cert_check",
    "description": "Check TLS certificate expiry, issuer, subject, and validity for a domain. Shows days until expiration.",
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Domain name to check (e.g. 'example.com')"
            },
            "port": {
                "type": "integer",
                "description": "TLS port (default: 443)"
            }
        },
        "required": ["domain"]
    }
}


def _parse_cert_time(time_str: str) -> datetime:
    """Parse certificate time string to datetime."""
    # OpenSSL format: 'Mon DD HH:MM:SS YYYY GMT'
    return datetime.strptime(time_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)


def _format_dn(dn_tuple) -> str:
    """Format a certificate distinguished name tuple into readable string."""
    parts = []
    if not dn_tuple:
        return "(empty)"
    for rdn in dn_tuple:
        for attr_type, attr_value in rdn:
            parts.append(f"{attr_type}={attr_value}")
    return ", ".join(parts)


def _get_san(cert: dict) -> list:
    """Extract Subject Alternative Names from certificate."""
    san = []
    for entry_type, value in cert.get("subjectAltName", ()):
        san.append(f"{entry_type}:{value}")
    return san


def run(domain: str = "", port: int = 443, **kwargs) -> str:
    if not domain:
        return "Error: 'domain' is required."

    # Strip protocol prefix if provided
    domain = domain.replace("https://", "").replace("http://", "")
    # Strip path
    domain = domain.split("/")[0]
    # Strip port from domain if included
    if ":" in domain:
        parts = domain.split(":")
        domain = parts[0]
        try:
            port = int(parts[1])
        except ValueError:
            pass

    port = int(port)

    try:
        # Create SSL context that still retrieves the certificate
        ctx = ssl.create_default_context()
        conn = ctx.wrap_socket(socket.socket(socket.AF_INET), server_hostname=domain)
        conn.settimeout(10.0)
        conn.connect((domain, port))
        cert = conn.getpeercert()
        cipher = conn.cipher()
        protocol = conn.version()
        conn.close()
    except ssl.SSLCertVerificationError as e:
        # Still try to get cert info even if verification fails
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            conn = ctx.wrap_socket(socket.socket(socket.AF_INET), server_hostname=domain)
            conn.settimeout(10.0)
            conn.connect((domain, port))
            # With CERT_NONE, getpeercert() returns empty dict; use binary
            cert_bin = conn.getpeercert(True)
            cipher = conn.cipher()
            protocol = conn.version()
            conn.close()
            return (f"Cert Check: {domain}:{port}\n"
                    f"{'=' * 40}\n\n"
                    f"WARNING: Certificate verification FAILED\n"
                    f"Reason: {e}\n\n"
                    f"Protocol: {protocol}\n"
                    f"Cipher: {cipher[0] if cipher else 'unknown'}\n\n"
                    f"The certificate exists but is not trusted.\n"
                    f"This could mean: self-signed, expired, or wrong hostname.")
        except Exception as e2:
            return f"Error: could not connect to {domain}:{port}\n  SSL error: {e}\n  Fallback error: {e2}"
    except socket.gaierror:
        return f"Error: cannot resolve hostname '{domain}'."
    except socket.timeout:
        return f"Error: connection to {domain}:{port} timed out."
    except ConnectionRefusedError:
        return f"Error: connection refused to {domain}:{port}."
    except Exception as e:
        return f"Error connecting to {domain}:{port}: {e}"

    if not cert:
        return f"Error: no certificate data returned from {domain}:{port}."

    # Parse certificate fields
    subject = _format_dn(cert.get("subject", ()))
    issuer = _format_dn(cert.get("issuer", ()))
    not_before_str = cert.get("notBefore", "")
    not_after_str = cert.get("notAfter", "")
    serial = cert.get("serialNumber", "unknown")
    san = _get_san(cert)

    # Calculate expiry
    now = datetime.now(timezone.utc)
    try:
        not_before = _parse_cert_time(not_before_str)
        not_after = _parse_cert_time(not_after_str)
        days_remaining = (not_after - now).days
        total_days = (not_after - not_before).days
    except Exception:
        not_before = not_before_str
        not_after = not_after_str
        days_remaining = None
        total_days = None

    # Status determination
    if days_remaining is not None:
        if days_remaining < 0:
            status = "EXPIRED"
            status_detail = f"Expired {abs(days_remaining)} days ago!"
        elif days_remaining <= 7:
            status = "CRITICAL"
            status_detail = f"Expires in {days_remaining} days!"
        elif days_remaining <= 30:
            status = "WARNING"
            status_detail = f"Expires in {days_remaining} days"
        else:
            status = "OK"
            status_detail = f"{days_remaining} days remaining"
    else:
        status = "UNKNOWN"
        status_detail = "Could not parse dates"

    # Format output
    lines = [
        f"Cert Check: {domain}:{port}",
        "=" * 40,
        "",
        f"Status:      {status} - {status_detail}",
        "",
        f"Subject:     {subject}",
        f"Issuer:      {issuer}",
        f"Serial:      {serial}",
        "",
        f"Valid From:  {not_before_str}",
        f"Valid Until: {not_after_str}",
    ]

    if days_remaining is not None:
        lines.append(f"Remaining:   {days_remaining} days")
    if total_days is not None:
        lines.append(f"Validity:    {total_days} days total")

    if san:
        lines.append("")
        lines.append(f"SANs ({len(san)}):")
        for s in san[:20]:  # Cap at 20
            lines.append(f"  {s}")
        if len(san) > 20:
            lines.append(f"  ... and {len(san) - 20} more")

    if cipher:
        lines.append("")
        lines.append(f"Protocol:    {protocol}")
        lines.append(f"Cipher:      {cipher[0]}")
        if len(cipher) > 2:
            lines.append(f"Bits:        {cipher[2]}")

    return "\n".join(lines)
