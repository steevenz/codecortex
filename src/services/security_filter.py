"""
Security Filter — comprehensive security checks for filesystem search.

Provides:
  - Sensitive file detection (extensions + exact names) [always blocked]
  - Sensitive content detection with severity levels (low/medium/high/critical)
  - Vulgar/inappropriate content detection [always blocked, never shown]
  - Content masking (replace with ***MASKED***) for non-strict mode
  - Path traversal prevention
  - .gitignore / .aiignore rule parsing and matching
  - CODECORTEX_SECURITY_STRICT env toggle:
      false (default) — mask sensitive content, block vulgar
      true — block ALL sensitive content and vulgar entirely

:project: CodeCortex
:package: Services.SecurityFilter
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
"""
from __future__ import annotations

import logging
import os
import re
import stat
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("CodeCortex.SecurityFilter")


# ────────────────────────────────────────────────────────────
# ENV Config
# ────────────────────────────────────────────────────────────
def _is_strict_mode() -> bool:
    """Check CODECORTEX_SECURITY_STRICT env var."""
    raw = os.getenv("CODECORTEX_SECURITY_STRICT", "false").strip().lower()
    return raw in ("1", "true", "yes", "on")


# ────────────────────────────────────────────────────────────
# Sensitive File Extensions (always blocked, no masking)
# ────────────────────────────────────────────────────────────
SENSITIVE_EXTENSIONS: Set[str] = {
    # Environment / secrets
    ".env", ".env.local", ".env.production", ".env.development",
    ".env.staging", ".env.test", ".env.example",
    ".secret", ".secrets",
    # Keys & certificates
    ".key", ".pem", ".p12", ".pfx", ".jks", ".keystore", ".crt", ".cert",
    ".cer", ".ca-bundle", ".p7b", ".p7c", ".der",
    # Credentials
    ".credentials", ".cred", ".credential",
    ".netrc", ".pgpass", ".my.cnf",
    # Tokens
    ".token", ".tokens",
    # SQL dumps / database exports
    ".sql", ".sqlite", ".sqlite3", ".db", ".dump", ".backup",
    # Config with secrets
    ".kubeconfig", ".dockerconfigjson",
    ".npmrc", ".yarnrc",
    # Terraform state (contains plaintext secrets)
    ".tfstate", ".tfstate.backup",
    # AWS
    ".aws", ".aws.json",
    # Firebase
    ".firebase", ".firebaserc", ".google-services.json",
    ".google-services.json",
    # Corporate VPN / network configs
    ".ovpn", ".conf",
    # Log files (may contain PII / secrets)
    ".log",
}

# Files that are ALWAYS blocked regardless of extension
SENSITIVE_EXACT_NAMES: Set[str] = {
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    "id_rsa.pub", "id_dsa.pub", "id_ecdsa.pub", "id_ed25519.pub",
    "authorized_keys", "known_hosts",
    "credentials.json", "credentials.yaml", "credentials.yml",
    "credential.json", "secrets.json", "secrets.yaml", "secrets.yml",
    "secret.json", "secret.yaml",
    "service_account.json", "service-account.json",
    "config.json", "settings.json", "local.json",
    "appsettings.json", "appsettings.Development.json",
    "oauth2.json", "oauth2client.json",
    "client_secret.json", "client-secret.json",
    "passwd", "shadow", "htpasswd",
    "tokens.json", "token.json",
    "access_token", "refresh_token",
    "github_token", "gitlab_token",
    "slack_token", "discord_token",
    "vault.yml", "vault.yaml", "vault.json",
    "sops.yaml", "sops.yml",
    "master.key", "credentials.yml.enc",
    ".env", ".env.local",
}

# Substrings in file paths that indicate sensitivity
SENSITIVE_PATH_SUBSTRINGS: Set[str] = {
    "secret", "credential", "cred", "token", "key", "password",
    "passwd", "auth", "oauth", "jwt",
    ".git/config", ".git-credentials",
    "/secrets/", "/secret/", "/credentials/", "/tokens/",
    "/certs/", "/certificates/", "/keys/",
    ".config/store/", ".config/git/",
}


