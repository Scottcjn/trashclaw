"""
Env Audit Plugin for TrashClaw

Scan a directory for common security misconfigurations:
  - .env files committed to git
  - Exposed secrets (API keys, passwords, tokens in source)
  - World-readable private keys
  - Sensitive files without .gitignore coverage

Plugin contract:
  TOOL_DEF = dict with name, description, parameters (OpenAI function schema)
  run(**kwargs) -> str  (called with the parsed arguments)
"""

import os
import re
import stat

TOOL_DEF = {
    "name": "env_audit",
    "description": "Scan a directory for common security misconfigurations: .env in git, exposed secrets, world-readable keys, missing .gitignore entries.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory to scan (default: current directory)"
            },
            "deep": {
                "type": "boolean",
                "description": "If true, scan file contents for secrets (slower). Default: true."
            }
        },
        "required": []
    }
}

# Filenames that should never be committed
SENSITIVE_FILES = [
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
    ".env.development",
    "credentials.json",
    "service-account.json",
    "secrets.yaml",
    "secrets.yml",
    ".netrc",
    ".npmrc",  # can contain tokens
    ".pypirc",  # can contain tokens
]

# Private key file patterns
KEY_PATTERNS = [
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "id_dsa",
]

# Regex patterns for secrets in file contents
SECRET_PATTERNS = [
    (r'(?i)(?:api[_-]?key|apikey)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{16,}', "API key"),
    (r'(?i)(?:secret|password|passwd|pwd)\s*[:=]\s*["\']?[^\s"\']{8,}', "Password/Secret"),
    (r'(?i)(?:aws_access_key_id|aws_secret_access_key)\s*[:=]\s*["\']?[A-Za-z0-9/+=]{16,}', "AWS credential"),
    (r'(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}', "Bearer token"),
    (r'ghp_[A-Za-z0-9]{36}', "GitHub PAT"),
    (r'sk-[A-Za-z0-9]{20,}', "OpenAI/Stripe secret key"),
    (r'(?i)(?:private[_-]?key)\s*[:=]\s*["\']?[A-Za-z0-9_\-/+=]{16,}', "Private key value"),
    (r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', "Private key block"),
]

# Extensions to scan for secrets
SCANNABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".rb", ".go", ".java",
    ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".conf",
    ".sh", ".bash", ".zsh", ".env", ".properties", ".xml",
    ".tf", ".hcl", ".dockerfile",
}

# Directories to skip
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "env", ".tox", ".mypy_cache", ".pytest_cache", "dist",
    "build", ".eggs", "*.egg-info",
}

MAX_FILE_SIZE = 512 * 1024  # 512KB max per file for content scanning


def _is_git_tracked(filepath: str, repo_root: str) -> bool:
    """Check if a file is tracked by git (would be committed)."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", filepath],
            cwd=repo_root, capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False  # Can't determine; assume not tracked


def _is_gitignored(filepath: str, repo_root: str) -> bool:
    """Check if a file is covered by .gitignore."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "check-ignore", "-q", filepath],
            cwd=repo_root, capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def _check_permissions(filepath: str) -> str:
    """Check if file has overly permissive permissions (world-readable)."""
    try:
        st = os.stat(filepath)
        mode = st.st_mode
        if mode & stat.S_IROTH:  # World-readable
            return f"{oct(mode & 0o777)} (world-readable)"
    except Exception:
        pass
    return ""


def _scan_file_contents(filepath: str) -> list:
    """Scan a file for secret patterns. Returns list of (line_no, pattern_name, snippet)."""
    findings = []
    try:
        size = os.path.getsize(filepath)
        if size > MAX_FILE_SIZE:
            return findings
        with open(filepath, "r", errors="replace") as f:
            for line_no, line in enumerate(f, 1):
                for pattern, name in SECRET_PATTERNS:
                    if re.search(pattern, line):
                        # Truncate the line for display
                        snippet = line.strip()
                        if len(snippet) > 100:
                            snippet = snippet[:97] + "..."
                        findings.append((line_no, name, snippet))
                        break  # One finding per line is enough
    except Exception:
        pass
    return findings


def _find_git_root(path: str) -> str:
    """Walk up to find .git directory."""
    current = os.path.abspath(path)
    while current != os.path.dirname(current):
        if os.path.isdir(os.path.join(current, ".git")):
            return current
        current = os.path.dirname(current)
    return ""


