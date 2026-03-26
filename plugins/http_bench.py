"""
HTTP Bench Plugin for TrashClaw

Simple HTTP benchmark: send N requests to a URL and report latency percentiles
(p50, p95, p99), success rate, and throughput. Pure stdlib, no dependencies.

Plugin contract:
  TOOL_DEF = dict with name, description, parameters (OpenAI function schema)
  run(**kwargs) -> str  (called with the parsed arguments)
"""

import time
import urllib.request
import urllib.error
import statistics
import ssl
import concurrent.futures

TOOL_DEF = {
    "name": "http_bench",
    "description": "Simple HTTP benchmark. Send N requests to a URL and report p50/p95/p99 latency, success rate, and throughput.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to benchmark (e.g. https://example.com)"
            },
            "requests": {
                "type": "integer",
                "description": "Number of requests to send (default: 20, max: 500)"
            },
            "concurrency": {
                "type": "integer",
                "description": "Number of concurrent workers (default: 4, max: 20)"
            },
            "method": {
                "type": "string",
                "description": "HTTP method: GET or POST (default: GET)"
            },
            "timeout": {
                "type": "number",
                "description": "Request timeout in seconds (default: 10)"
            }
        },
        "required": ["url"]
    }
}


def _percentile(sorted_data: list, pct: float) -> float:
    """Calculate percentile from sorted data."""
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * (pct / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return sorted_data[f]
    d = k - f
    return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])


def _make_request(url: str, method: str, req_timeout: float) -> dict:
    """Make a single HTTP request and return timing info."""
    result = {"status": 0, "latency_ms": 0.0, "error": None, "size": 0}
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url, method=method.upper())
        req.add_header("User-Agent", "TrashClaw-HTTPBench/1.0")

        start = time.monotonic()
        with urllib.request.urlopen(req, timeout=req_timeout, context=ctx) as resp:
            body = resp.read()
            elapsed = time.monotonic() - start
            result["status"] = resp.status
            result["latency_ms"] = elapsed * 1000
            result["size"] = len(body)
    except urllib.error.HTTPError as e:
        elapsed = time.monotonic() - start
        result["status"] = e.code
        result["latency_ms"] = elapsed * 1000
        result["error"] = f"HTTP {e.code}"
    except urllib.error.URLError as e:
        result["error"] = str(e.reason)
    except Exception as e:
        result["error"] = str(e)
    return result


def run(url: str = "", requests: int = 20, concurrency: int = 4,
        method: str = "GET", timeout: float = 10.0, **kwargs) -> str:
    if not url:
        return "Error: 'url' is required."

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url

    requests = min(max(int(requests), 1), 500)
    concurrency = min(max(int(concurrency), 1), 20)
    timeout = min(max(float(timeout), 0.5), 60.0)
    method = method.upper()
    if method not in ("GET", "POST", "HEAD", "PUT", "DELETE", "PATCH"):
        method = "GET"

    lines = [f"HTTP Benchmark: {method} {url}",
             f"Requests: {requests} | Concurrency: {concurrency} | Timeout: {timeout}s",
             "-" * 50, ""]

    results = []
    wall_start = time.monotonic()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(_make_request, url, method, timeout)
            for _ in range(requests)
        ]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    wall_elapsed = time.monotonic() - wall_start

    # Analyze results
    successes = [r for r in results if r["error"] is None and 200 <= r["status"] < 400]
    failures = [r for r in results if r not in successes]
    latencies = sorted([r["latency_ms"] for r in successes])

    success_rate = len(successes) / len(results) * 100 if results else 0

    if latencies:
        p50 = _percentile(latencies, 50)
        p95 = _percentile(latencies, 95)
        p99 = _percentile(latencies, 99)
        avg = statistics.mean(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)

        lines.append("Latency (ms):")
        lines.append(f"  min:  {min_lat:>8.1f}")
        lines.append(f"  avg:  {avg:>8.1f}")
        lines.append(f"  p50:  {p50:>8.1f}")
        lines.append(f"  p95:  {p95:>8.1f}")
        lines.append(f"  p99:  {p99:>8.1f}")
        lines.append(f"  max:  {max_lat:>8.1f}")
    else:
        lines.append("No successful requests to report latency.")

    lines.append("")
    lines.append("Results:")
    lines.append(f"  Total:       {len(results)}")
    lines.append(f"  Successful:  {len(successes)}")
    lines.append(f"  Failed:      {len(failures)}")
    lines.append(f"  Success %:   {success_rate:.1f}%")
    lines.append(f"  Wall time:   {wall_elapsed:.2f}s")

    if wall_elapsed > 0:
        rps = len(results) / wall_elapsed
        lines.append(f"  Throughput:  {rps:.1f} req/s")

    if successes:
        total_bytes = sum(r["size"] for r in successes)
        lines.append(f"  Avg size:    {total_bytes // len(successes):,} bytes")

    # Show error breakdown if any failures
    if failures:
        lines.append("")
        lines.append("Errors:")
        error_counts = {}
        for r in failures:
            err = r["error"] or f"HTTP {r['status']}"
            error_counts[err] = error_counts.get(err, 0) + 1
        for err, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {count}x {err}")

    return "\n".join(lines)