# ────────────────────────────────────────────────────────────
# Pattern type: (name, description, severity, compiled_regex)
# Severity: "low" | "medium" | "high" | "critical" | "vulgar"
# ────────────────────────────────────────────────────────────

PatternEntry = Tuple[str, str, str, re.Pattern]

MASK_PLACEHOLDER = "***MASKED***"


def _compile_sensitive_patterns() -> Tuple[List[PatternEntry], List[PatternEntry]]:
    """
    Compile all content detection patterns.

    Returns (sensitive_patterns, vulgar_patterns).
    sensitive_patterns — matched content is masked or blocked per config.
    vulgar_patterns — matched content is ALWAYS blocked, never shown.
    """
    sensitive: List[PatternEntry] = [
        # ── Critical: Private Keys ──
        ("private_key", "Private Key (PEM)", "critical", re.compile(
            r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'
        )),
        ("ssh_private_key", "SSH Private Key", "critical", re.compile(
            r'-----BEGIN OPENSSH PRIVATE KEY-----'
        )),
        ("pgp_private_key", "PGP Private Key", "critical", re.compile(
            r'-----BEGIN PGP PRIVATE KEY BLOCK-----'
        )),

        # ── Critical: Tokens ──
        ("github_token", "GitHub Token", "critical", re.compile(
            r'(?i)(ghp_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9_\-]{30,}'
        )),
        ("jwt", "JWT Token", "critical", re.compile(
            r'eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}'
        )),
        ("slack_token", "Slack Token", "critical", re.compile(
            r'(?i)(xox[baprs]-[A-Za-z0-9\-]{10,}|slack_token)'
        )),
        ("stripe_live", "Stripe Live Key", "critical", re.compile(
            r'(?i)(sk_live_|pk_live_)[A-Za-z0-9_\-]{10,}'
        )),
        ("bearer_hardcoded", "Bearer token (hardcoded)", "critical", re.compile(
            r'(?i)(Bearer\s+[A-Za-z0-9_\-\.]{20,}|authorization:\s*Bearer\s+[A-Za-z0-9_\-\.]{20,})'
        )),
        ("docker_auth", "Docker config auth", "critical", re.compile(
            r'"auth"\s*:\s*"[A-Za-z0-9+/=]{20,}"'
        )),

        # ── High: Connection Strings ──
        ("pg_conn", "PostgreSQL Connection String", "high", re.compile(
            r'(?i)(postgres(ql)?://[A-Za-z0-9_\-]+:[^@]+@[A-Za-z0-9_\-\.]+)'
        )),
        ("mysql_conn", "MySQL Connection String", "high", re.compile(
            r'(?i)(mysql://[A-Za-z0-9_\-]+:[^@]+@[A-Za-z0-9_\-\.]+)'
        )),
        ("mongodb_conn", "MongoDB Connection String", "high", re.compile(
            r'(?i)(mongodb(\+srv)?://[A-Za-z0-9_\-]+:[^@]+@[A-Za-z0-9_\-\.]+)'
        )),
        ("redis_conn", "Redis Connection String", "high", re.compile(
            r'(?i)(redis://:?[^@]+@[A-Za-z0-9_\-\.]+)'
        )),
        ("jdbc_url", "JDBC URL with creds", "high", re.compile(
            r'(?i)jdbc:[a-z]+://[A-Za-z0-9_\-]+:[^@]+@'
        )),

        # ── High: API Keys ──
        ("aws_key", "AWS Access Key", "high", re.compile(
            r'(?i)(AKIA[0-9A-Z]{16}|aws_access_key_id|aws_secret_access_key)'
        )),
        ("gcp_key", "GCP Service Account", "high", re.compile(
            r'"private_key_id"\s*:\s*"[A-Za-z0-9_\-]{20,}"'
        )),
        ("azure_key", "Azure Key", "high", re.compile(
            r'(?i)(azure_|AZURE_)[A-Za-z0-9_\-]{20,}'
        )),
        ("gitlab_token", "GitLab Token", "high", re.compile(
            r'(?i)(glpat-|gitlab_token|gitlab_access_token)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{10,}["\']?'
        )),
        ("stripe_test", "Stripe Test Key", "high", re.compile(
            r'(?i)(sk_test_|pk_test_)[A-Za-z0-9_\-]{10,}'
        )),
        ("firebase_key", "Firebase Key", "high", re.compile(
            r'(?i)(AIza[A-Za-z0-9_\-]{10,}|firebase_secret|FIREBASE_SECRET)'
        )),
        ("telegram_bot", "Telegram Bot Token", "high", re.compile(
            r'(?i)(\d{8,10}:[A-Za-z0-9_\-]{30,}|telegram_bot_token)'
        )),
        ("slack_webhook", "Slack Webhook URL", "high", re.compile(
            r'(?i)https?://hooks\.slack\.com/services/[A-Za-z0-9/]{20,}'
        )),
        ("twilio_key", "Twilio Key", "high", re.compile(
            r'(?i)(SK[A-Z0-9]{32}|TWILIO_AUTH_TOKEN|twilio_auth_token)'
        )),
        ("cloudflare_api", "Cloudflare API Token", "high", re.compile(
            r'(?i)(cloudflare_api|CF_API|cloudflare_token)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{20,}["\']?'
        )),

        # ── Medium: Passwords & Secrets ──
        ("password", "Password assignment", "medium", re.compile(
            r'(?i)(password|passwd|pwd)\s*[:=]\s*["\'][^"\']{4,}["\']'
        )),
        ("api_key", "API keys (generic)", "medium", re.compile(
            r'(?i)(?:api[_-]?key|apikey|api[_-]?secret|api_secret)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{16,}["\']?'
        )),
        ("generic_secret", "Generic secret assignment", "medium", re.compile(
            r'(?i)(secret|secret_key|private_key|encryption_key)\s*[:=]\s*["\'][A-Za-z0-9_\-]{16,}["\']'
        )),
        ("github_old_token", "GitHub (old) Token", "medium", re.compile(
            r'(?i)(github_token|github_access_token)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{20,}["\']?'
        )),
        ("discord_token", "Discord Token", "medium", re.compile(
            r'(?i)(discord_token|discord_bot_token)\s*[:=]\s*["\']?[A-Za-z0-9_\-\.]{20,}["\']?'
        )),
        ("email_creds", "Email credentials", "medium", re.compile(
            r'(?i)(smtp_password|imap_password|email_password|mail_password)\s*[:=]\s*["\'][^"\']+["\']'
        )),
        ("npm_token", "NPM Token", "medium", re.compile(
            r'(?i)(npm_token|npm_auth_token|_authToken)\s*[:=]\s*["\'][A-Za-z0-9_\-]{20,}["\']'
        )),
        ("heroku_api", "Heroku API Key", "medium", re.compile(
            r'(?i)(heroku_api_key|HEROKU_API_KEY)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{20,}["\']?'
        )),
        ("sonar_token", "SonarQube Token", "medium", re.compile(
            r'(?i)(sonar_token|sonarqube_token|SONAR_TOKEN)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{20,}["\']?'
        )),
        ("datadog_key", "Datadog API Key", "medium", re.compile(
            r'(?i)(datadog_api_key|datadog_app_key|DD_API_KEY)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{20,}["\']?'
        )),
        ("newrelic_key", "New Relic API Key", "medium", re.compile(
            r'(?i)(new_relic_license_key|newrelic_api_key|NEW_RELIC)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{20,}["\']?'
        )),
        ("sendgrid_key", "SendGrid API Key", "medium", re.compile(
            r'(?i)(sendgrid_api_key|SENDGRID_API_KEY)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{20,}["\']?'
        )),
        ("mailgun_key", "Mailgun API Key", "medium", re.compile(
            r'(?i)(mailgun_api_key|mailgun_private_key|MAILGUN_API)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{20,}["\']?'
        )),
        ("s3_creds", "S3 Access Key", "medium", re.compile(
            r'(?i)(s3_access_key|s3_secret_key|aws_access_key|aws_secret_key)'
        )),

        # ── Low: PII & Internal Info ──
        ("ssn", "US Social Security Number", "low", re.compile(
            r'\b\d{3}-\d{2}-\d{4}\b'
        )),
        ("credit_card", "Credit Card Number", "low", re.compile(
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
        )),
        ("ip_private", "Private IP Address", "low", re.compile(
            r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b'
        )),
    ]

    # ── Vulgar / Inappropriate Content (ALWAYS blocked) ──
    vulgar: List[PatternEntry] = [
        ("explicit_content", "Explicit/Inappropriate content", "vulgar", re.compile(
            r'(?i)\b(?:NSFW|explicit[_-]?content|adult[_-]?content|xxx)\b'
        )),
    ]

    return sensitive, vulgar