def run(path: str = "", deep: bool = True, **kwargs) -> str:
    scan_dir = os.path.abspath(path or os.getcwd())
    if not os.path.isdir(scan_dir):
        return f"Error: not a directory: {scan_dir}"

    git_root = _find_git_root(scan_dir)
    has_git = bool(git_root)

    issues = []  # (severity, category, filepath, detail)

    # Walk the directory tree
    for root, dirs, files in os.walk(scan_dir):
        # Skip hidden/vendor directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

        rel_root = os.path.relpath(root, scan_dir)

        for fname in files:
            filepath = os.path.join(root, fname)
            rel_path = os.path.relpath(filepath, scan_dir)

            # Check 1: Sensitive files present
            if fname.lower() in [s.lower() for s in SENSITIVE_FILES]:
                if has_git:
                    tracked = _is_git_tracked(rel_path, git_root)
                    ignored = _is_gitignored(rel_path, git_root)
                    if tracked:
                        issues.append(("CRITICAL", "sensitive_file_tracked", rel_path,
                                       f"Sensitive file is tracked by git!"))
                    elif not ignored:
                        issues.append(("WARNING", "sensitive_file_not_ignored", rel_path,
                                       f"Sensitive file exists but is NOT in .gitignore"))
                else:
                    issues.append(("WARNING", "sensitive_file_present", rel_path,
                                   f"Sensitive file found (no git repo to check ignore rules)"))

            # Check 2: Private key files
            for pat in KEY_PATTERNS:
                if pat.startswith("*"):
                    if fname.endswith(pat[1:]):
                        perm = _check_permissions(filepath)
                        if perm:
                            issues.append(("WARNING", "key_permissions", rel_path,
                                           f"Private key is {perm}"))
                        if has_git and _is_git_tracked(rel_path, git_root):
                            issues.append(("CRITICAL", "key_tracked", rel_path,
                                           f"Private key tracked by git!"))
                        break
                elif fname == pat:
                    perm = _check_permissions(filepath)
                    if perm:
                        issues.append(("WARNING", "key_permissions", rel_path,
                                       f"Private key is {perm}"))
                    if has_git and _is_git_tracked(rel_path, git_root):
                        issues.append(("CRITICAL", "key_tracked", rel_path,
                                       f"Private key tracked by git!"))
                    break

            # Check 3: Content scanning for secrets
            if deep:
                _, ext = os.path.splitext(fname)
                if ext.lower() in SCANNABLE_EXTENSIONS or fname.lower() in (".env",):
                    findings = _scan_file_contents(filepath)
                    for line_no, pattern_name, snippet in findings:
                        issues.append(("WARNING", "secret_in_source", rel_path,
                                       f"Line {line_no}: possible {pattern_name}"))

    # Check 4: .gitignore coverage
    if has_git:
        gitignore_path = os.path.join(git_root, ".gitignore")
        if not os.path.exists(gitignore_path):
            issues.append(("INFO", "no_gitignore", ".gitignore",
                           "No .gitignore file found in repository"))
        else:
            try:
                with open(gitignore_path, "r") as f:
                    gitignore_content = f.read()
                recommended = [".env", "*.pem", "*.key", "id_rsa", "credentials.json"]
                missing = [p for p in recommended if p not in gitignore_content]
                if missing:
                    issues.append(("INFO", "gitignore_incomplete", ".gitignore",
                                   f"Missing recommended patterns: {', '.join(missing)}"))
            except Exception:
                pass

    # Format output
    lines = [f"Env Audit: {scan_dir}", "=" * 50]

    if not issues:
        lines.append("")
        lines.append("No issues found. Directory looks clean.")
        return "\n".join(lines)

    # Group by severity
    critical = [i for i in issues if i[0] == "CRITICAL"]
    warnings = [i for i in issues if i[0] == "WARNING"]
    info = [i for i in issues if i[0] == "INFO"]

    if critical:
        lines.append("")
        lines.append(f"CRITICAL ({len(critical)}):")
        for sev, cat, fpath, detail in critical:
            lines.append(f"  [!] {fpath}: {detail}")

    if warnings:
        lines.append("")
        lines.append(f"WARNINGS ({len(warnings)}):")
        for sev, cat, fpath, detail in warnings:
            lines.append(f"  [*] {fpath}: {detail}")

    if info:
        lines.append("")
        lines.append(f"INFO ({len(info)}):")
        for sev, cat, fpath, detail in info:
            lines.append(f"  [i] {fpath}: {detail}")

    lines.append("")
    lines.append(f"Total: {len(critical)} critical, {len(warnings)} warnings, {len(info)} info")

    return "\n".join(lines)
