"""
SVN.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Svn
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Filesystem-v1.0
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from pathlib import Path
import os
import subprocess
import shutil
import re
from src.core import ApiError


from src.core.utils.path import norm_path as _norm


_CRED_RE_USERPASS = re.compile(r"(?i)(https?://)([^/@:\s]+):([^@/\s]*)@")
_CRED_RE_TOKEN = re.compile(r"(?i)(https?://)([^/@\s]+)@")


def _redact_credentials(text: str) -> str:
    if not text:
        return ""
    redacted = _CRED_RE_USERPASS.sub(r"\1***:***@", text)
    return _CRED_RE_TOKEN.sub(r"\1***@", redacted)


SVN_SUBCOMMANDS = {
    "checkout", "co", "update", "up", "commit", "ci",
    "add", "status", "stat", "log", "diff", "di",
    "info", "revert", "cleanup", "lock", "unlock",
    "propset", "pset", "propget", "pget", "proplist", "plist",
    "import", "export", "resolve", "mkdir", "delete", "del",
    "copy", "cp", "move", "mv", "rename", "ren",
    "list", "ls", "switch", "sw", "merge",
}


class DiskSvn:
    """Centralized SVN operations for the fs_svn MCP tool.
    SVN is optional — all methods gracefully return None/False
    when svn CLI is unavailable.
    """

    _svn_available: Optional[bool] = None
    _root_cache: Dict[str, Optional[str]] = {}

    @classmethod
    def is_svn_available(cls) -> bool:
        if cls._svn_available is None:
            cls._svn_available = shutil.which("svn") is not None
        return cls._svn_available

    @classmethod
    def find_root(cls, path: Path) -> Optional[Path]:
        p = path.resolve()
        parent = p.parent if p.is_file() else p
        key = str(parent)
        if key in cls._root_cache:
            cached = cls._root_cache[key]
            return Path(cached) if cached else None
        current = parent
        for _ in range(20):
            if (current / ".svn").exists():
                cls._root_cache[key] = str(current)
                return current
            if current == current.parent:
                break
            current = current.parent
        cls._root_cache[key] = None
        return None

    @classmethod
    def clear_cache(cls) -> None:
        cls._svn_available = None
        cls._root_cache.clear()

    @classmethod
    def restore_file(cls, root: Path, path: Path) -> Dict[str, Any]:
        """Restore a corrupted/tracked file from SVN repository.

        Uses 'svn revert <file>' to restore the file to its last committed state.
        Works even if the working copy is corrupted.

        Returns:
            {'ok': True} on success.
            {'ok': False, 'error': str, 'reason': str} on failure.
        """
        if not cls.is_svn_available():
            return {'ok': False, 'error': 'svn CLI not available', 'reason': 'no_svn_cli'}
        try:
            rel = path.relative_to(root)
        except ValueError:
            return {'ok': False, 'error': f'File {path} is not under SVN root {root}',
                    'reason': 'path_not_in_repo'}
        if not cls.is_tracked(root, path):
            return {'ok': False, 'error': f'File {rel} is not tracked in SVN',
                    'reason': 'file_not_tracked'}
        try:
            result = subprocess.run(
                ["svn", "revert", str(rel)],
                cwd=str(root), capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                return {'ok': True, 'method': 'svn_revert'}
            return {
                'ok': False,
                'error': f'svn revert failed: {result.stderr.strip()}',
                'reason': 'svn_command_failed',
            }
        except subprocess.TimeoutExpired:
            return {'ok': False, 'error': 'svn revert timed out after 30s',
                    'reason': 'timeout'}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'reason': 'exception'}

    @classmethod
    def is_tracked(cls, root: Path, path: Path) -> bool:
        if not cls.is_svn_available():
            return False
        try:
            rel = path.relative_to(root)
            result = subprocess.run(
                ["svn", "info", str(rel)],
                cwd=str(root), capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def stage(cls, root: Path, path: Path) -> bool:
        if not cls.is_svn_available():
            return False
        try:
            rel = path.relative_to(root)
            is_tracked = cls.is_tracked(root, path)
            cmd = ["svn", "add", "--parents", str(rel)] if not is_tracked else ["svn", "add", "--force", str(rel)]
            result = subprocess.run(
                cmd, cwd=str(root), capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def stage_all(cls, root: Path, paths: List[Path]) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        for p in paths:
            results[str(p)] = cls.stage(root, p)
        return results

    @classmethod
    def ensure(cls, path: Path) -> Tuple[Optional[Path], bool]:
        if not cls.is_svn_available():
            return None, False
        root = cls.find_root(path)
        if not root:
            return None, False
        return root, cls.is_tracked(root, path)

    @classmethod
    def get_insights(cls, path: Path) -> Optional[Dict[str, Any]]:
        root = cls.find_root(path)
        if not root or not cls.is_svn_available():
            return None
        try:
            rel = path.relative_to(root)
            cwd = str(root)

            info = subprocess.run(
                ["svn", "info", str(rel)],
                cwd=cwd, capture_output=True, text=True, timeout=5,
            )
            log = subprocess.run(
                ["svn", "log", "-l", "1", "--quiet", str(rel)],
                cwd=cwd, capture_output=True, text=True, timeout=5,
            )

            data: Dict[str, Any] = {"repo_root": _norm(str(root))}

            if info.returncode == 0:
                for line in info.stdout.splitlines():
                    line = line.strip()
                    if ":" in line:
                        k, _, v = line.partition(":")
                        ks = k.strip().lower().replace(" ", "_")
                        vs = v.strip()
                        if ks == "url":
                            data["url"] = vs
                        elif ks == "revision":
                            try:
                                data["revision"] = int(vs)
                            except ValueError:
                                data["revision"] = vs
                        elif ks == "last_changed_rev":
                            try:
                                data["last_changed_rev"] = int(vs)
                            except ValueError:
                                data["last_changed_rev"] = vs
                        elif ks == "last_changed_author":
                            data["last_author"] = vs
                        elif ks == "last_changed_date":
                            data["last_changed_date"] = vs
                        elif ks == "relative_url":
                            data["relative_url"] = vs
                        elif ks == "repository_root":
                            data["repository_root"] = vs
                        elif ks == "node_kind":
                            data["node_kind"] = vs

            if log.returncode == 0 and log.stdout.strip():
                for line in log.stdout.splitlines():
                    m = re.match(r"r(\d+)\s*\|\s*(\S+)", line)
                    if m:
                        data["last_commit_revision"] = int(m.group(1))
                        data["last_commit_author"] = m.group(2)
                        break

            return data if len(data) > 1 else None
        except Exception:
            return None

    @classmethod
    def get_file_status(cls, root: Path, path: Path) -> Optional[Dict[str, str]]:
        if not cls.is_svn_available():
            return None
        try:
            rel = path.relative_to(root)
            result = subprocess.run(
                ["svn", "status", "--non-interactive", str(rel)],
                cwd=str(root), capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None
            line = result.stdout.strip()
            status_map = {
                "M": "modified", "A": "added", "D": "deleted",
                "R": "replaced", "C": "conflicted", "X": "external",
                "I": "ignored", "?": "untracked", "!": "missing",
                "~": "obstructed", " ": "unmodified",
            }
            svn_status = status_map.get(line[0], line[0]) if line else None
            props_status = status_map.get(line[1], line[1]) if len(line) > 1 else None
            return {
                "svn_status": svn_status,
                "props_status": props_status,
                "wc_status": "tracked" if svn_status and svn_status not in ("untracked",) else "untracked",
            }
        except Exception:
            return None

    @classmethod
    def execute(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        target = params.get("target", "")
        subcommand = params.get("subcommand", "")
        args = params.get("args") or []
        flags = params.get("flags") or {}
        dry_run = params.get("dry_run", False)
        timeout_seconds = params.get("timeout_seconds", 300)

        if not target:
            raise ApiError("target is required", status_code=400, error_code="REP_SVN_400")
        if not subcommand:
            raise ApiError("subcommand is required", status_code=400, error_code="REP_SVN_400")

        if not cls.is_svn_available():
            raise ApiError(
                "SVN CLI is not available. Install svn (Subversion) to use this tool.",
                status_code=500,
                error_code="REP_SVN_500",
            )

        is_remote_op = subcommand in ("checkout", "co", "import", "export")
        needs_wc = subcommand not in ("checkout", "co", "import", "export", "info", "list", "ls")

        resolved_target = target
        cwd = None

        if needs_wc:
            tp = Path(target).resolve()
            if tp.exists():
                root = cls.find_root(tp)
                if root:
                    cwd = str(root)
                    resolved_target = str(tp)
                else:
                    raise ApiError(
                        f"Not a Subversion working copy: {target}",
                        status_code=404,
                        error_code="REP_SVN_404",
                        details={"operation": subcommand, "target": _norm(Path(target).resolve())},
                    )
            else:
                raise ApiError(
                    f"Path does not exist: {target}",
                    status_code=404,
                    error_code="REP_SVN_404",
                    details={"operation": subcommand, "target": _norm(Path(target).resolve())},
                )

        cmd = ["svn", subcommand]
        for flag, value in flags.items():
            if value is True:
                cmd.append(flag)
            elif value is not False and value is not None:
                cmd.append(flag)
                cmd.append(str(value))

        if subcommand in ("checkout", "co") and not args:
            cmd.append(target)
        elif args:
            cmd.extend(args)
        elif needs_wc:
            cmd.append(resolved_target)

        if dry_run and subcommand in ("commit", "ci", "delete", "del", "mkdir", "import",
                                       "lock", "unlock", "propset", "pset", "copy", "cp",
                                       "move", "mv", "rename", "ren"):
            return {
                "status_code": 200,
                "message": f"DRY RUN: would execute `{_redact_credentials(' '.join(cmd))}`",
                "data": {
                    "operation": subcommand,
                    "command": _redact_credentials(" ".join(cmd)),
                    "target": _norm(Path(target).resolve()) if not is_remote_op else target,
                    "dry_run": True,
                },
            }

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True, text=True, timeout=timeout_seconds,
            )

            if result.returncode != 0:
                return cls._error_response(subcommand, result, target, cmd)

            return cls._success_response(subcommand, result, target, cmd)

        except subprocess.TimeoutExpired:
            raise ApiError(
                f"SVN command timed out after {timeout_seconds}s",
                status_code=408,
                error_code="REP_SVN_408",
                details={
                    "operation": subcommand,
                    "command": _redact_credentials(" ".join(cmd)),
                    "target": _norm(Path(target).resolve()) if not is_remote_op else target,
                },
            )
        except FileNotFoundError:
            raise ApiError("SVN CLI not found", status_code=500, error_code="REP_SVN_500")
        except Exception as e:
            raise ApiError(f"SVN execution error: {e}", status_code=500, error_code="REP_SVN_500")

    @classmethod
    def _success_response(cls, subcommand: str, result: subprocess.CompletedProcess,
                          target: str, cmd: List[str]) -> Dict[str, Any]:
        parser = cls._get_parser(subcommand)
        if parser:
            data = parser(result, target, cmd)
            return {
                "status_code": 200,
                "message": data.pop("_message", f"SVN {subcommand} completed"),
                "data": data,
            }
        return {
            "status_code": 200,
            "message": f"SVN {subcommand} completed",
            "data": {
                "operation": subcommand,
                "stdout": result.stdout.strip(),
            },
        }

    @classmethod
    def _error_response(cls, subcommand: str, result: subprocess.CompletedProcess,
                        target: str, cmd: List[str]) -> Dict[str, Any]:
        stderr = result.stderr.strip()
        data: Dict[str, Any] = {
            "operation": subcommand,
            "command": _redact_credentials(" ".join(cmd)),
            "target": _norm(Path(target).resolve()) if not target.startswith("svn://") and not target.startswith("http") else target,
        }

        if "not a working copy" in stderr.lower():
            raise ApiError("Not a Subversion working copy", status_code=404, error_code="REP_SVN_404", details=data)
        if "E170001" in stderr or "Authentication failed" in stderr:
            data["svn_error_code"] = "E170001"
            data["suggestion"] = "Check username/password or use --username with --password"
            raise ApiError(f"Authentication failed: {stderr}", status_code=401, error_code="REP_SVN_401", details=data)
        if "E155010" in stderr or "conflict" in stderr.lower():
            data["svn_error_code"] = "E155010"
            data["suggestion"] = "Resolve conflicts using 'svn resolve' or 'svn revert'"
            raise ApiError(f"Conflict detected: {stderr}", status_code=409, error_code="REP_SVN_409", details=data)
        if "E200033" in stderr or "locked" in stderr.lower():
            data["suggestion"] = "Run 'svn cleanup' to remove stale locks"
            raise ApiError(f"Working copy locked: {stderr}", status_code=423, error_code="REP_SVN_423", details=data)
        if "is not under version control" in stderr.lower():
            raise ApiError(stderr, status_code=404, error_code="REP_SVN_404", details=data)

        data["stderr"] = _redact_credentials(stderr)
        raise ApiError(data["stderr"] or "SVN command failed", status_code=400, error_code="REP_SVN_400", details=data)

    @classmethod
    def _get_parser(cls, subcommand: str):
        canonical = {
            "co": "checkout", "up": "update", "ci": "commit",
            "stat": "status", "di": "diff",
            "pset": "propset", "pget": "propget", "plist": "proplist",
            "cp": "copy", "mv": "move", "ren": "rename",
            "del": "delete", "ls": "list", "sw": "switch",
        }
        sc = canonical.get(subcommand, subcommand)
        parsers = {
            "checkout": cls._parse_checkout,
            "update": cls._parse_update,
            "commit": cls._parse_commit,
            "add": cls._parse_add,
            "status": cls._parse_status,
            "log": cls._parse_log,
            "diff": cls._parse_diff,
            "info": cls._parse_info,
            "revert": cls._parse_revert,
            "cleanup": cls._parse_cleanup,
            "lock": cls._parse_lock,
            "unlock": cls._parse_lock,
            "resolve": cls._parse_resolve,
        }
        return parsers.get(sc)

    @classmethod
    def _parse_checkout(cls, result: subprocess.CompletedProcess, target: str, cmd: List[str]) -> Dict[str, Any]:
        output = result.stderr.strip() or result.stdout.strip()
        data: Dict[str, Any] = {"operation": "checkout"}

        m = re.search(r"Checked out revision (\d+)", output)
        if m:
            data["revision"] = int(m.group(1))

        url = target if target.startswith("svn") or target.startswith("http") else ""
        if not url:
            for a in cmd:
                if a.startswith("http") or a.startswith("svn"):
                    url = a
                    break
        if url:
            data["url"] = url

        if len(cmd) > 2:
            last_arg = cmd[-1]
            if "/" in last_arg or "\\" in last_arg:
                data["local_path"] = _norm(Path(last_arg).resolve())
            else:
                data["local_path"] = _norm(Path.cwd() / last_arg) if last_arg else ""

        data["_message"] = output
        return data

    @classmethod
    def _parse_update(cls, result: subprocess.CompletedProcess, target: str, cmd: List[str]) -> Dict[str, Any]:
        output = result.stderr.strip() or result.stdout.strip()
        data: Dict[str, Any] = {"operation": "update", "details": []}

        m = re.search(r"Updated to revision (\d+)", output)
        if m:
            data["updated_revision"] = int(m.group(1))

        for line in output.splitlines():
            line = line.strip()
            if line and len(line) > 3 and line[0] in "A D U G C E!":
                status_map = {
                    "A": "added", "D": "deleted", "U": "updated",
                    "G": "merged", "C": "conflicted", "E": "existed",
                    "!": "missing",
                }
                status_code = line[0]
                path_part = line[1:].strip()
                if path_part:
                    data["details"].append({
                        "path": path_part,
                        "status": status_map.get(status_code, status_code),
                    })

        summary: Dict[str, int] = {}
        for d in data["details"]:
            s = d["status"]
            summary[s] = summary.get(s, 0) + 1
        data["summary"] = summary
        data["_message"] = output
        return data

    @classmethod
    def _parse_commit(cls, result: subprocess.CompletedProcess, target: str, cmd: List[str]) -> Dict[str, Any]:
        output = result.stderr.strip() or result.stdout.strip()
        data: Dict[str, Any] = {"operation": "commit"}

        m = re.search(r"Committed revision (\d+)", output)
        if m:
            data["new_revision"] = int(m.group(1))

        m = re.search(r"(\d+) lines?", output)
        if m:
            data["lines_changed"] = int(m.group(1))

        paths_sent = []
        if "Transmitting file data" in output:
            paths_sent.append("data transmitted")
        data["_message"] = output.replace("Transmitting file data", "").strip() or output
        return data

    @classmethod
    def _parse_add(cls, result: subprocess.CompletedProcess, target: str, cmd: List[str]) -> Dict[str, Any]:
        output = result.stderr.strip() or result.stdout.strip()
        data: Dict[str, Any] = {"operation": "add", "added_paths": []}

        for line in output.splitlines():
            line = line.strip()
            if line.startswith("A") or line.startswith("a"):
                path_part = line[1:].strip()
                if path_part:
                    data["added_paths"].append(path_part)

        data["_message"] = output
        return data

    @classmethod
    def _parse_status(cls, result: subprocess.CompletedProcess, target: str, cmd: List[str]) -> Dict[str, Any]:
        data: Dict[str, Any] = {"operation": "status", "entries": []}
        status_map = {
            " ": "unmodified",
            "M": "modified", "A": "added", "D": "deleted",
            "R": "replaced", "C": "conflicted", "X": "external",
            "I": "ignored", "?": "unversioned", "!": "missing",
            "~": "obstructed", "L": "locked",
        }

        wc_revision = ""
        for line in result.stdout.splitlines():
            line = line.rstrip()
            if not line or line.startswith("Status against revision"):
                m = re.search(r"revision:\s*(\d+)", line)
                if m:
                    wc_revision = m.group(1)
                continue

            if len(line) < 8:
                continue

            entry: Dict[str, Any] = {
                "status": status_map.get(line[0], line[0]),
                "props_status": status_map.get(line[1], line[1]) if len(line) > 1 else "",
                "locked": line[2] == "L",
                "added_history": line[3] == "+",
                "switched": line[4] == "S",
                "locked_other": line[5] == "K",
                "conflict_other": line[6] == "C",
                "path": line[7:].strip(),
            }

            is_verbose = "--verbose" in cmd or "-v" in cmd
            if is_verbose and len(line) > 7:
                parts = line[7:].split()
                if parts:
                    entry["path"] = parts[0]

            data["entries"].append(entry)

        if wc_revision:
            data["revision"] = int(wc_revision)

        summary: Dict[str, int] = {}
        for e in data["entries"]:
            s = e["status"]
            summary[s] = summary.get(s, 0) + 1
        data["summary"] = summary
        data["_message"] = f"Status retrieved ({len(data['entries'])} entries)"
        return data

    @classmethod
    def _parse_log(cls, result: subprocess.CompletedProcess, target: str, cmd: List[str]) -> Dict[str, Any]:
        data: Dict[str, Any] = {"operation": "log", "revisions": []}
        is_verbose = "--verbose" in cmd or "-v" in cmd

        current_rev: Optional[Dict[str, Any]] = None
        in_changed_paths = False
        changed_paths: List[Dict[str, str]] = []

        for line in result.stdout.splitlines():
            line = line.rstrip()

            m = re.match(r"r(\d+)\s*\|\s*(\S+)\s*\|\s*(.*?)\s*\|\s*(\d+)\s*(lines?)?", line)
            if m:
                if current_rev:
                    if is_verbose and changed_paths:
                        current_rev["changed_paths"] = changed_paths
                    data["revisions"].append(current_rev)
                current_rev = {
                    "revision": int(m.group(1)),
                    "author": m.group(2),
                    "date": m.group(3).strip(),
                    "lines": int(m.group(4)),
                    "message": "",
                }
                in_changed_paths = False
                changed_paths = []
                continue

            if is_verbose and current_rev:
                if line.strip() == "Changed paths:":
                    in_changed_paths = True
                    continue
                if in_changed_paths:
                    if not line.strip():
                        in_changed_paths = False
                        continue
                    if line.startswith(" ") and "/" in line:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            changed_paths.append({
                                "action": parts[0],
                                "path": parts[1],
                            })
                        elif len(parts) == 1:
                            changed_paths.append({"action": "M", "path": parts[0]})
                        continue

            if current_rev and not in_changed_paths:
                if current_rev["message"]:
                    current_rev["message"] += "\n" + line
                else:
                    current_rev["message"] = line

        if current_rev:
            if is_verbose and changed_paths:
                current_rev["changed_paths"] = changed_paths
            data["revisions"].append(current_rev)

        data["total"] = len(data["revisions"])
        data["_message"] = f"Log retrieved ({data['total']} revisions)"
        return data

    @classmethod
    def _parse_diff(cls, result: subprocess.CompletedProcess, target: str, cmd: List[str]) -> Dict[str, Any]:
        data: Dict[str, Any] = {"operation": "diff", "files": []}
        current_file: Optional[str] = None
        current_hunk: Optional[Dict[str, str]] = None
        current_content: List[str] = []

        for line in result.stdout.splitlines():
            m = re.match(r"Index:\s+(.+)", line)
            if m:
                if current_file and current_hunk is not None:
                    current_hunk["content"] = "\n".join(current_content)
                    data["files"][-1]["hunks"].append(current_hunk)
                elif current_file:
                    pass
                current_file = m.group(1)
                data["files"].append({"path": current_file, "status": "modified", "hunks": []})
                current_hunk = None
                current_content = []
                continue

            if line.startswith("@@") and current_file:
                if current_hunk is not None:
                    current_hunk["content"] = "\n".join(current_content)
                    data["files"][-1]["hunks"].append(current_hunk)
                current_hunk = {"line_range": line, "content": ""}
                current_content = []
                continue

            if line.startswith("==================================================================="):
                continue
            if line.startswith("--- ") or line.startswith("+++ "):
                continue

            if current_file:
                current_content.append(line)

        if current_file and current_hunk is not None:
            current_hunk["content"] = "\n".join(current_content)
            data["files"][-1]["hunks"].append(current_hunk)

        data["_message"] = f"Diff retrieved ({len(data['files'])} files)"
        return data

    @classmethod
    def _parse_info(cls, result: subprocess.CompletedProcess, target: str, cmd: List[str]) -> Dict[str, Any]:
        data: Dict[str, Any] = {"operation": "info"}
        for line in result.stdout.splitlines():
            line = line.strip()
            if ":" in line:
                key, _, value = line.partition(":")
                key_stripped = key.strip().lower().replace(" ", "_")
                value_stripped = value.strip()
                if key_stripped in ("path", "url", "relative_url", "repository_root", "node_kind",
                                    "schedule", "copy_from_url", "copy_from_rev", "uuid"):
                    data[key_stripped] = value_stripped
                elif key_stripped in ("revision", "last_changed_rev", "copy_from_rev"):
                    try:
                        data[key_stripped] = int(value_stripped)
                    except ValueError:
                        data[key_stripped] = value_stripped
                elif key_stripped == "last_changed_author":
                    data["last_changed_author"] = value_stripped
                else:
                    data[key_stripped] = value_stripped

        data["_message"] = "Repository info retrieved"
        return data

    @classmethod
    def _parse_revert(cls, result: subprocess.CompletedProcess, target: str, cmd: List[str]) -> Dict[str, Any]:
        output = result.stderr.strip() or result.stdout.strip()
        reverted: List[str] = []
        for line in output.splitlines():
            if "Reverted" in line:
                path_part = line.replace("Reverted", "").strip().rstrip(".")
                if path_part:
                    reverted.append(path_part)
        return {
            "operation": "revert",
            "reverted_paths": reverted,
            "_message": output,
        }

    @classmethod
    def _parse_cleanup(cls, result: subprocess.CompletedProcess, target: str, cmd: List[str]) -> Dict[str, Any]:
        output = result.stderr.strip() or result.stdout.strip()
        return {
            "operation": "cleanup",
            "_message": output or "Cleanup completed",
        }

    @classmethod
    def _parse_lock(cls, result: subprocess.CompletedProcess, target: str, cmd: List[str]) -> Dict[str, Any]:
        output = result.stderr.strip() or result.stdout.strip()
        locked: List[str] = []
        for line in output.splitlines():
            if "locked by user" in line:
                continue
            if line.strip():
                locked.append(line.strip())
        op = "lock" if "lock" in str(cmd) else "unlock"
        return {
            "operation": op,
            "locked_paths": locked if op == "lock" else [],
            "unlocked_paths": locked if op == "unlock" else [],
            "_message": output,
        }

    @classmethod
    def _parse_resolve(cls, result: subprocess.CompletedProcess, target: str, cmd: List[str]) -> Dict[str, Any]:
        output = result.stderr.strip() or result.stdout.strip()
        resolved: List[str] = []
        for line in output.splitlines():
            if "Resolved" in line:
                path_part = line.replace("Resolved", "").strip().rstrip(".")
                if path_part:
                    resolved.append(path_part)
        return {
            "operation": "resolve",
            "resolved_files": resolved,
            "_message": output,
        }