# Lazy-compile on first use
_COMPILED_SENSITIVE: Optional[List[PatternEntry]] = None
_COMPILED_VULGAR: Optional[List[PatternEntry]] = None


def _get_patterns() -> Tuple[List[PatternEntry], List[PatternEntry]]:
    global _COMPILED_SENSITIVE, _COMPILED_VULGAR
    if _COMPILED_SENSITIVE is None or _COMPILED_VULGAR is None:
        _COMPILED_SENSITIVE, _COMPILED_VULGAR = _compile_sensitive_patterns()
    return _COMPILED_SENSITIVE, _COMPILED_VULGAR


# ────────────────────────────────────────────────────────────
# .gitignore / .aiignore Parser
# ────────────────────────────────────────────────────────────

class IgnoreRule:
    """A single ignore pattern parsed from .gitignore / .aiignore."""

    __slots__ = ("pattern", "negate", "dir_only", "anchored", "raw")

    def __init__(self, pattern: str, negate: bool = False):
        self.raw = pattern
        self.negate = negate
        self.dir_only = pattern.endswith("/")
        clean = pattern.rstrip("/") if self.dir_only else pattern
        # Anchored if contains "/" (not at end) or starts with "/"
        self.anchored = "/" in clean or clean.startswith("/")
        # Remove leading "/" for anchored patterns
        if clean.startswith("/"):
            clean = clean[1:]
        # Convert gitignore glob to regex
        self.pattern = self._glob_to_regex(clean)

    @staticmethod
    def _glob_to_regex(pat: str) -> re.Pattern:
        """Convert a gitignore glob pattern to a compiled regex."""
        parts = []
        i = 0
        while i < len(pat):
            c = pat[i]
            if c == "*":
                if i + 1 < len(pat) and pat[i + 1] == "*":
                    # ** matches everything
                    parts.append(".*")
                    i += 2
                    # Skip any following /
                    if i < len(pat) and pat[i] == "/":
                        i += 1
                else:
                    # * matches anything except /
                    parts.append("[^/]*")
                    i += 1
            elif c == "?":
                parts.append("[^/]")
                i += 1
            elif c == "[":
                # Character class [...] 
                end = pat.find("]", i)
                if end == -1:
                    parts.append(re.escape(c))
                    i += 1
                else:
                    parts.append(pat[i:end + 1])
                    i = end + 1
            elif c in ".^$+{}()|\\":
                parts.append("\\" + c)
                i += 1
            else:
                parts.append(c)
                i += 1
        return re.compile("^" + "".join(parts) + "$")

    def matches(self, rel_path: str, is_dir: bool = False) -> bool:
        """Check if a relative path matches this ignore rule."""
        if self.dir_only and not is_dir:
            return False
        if self.anchored:
            return bool(self.pattern.search(rel_path))
        # Match against basename or any component
        if bool(self.pattern.search(rel_path)):
            return True
        # Also check each path component
        for part in Path(rel_path).parts:
            if bool(self.pattern.search(part)):
                return True
        return False

    def __repr__(self) -> str:
        return f"IgnoreRule(negate={self.negate}, pattern={self.raw})"


