"""
Port Scan Plugin for TrashClaw

Check if common ports are open on a host using pure sockets (no nmap).
Useful for quick connectivity checks and service discovery.

Plugin contract:
  TOOL_DEF = dict with name, description, parameters (OpenAI function schema)
  run(**kwargs) -> str  (called with the parsed arguments)
"""

import socket

TOOL_DEF = {
    "name": "port_scan",
    "description": "Check if common ports are open on a host. Pure socket-based, no nmap needed. Specify a host and optionally a comma-separated list of ports.",
    "parameters": {
        "type": "object",
        "properties": {
            "host": {
                "type": "string",
                "description": "Hostname or IP address to scan"
            },
            "ports": {
                "type": "string",
                "description": "Comma-separated list of ports to check (default: common ports 22,80,443,8080,3306,5432,6379,27017)"
            },
            "timeout": {
                "type": "number",
                "description": "Connection timeout in seconds per port (default: 1.5)"
            }
        },
        "required": ["host"]
    }
}

# Well-known port labels
PORT_LABELS = {
    21: "FTP",
    22: "SSH",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    993: "IMAPS",
    995: "POP3S",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    5672: "RabbitMQ",
    6379: "Redis",
    8080: "HTTP-Alt",
    8443: "HTTPS-Alt",
    8099: "Custom",
    9090: "Prometheus",
    9200: "Elasticsearch",
    11211: "Memcached",
    27017: "MongoDB",
}

DEFAULT_PORTS = [22, 80, 443, 8080, 3306, 5432, 6379, 27017]


def _check_port(host: str, port: int, timeout: float) -> bool:
    """Return True if port is open (accepts TCP connection)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((host, port))
            return result == 0
    except (socket.gaierror, socket.herror, OSError):
        return False


def run(host: str = "", ports: str = "", timeout: float = 1.5, **kwargs) -> str:
    if not host:
        return "Error: 'host' is required."

    # Parse ports
    if ports:
        try:
            port_list = [int(p.strip()) for p in ports.split(",") if p.strip()]
        except ValueError:
            return "Error: 'ports' must be comma-separated integers (e.g. '22,80,443')."
    else:
        port_list = DEFAULT_PORTS

    if not port_list:
        return "Error: no ports specified."

    if len(port_list) > 100:
        return "Error: max 100 ports per scan."

    timeout = float(timeout)
    if timeout <= 0 or timeout > 30:
        timeout = 1.5

    # Resolve hostname first to give a clear error
    try:
        ip = socket.gethostbyname(host)
    except socket.gaierror:
        return f"Error: cannot resolve hostname '{host}'."

    results_open = []
    results_closed = []

    for port in sorted(port_list):
        label = PORT_LABELS.get(port, "")
        is_open = _check_port(ip, port, timeout)
        tag = f" ({label})" if label else ""
        line = f"  {port:>5}/tcp{tag}"
        if is_open:
            results_open.append(f"{line}  OPEN")
        else:
            results_closed.append(f"{line}  closed")

    header = f"Port scan: {host} ({ip})\n"
    header += f"Ports checked: {len(port_list)} | Timeout: {timeout}s\n"
    header += "-" * 40

    lines = [header, ""]
    if results_open:
        lines.append("OPEN:")
        lines.extend(results_open)
    if results_closed:
        if results_open:
            lines.append("")
        lines.append("CLOSED:")
        lines.extend(results_closed)

    summary = f"\n\nSummary: {len(results_open)} open, {len(results_closed)} closed"
    lines.append(summary)

    return "\n".join(lines)