def parse_ignore_file(filepath: str) -> List[IgnoreRule]:
    """Parse a .gitignore or .aiignore file into a list of rules."""
    rules: List[IgnoreRule] = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("\\!"):
                    # Escaped literal "!"
                    line = "!" + line[2:]
                if line.startswith("!"):
                    rules.append(IgnoreRule(line[1:], negate=True))
                else:
                    rules.append(IgnoreRule(line, negate=False))
    except (FileNotFoundError, PermissionError):
        pass
    except Exception as e:
        logger.warning("ignore|parse_error|file=%s|error=%s", filepath, str(e)[:80])
    return rules


# ────────────────────────────────────────────────────────────
# SecurityFilter
# ────────────────────────────────────────────────────────────

class SecurityFilter:
    """
    Comprehensive security filter for filesystem search.

    Combines:
      - Sensitive file detection (by name, extension, path substring) [always blocked]
      - Sensitive content detection with severity (critical/high/medium/low)
        • Default mode: mask content → replace with ***MASKED***
        • Strict mode (CODECORTEX_SECURITY_STRICT=true): block entirely
      - Vulgar/inappropriate content detection [ALWAYS blocked, never shown]
      - .gitignore and .aiignore rule enforcement
      - Path traversal prevention
    """

    def __init__(self, project_root: Optional[str] = None):
        self._project_root: Optional[Path] = None
        if project_root:
            self._project_root = Path(project_root).resolve(strict=False)

        # Parsed ignore rules
        self._gitignore_rules: List[IgnoreRule] = []
        self._aiignore_rules: List[IgnoreRule] = []
        self._ignore_loaded = False

        # Strict mode from env
        self._strict = _is_strict_mode()

        # Compiled patterns
        self._sensitive_patterns, self._vulgar_patterns = _get_patterns()
        self._mask_placeholder = MASK_PLACEHOLDER

        logger.debug("security|init|strict=%s|root=%s", self._strict, self._project_root)

    # ── Config ──────────────────────────────────────────

    @property
    def strict_mode(self) -> bool:
        return self._strict

    def set_strict_mode(self, enabled: bool) -> None:
        self._strict = enabled

    @property
    def project_root(self) -> Optional[Path]:
        return self._project_root

    @project_root.setter
    def project_root(self, value: str) -> None:
        self._project_root = Path(value).resolve(strict=False)

    # ── Ignore file loading ─────────────────────────────

    def load_ignore_files(self, force: bool = False) -> None:
        """Load .gitignore and .aiignore from project root."""
        if self._ignore_loaded and not force:
            return
        self._gitignore_rules = []
        self._aiignore_rules = []
        if self._project_root:
            gitignore_path = str(self._project_root / ".gitignore")
            self._gitignore_rules = parse_ignore_file(gitignore_path)
            aiignore_path = str(self._project_root / ".aiignore")
            self._aiignore_rules = parse_ignore_file(aiignore_path)
            logger.debug(
                "ignore|loaded|gitignore=%d|aiignore=%d|root=%s",
                len(self._gitignore_rules), len(self._aiignore_rules),
                self._project_root,
            )
        self._ignore_loaded = True

    def force_reload_ignore_files(self) -> None:
        """Force re-load of ignore files."""
        self._ignore_loaded = False
        self.load_ignore_files(force=True)

    # ── Path validation ─────────────────────────────────

    def is_path_allowed(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a file path is allowed (stays within project root).

        Returns (allowed, reason) where reason is None if allowed.
        """
        if not self._project_root:
            return True, None
        try:
            resolved = Path(file_path).resolve(strict=False)
        except (OSError, ValueError, RuntimeError):
            return False, "Path resolution failed"
        root_str = str(self._project_root).rstrip("\\/")
        file_str = str(resolved).rstrip("\\/")
        if not file_str.startswith(root_str):
            return False, f"Path traversal denied: {file_path} is outside project root {self._project_root}"
        return True, None

    # ── Sensitive file detection (always blocked) ───────

    def is_sensitive_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a file path is sensitive (by name, extension, or path substring).

        Returns (is_sensitive, reason) where reason is None if not sensitive.
        These files are ALWAYS blocked regardless of strict mode.
        """
        try:
            p = Path(file_path)
        except Exception:
            return False, None

        name = p.name
        ext = p.suffix.lower()
        parent_str = str(p.parent).lower()

        if name in SENSITIVE_EXACT_NAMES:
            return True, f"Sensitive file name: {name}"

        if ext in SENSITIVE_EXTENSIONS:
            return True, f"Sensitive file extension: {ext}"

        if name.startswith(".env") and ext in {".local", ".production", ".development", ".staging", ".test", ""}:
            return True, f"Sensitive environment file: {name}"

        name_lower = name.lower()
        for substr in SENSITIVE_PATH_SUBSTRINGS:
            if substr in parent_str or substr in name_lower:
                return True, f"Sensitive path substring: {substr}"

        return False, None

    # ── Vulgar content detection (ALWAYS blocked) ───────

    def contains_vulgar_content(self, text: str) -> Tuple[bool, List[str]]:
        """
        Scan text for vulgar/inappropriate content.

        Returns (has_vulgar, list_of_findings).
        Files with vulgar content are NEVER shown in search results.
        """
        if len(text) > 500_000:
            return False, []
        findings: List[str] = []
        for name, description, severity, pattern in self._vulgar_patterns:
            try:
                if pattern.search(text):
                    findings.append(f"Vulgar content detected: {description} ({name})")
            except Exception:
                continue
        return len(findings) > 0, findings

    # ── Sensitive content detection ─────────────────────

    def detect_sensitive_content(self, text: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Scan text for sensitive content with severity levels.

        Returns (has_sensitive, list_of_findings) where each finding has:
          - name: pattern name
          - description: human-readable description
          - severity: "low" | "medium" | "high" | "critical"
        """
        if len(text) > 500_000:
            return False, []
        findings: List[Dict[str, Any]] = []
        for name, description, severity, pattern in self._sensitive_patterns:
            try:
                if pattern.search(text):
                    findings.append({
                        "name": name,
                        "description": f"{description} ({name})",
                        "severity": severity,
                    })
            except Exception:
                continue
        return len(findings) > 0, findings

    def contains_sensitive_content(self, text: str) -> Tuple[bool, List[str]]:
        """Legacy compat: returns (bool, list_of_reason_strings)."""
        found, findings = self.detect_sensitive_content(text)
        return found, [f["description"] for f in findings]

    # ── Content masking ─────────────────────────────────

    def mask_sensitive_content(self, text: str) -> Tuple[str, bool, List[str]]:
        """
        Replace all sensitive content with ***MASKED*** placeholders.

        Never masks vulgar content — that should be blocked entirely.

        Returns (masked_text, was_masked, list_of_findings).
        """
        if not text or len(text) > 500_000:
            return text, False, []

        masked = text
        was_masked = False
        all_findings: List[str] = []

        for name, description, severity, pattern in self._sensitive_patterns:
            try:
                matches = list(pattern.finditer(masked))
                for m in reversed(matches):
                    start, end = m.start(), m.end()
                    # Only mask actual secret values (skip short markers)
                    if end - start >= 6:
                        masked = masked[:start] + self._mask_placeholder + masked[end:]
                        was_masked = True
                if matches:
                    all_findings.append(f"{description} ({name}) [{severity}]")
            except Exception:
                continue

        return masked, was_masked, all_findings

    # ── Content processing (unified) ────────────────────

    def process_content(self, text: str) -> Dict[str, Any]:
        """
        Process content through the full security pipeline.

        Returns dict:
          - action: "allow" | "mask" | "block"
          - text: masked text if action="mask", original if "allow", empty if "block"
          - reasons: list[str] explaining actions taken
          - findings: list of detailed findings
        """
        result: Dict[str, Any] = {
            "action": "allow",
            "text": text,
            "reasons": [],
            "findings": [],
        }

        if not text:
            return result

        # 1. Check vulgar (ALWAYS block — never shown)
        has_vulgar, vulgar_findings = self.contains_vulgar_content(text)
        if has_vulgar:
            result["action"] = "block"
            result["reasons"].extend(vulgar_findings)
            result["findings"].extend(vulgar_findings)
            result["text"] = ""
            return result

        # 2. Check sensitive content
        has_sensitive, _findings = self.detect_sensitive_content(text)
        if not has_sensitive:
            return result

        if self._strict:
            # Strict mode: block ALL sensitive content
            result["action"] = "block"
            result["reasons"].append("Strict mode: sensitive content blocked entirely")
            result["findings"].extend([f["description"] for f in _findings])
            result["text"] = ""
        else:
            # Default mode: mask sensitive content
            masked_text, was_masked, mask_findings = self.mask_sensitive_content(text)
            if was_masked:
                result["action"] = "mask"
                result["text"] = masked_text
                result["reasons"].append("Sensitive content masked")
                result["findings"].extend(mask_findings)

        return result

    # ── Ignore check ────────────────────────────────────

    def is_ignored(self, rel_path: str, is_dir: bool = False) -> bool:
        """
        Check if a relative path is ignored by .gitignore or .aiignore.

        .gitignore semantics: last matching rule wins.
        """
        self.load_ignore_files()

        ignored = False

        for rule in self._gitignore_rules:
            if rule.matches(rel_path, is_dir):
                ignored = not rule.negate

        for rule in self._aiignore_rules:
            if rule.matches(rel_path, is_dir):
                ignored = not rule.negate

        return ignored

    # ── Full file check ─────────────────────────────────

    def check_file(self, file_path: str, content: Optional[str] = None,
                   rel_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Run ALL security checks on a file.

        Returns a dict with:
          allowed: bool
          reasons: list[str]  (why it was blocked/masked)
          details: dict       (extra info)
          content_action: "allow" | "mask" | "block" (content handling)
          masked_content: str | None (masked version if action="mask")
        """
        result: Dict[str, Any] = {
            "allowed": True,
            "reasons": [],
            "details": {},
            "content_action": "allow",
            "masked_content": None,
        }

        # 1. Path allowed (project root)
        allowed, reason = self.is_path_allowed(file_path)
        if not allowed:
            result["allowed"] = False
            result["reasons"].append(reason or "Path not allowed")
            return result

        # 2. Sensitive file
        is_sensitive, reason = self.is_sensitive_file(file_path)
        if is_sensitive:
            result["allowed"] = False
            result["reasons"].append(reason or "Sensitive file")
            result["details"]["sensitive_file"] = True

        # 3. Ignore rules
        effective_rel = rel_path or self._to_rel_path(file_path)
        if effective_rel and self.is_ignored(effective_rel):
            result["allowed"] = False
            result["reasons"].append(f"Ignored by .gitignore/.aiignore: {effective_rel}")
            result["details"]["ignored"] = True

        # 4. Content security (vulgar → block, sensitive → mask/block per strict)
        if content is not None:
            processed = self.process_content(content)
            if processed["action"] == "block":
                result["allowed"] = False
                result["reasons"].extend(processed["reasons"])
                result["details"]["content"] = processed["findings"]
                result["content_action"] = "block"
            elif processed["action"] == "mask":
                # Default mode: content is masked but file IS allowed
                result["reasons"].extend(processed["reasons"])
                result["details"]["content"] = processed["findings"]
                result["content_action"] = "mask"
                result["masked_content"] = processed["text"]

        return result

    # ── Utilities ───────────────────────────────────────

    def _to_rel_path(self, abs_path: str) -> Optional[str]:
        """Convert absolute path to relative (w.r.t. project root)."""
        if not self._project_root:
            return None
        try:
            return str(Path(abs_path).relative_to(self._project_root))
        except ValueError:
            return None

    @classmethod
    def get_default_gitignore_rules(cls) -> List[IgnoreRule]:
        """Return default built-in ignore patterns for common noise directories."""
        patterns = [
            ".git/",
            "__pycache__/",
            "node_modules/",
            ".venv/",
            "venv/",
            "dist/",
            "build/",
            ".next/",
            ".vscode/",
            ".idea/",
            "target/",
            ".tox/",
            ".eggs/",
            "*.pyc",
            "*.pyo",
            "*.so",
            "*.dll",
            "*.dylib",
            ".DS_Store",
            "Thumbs.db",
        ]
        return [IgnoreRule(p) for p in patterns]
