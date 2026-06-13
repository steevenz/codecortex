"""
Centralized git operations for all fs_* tools and fs_git MCP tool.
    Git is optional — all methods gracefully return None/False
    when git CLI is unavailable or the path is not in a repo.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Git
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Filesystem-v1.0
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


class DiskGit:
    """Centralized git operations for filesystem tools."""

    _git_available: Optional[bool] = None
    _root_cache: Dict[str, Optional[str]] = {}

    @classmethod
    def is_git_available(cls) -> bool:
        if cls._git_available is None:
            cls._git_available = shutil.which("git") is not None
        return cls._git_available

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
            if (current / ".git").exists():
                cls._root_cache[key] = str(current)
                return current
            if current == current.parent:
                break
            current = current.parent
        cls._root_cache[key] = None
        return None

    @classmethod
    def is_tracked(cls, root: Path, path: Path) -> bool:
        if not cls.is_git_available():
            return False
        try:
            rel = path.relative_to(root)
            result = subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(rel)],
                cwd=str(root), capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def stage(cls, root: Path, path: Path) -> bool:
        if not cls.is_git_available():
            return False
        try:
            rel = path.relative_to(root)
            result = subprocess.run(
                ["git", "add", str(rel)],
                cwd=str(root), capture_output=True, text=True, timeout=10,
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
    def commit(cls, root: Path, message: str) -> bool:
        if not cls.is_git_available():
            return False
        try:
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=str(root), capture_output=True, text=True, timeout=30,
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def restore_file(cls, root: Path, path: Path) -> Dict[str, Any]:
        """Restore a corrupted/tracked file from git HEAD.

        Uses 'git checkout HEAD -- <file>' to restore the file to its
        last committed state. Works even if the working copy is corrupted.

        Returns:
            {'ok': True} on success.
            {'ok': False, 'error': str, 'reason': str} on failure.
        """
        if not cls.is_git_available():
            return {'ok': False, 'error': 'git CLI not available', 'reason': 'no_git_cli'}
        try:
            rel = path.relative_to(root)
        except ValueError:
            return {'ok': False, 'error': f'File {path} is not under repo root {root}',
                    'reason': 'path_not_in_repo'}
        if not cls.is_tracked(root, path):
            return {'ok': False, 'error': f'File {rel} is not tracked in git',
                    'reason': 'file_not_tracked'}
        try:
            # First try git restore (newer git)
            result = subprocess.run(
                ["git", "restore", "--source=HEAD", "--staged", "--worktree", "--", str(rel)],
                cwd=str(root), capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                return {'ok': True, 'method': 'git_restore'}
            # Fallback: git checkout HEAD -- <file> (older git)
            result = subprocess.run(
                ["git", "checkout", "HEAD", "--", str(rel)],
                cwd=str(root), capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                return {'ok': True, 'method': 'git_checkout'}
            return {
                'ok': False,
                'error': f'git restore/checkout failed: {result.stderr.strip()}',
                'reason': 'git_command_failed',
            }
        except subprocess.TimeoutExpired:
            return {'ok': False, 'error': 'git restore timed out after 30s',
                    'reason': 'timeout'}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'reason': 'exception'}

    @classmethod
    def get_insights(cls, path: Path) -> Optional[Dict[str, Any]]:
        root = cls.find_root(path)
        if not root or not cls.is_git_available():
            return None
        try:
            rel = path.relative_to(root)
            cwd = str(root)
            info = subprocess.run(
                ["git", "log", "-1", "--format=%H|%ae|%cI|%s", "--follow", "--", str(rel)],
                cwd=cwd, capture_output=True, text=True, timeout=5,
            )
            stats = subprocess.run(
                ["git", "log", "--numstat", "--format=COMMIT %H", "--follow", "--", str(rel)],
                cwd=cwd, capture_output=True, text=True, timeout=5,
            )
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=cwd, capture_output=True, text=True, timeout=5,
            )
            commit_hash = author = date = msg = ""
            if info.returncode == 0 and info.stdout.strip():
                parts = info.stdout.strip().split("|", 3)
                if len(parts) >= 4:
                    commit_hash, author, date, msg = parts[0], parts[1], parts[2], parts[3]
            commit_count = 0
            added = 0
            deleted = 0
            if stats.returncode == 0:
                for line in stats.stdout.splitlines():
                    if line.startswith("COMMIT "):
                        commit_count += 1
                    elif line.strip():
                        parts = line.split("\t")
                        if len(parts) >= 2:
                            try:
                                a = int(parts[0]) if parts[0] not in ("-", "") else 0
                                d = int(parts[1]) if parts[1] not in ("-", "") else 0
                                added += a
                                deleted += d
                            except ValueError:
                                pass
            return {
                "repo_root": _norm(str(root)),
                "current_branch": branch.stdout.strip() if branch.returncode == 0 else "",
                "last_commit_message": msg,
                "last_commit_date": date,
                "last_author": author,
                "commit_count": commit_count,
                "lines_added": added,
                "lines_deleted": deleted,
            }
        except Exception:
            return None

    @classmethod
    def ensure(cls, path: Path) -> Tuple[Optional[Path], bool]:
        if not cls.is_git_available():
            return None, False
        root = cls.find_root(path)
        if not root:
            return None, False
        return root, cls.is_tracked(root, path)

    @classmethod
    def clear_cache(cls) -> None:
        cls._git_available = None
        cls._root_cache.clear()

    @classmethod
    def get_file_status(cls, root: Path, path: Path) -> Optional[Dict[str, str]]:
        """Get git status for a single file relative to a repo root."""
        if not cls.is_git_available():
            return None
        try:
            rel = path.relative_to(root)
            result = subprocess.run(
                ["git", "status", "--porcelain", "--", str(rel)],
                cwd=str(root), capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None
            line = result.stdout.strip()
            if len(line) < 3:
                return None
            staged = line[0:1].strip() or None
            working = line[1:2].strip() or None
            status_map = {
                "M": "modified", "A": "added", "D": "deleted",
                "R": "renamed", "C": "copied", "U": "updated",
                "?": "untracked", "!": "ignored",
            }
            return {
                "staged_status": status_map.get(staged, staged),
                "working_status": status_map.get(working, working),
            }
        except Exception:
            return None

    @classmethod
    def validate_repo(cls, repo_path: str) -> Tuple[bool, str, Optional[str]]:
        """Validate that repo_path is a valid git repository.
        Returns (is_valid, message, git_version)."""
        p = Path(repo_path).resolve()
        if not p.exists():
            return False, f"Path does not exist: {repo_path}", None
        if not p.is_dir():
            return False, f"Path is not a directory: {repo_path}", None
        if not cls.is_git_available():
            return False, "Git CLI is not available on this system", None
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=str(p), capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return False, f"Not a git repository: {repo_path}", None
            git_root = result.stdout.strip()
            version = subprocess.run(
                ["git", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            git_ver = version.stdout.strip() if version.returncode == 0 else "unknown"
            return True, git_root, git_ver
        except Exception as e:
            return False, f"Git validation error: {e}", None

    @classmethod
    def execute(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a git subcommand with structured params.

        params:
            repo_path (str) - Required. Path to git repo root.
            subcommand (str) - Required. Git subcommand (init, status, add, commit, etc.)
            args (list) - Optional. Positional arguments for the subcommand.
            flags (dict) - Optional. Command line flags, e.g. {"--oneline": true, "-n": 10}
            dry_run (bool) - Optional. Simulate without executing (default false).
            timeout_seconds (int) - Optional. Timeout in seconds (default 300 for remote ops).
        """
        repo_path = params.get("repo_path", "")
        subcommand = params.get("subcommand", "")
        args = params.get("args") or []
        flags = params.get("flags") or {}
        dry_run = params.get("dry_run", False)
        timeout_seconds = params.get("timeout_seconds", 300)

        if not repo_path:
            raise ApiError("repo_path is required", status_code=400, error_code="REP_GIT_400")
        if not subcommand:
            raise ApiError("subcommand is required", status_code=400, error_code="REP_GIT_400")

        is_valid, message, git_ver = cls.validate_repo(repo_path)
        if not is_valid and subcommand not in ("init", "clone"):
            raise ApiError(
                message,
                status_code=404,
                error_code="REP_GIT_404",
                details={"repo_path": _norm(str(Path(repo_path).resolve()))},
            )
        if not cls.is_git_available() and subcommand not in ("init",):
            raise ApiError("Git CLI is not available", status_code=500, error_code="REP_GIT_500")

        git_root = message if is_valid else repo_path

        cmd = ["git", subcommand]
        cmd.extend(args)
        for flag, value in flags.items():
            if value is True:
                cmd.append(flag)
            elif value is not False and value is not None:
                cmd.append(flag)
                cmd.append(str(value))

        if dry_run:
            return {
                "status_code": 200,
                "message": f"DRY RUN: would execute `{_redact_credentials(' '.join(cmd))}`",
                "data": {
                    "operation": subcommand,
                    "command": _redact_credentials(" ".join(cmd)),
                    "repo_path": _norm(Path(repo_path).resolve()),
                    "dry_run": True,
                    "git_version": git_ver or "",
                },
            }

        try:
            timeout = timeout_seconds
            result = subprocess.run(
                cmd,
                cwd=str(Path(repo_path).resolve()),
                capture_output=True, text=True, timeout=timeout,
            )

            if result.returncode != 0:
                return cls._error_response(subcommand, result, repo_path, cmd)

            return cls._success_response(subcommand, result, repo_path, cmd, git_ver)

        except subprocess.TimeoutExpired:
            raise ApiError(
                f"Git command timed out after {timeout_seconds}s",
                status_code=408,
                error_code="REP_GIT_408",
                details={
                    "operation": subcommand,
                    "command": _redact_credentials(" ".join(cmd)),
                    "repo_path": _norm(Path(repo_path).resolve()),
                },
            )
        except FileNotFoundError:
            raise ApiError("Git CLI not found", status_code=500, error_code="REP_GIT_500")
        except Exception as e:
            raise ApiError(f"Git execution error: {e}", status_code=500, error_code="REP_GIT_500")

    @classmethod
    def _success_response(cls, subcommand: str, result: subprocess.CompletedProcess,
                          repo_path: str, cmd: List[str], git_ver: Optional[str]) -> Dict[str, Any]:
        parser = cls._get_parser(subcommand)
        if parser:
            data = parser(result, repo_path, cmd)
            return {
                "status_code": 200,
                "message": data.pop("_message", f"Git {subcommand} completed"),
                "data": data,
            }
        return {
            "status_code": 200,
            "message": f"Git {subcommand} completed",
            "data": {
                "operation": subcommand,
                "repo_path": _norm(Path(repo_path).resolve()),
                "git_version": git_ver or "",
                "stdout": result.stdout.strip(),
            },
        }

    @classmethod
    def _error_response(cls, subcommand: str, result: subprocess.CompletedProcess,
                        repo_path: str, cmd: List[str]) -> Dict[str, Any]:
        stderr = result.stderr.strip()
        data: Dict[str, Any] = {
            "operation": subcommand,
            "command": _redact_credentials(" ".join(cmd)),
            "repo_path": _norm(Path(repo_path).resolve()),
        }

        if "not a git repository" in stderr.lower():
            raise ApiError("Not a git repository", status_code=404, error_code="REP_GIT_404", details=data)
        if "conflict" in stderr.lower():
            data["conflicts"] = cls._parse_conflicts(stderr)
            data["resolution_hint"] = "Resolve conflicts using 'git add' or 'git mergetool', then commit."
            raise ApiError(f"Merge conflict: {stderr}", status_code=409, error_code="REP_GIT_409", details=data)
        if "did not match any file" in stderr.lower():
            raise ApiError(stderr, status_code=404, error_code="REP_GIT_404", details=data)
        if "pathspec" in stderr.lower() and "did not match" in stderr.lower():
            raise ApiError(stderr, status_code=404, error_code="REP_GIT_404", details=data)
        if "nothing to commit" in stderr.lower():
            return {"status_code": 200, "message": "Nothing to commit, working tree clean", "data": {"operation": subcommand}}
        if "already up-to-date" in stderr.lower() or "already up to date" in stderr.lower():
            return {"status_code": 200, "message": "Already up-to-date", "data": {"operation": subcommand}}

        data["stderr"] = _redact_credentials(stderr)
        raise ApiError(data["stderr"] or "Git command failed", status_code=400, error_code="REP_GIT_400", details=data)

    @classmethod
    def _get_parser(cls, subcommand: str):
        parsers = {
            "status": cls._parse_status,
            "log": cls._parse_log,
            "diff": cls._parse_diff,
            "branch": cls._parse_branch,
            "remote": cls._parse_remote,
            "stash": cls._parse_stash,
            "commit": cls._parse_commit,
            "init": cls._parse_init,
            "clone": cls._parse_clone,
            "push": cls._parse_sync,
            "pull": cls._parse_sync,
            "fetch": cls._parse_sync,
            "merge": cls._parse_merge,
        }
        return parsers.get(subcommand)

    @classmethod
    def _parse_status(cls, result: subprocess.CompletedProcess, repo_path: str, cmd: List[str]) -> Dict[str, Any]:
        data: Dict[str, Any] = {"operation": "status", "repo_path": _norm(Path(repo_path).resolve())}
        branch_info = cls._get_branch_info(repo_path)
        if branch_info:
            data.update(branch_info)

        staged: List[Dict[str, str]] = []
        unstaged: List[Dict[str, str]] = []
        untracked: List[str] = []
        status_map = {
            "M": "modified", "A": "added", "D": "deleted",
            "R": "renamed", "C": "copied", "U": "updated",
            "?": "untracked", "!": "ignored",
        }
        for line in result.stdout.splitlines():
            if len(line) < 3:
                continue
            xy = line[0:2]
            path = line[3:].strip()
            staged_s = status_map.get(xy[0])
            working_s = status_map.get(xy[1])
            if staged_s:
                staged.append({"path": path, "status": staged_s})
            if working_s:
                unstaged.append({"path": path, "status": working_s})
            if xy[0] == "?":
                untracked.append(path)

        data["staged"] = staged
        data["unstaged"] = unstaged
        data["untracked"] = untracked
        data["_message"] = f"Repository status: {len(staged)} staged, {len(unstaged)} unstaged, {len(untracked)} untracked"
        return data

    @classmethod
    def _get_branch_info(cls, repo_path: str) -> Optional[Dict[str, Any]]:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_path, capture_output=True, text=True, timeout=5,
            )
            branch = result.stdout.strip() if result.returncode == 0 else "HEAD"
            ahead_behind = subprocess.run(
                ["git", "rev-list", "--count", "--left-right", f"{branch}@{{upstream}}...HEAD"],
                cwd=repo_path, capture_output=True, text=True, timeout=5,
            )
            ahead = 0
            behind = 0
            if ahead_behind.returncode == 0 and ahead_behind.stdout.strip():
                parts = ahead_behind.stdout.strip().split("\t")
                if len(parts) == 2:
                    try:
                        behind = int(parts[0])
                        ahead = int(parts[1])
                    except ValueError:
                        pass
            return {"branch": branch, "ahead": ahead, "behind": behind}
        except Exception:
            return None

    @classmethod
    def _parse_log(cls, result: subprocess.CompletedProcess, repo_path: str, cmd: List[str]) -> Dict[str, Any]:
        entries: List[Dict[str, str]] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 4)
            if len(parts) >= 5:
                entries.append({
                    "hash": parts[0],
                    "graph": parts[1] if parts[1] in ("*", "|", "/", "\\") else "",
                    "author": parts[2],
                    "date": parts[3],
                    "subject": " ".join(parts[4:]),
                })
            elif len(parts) >= 4:
                entries.append({
                    "hash": parts[0],
                    "graph": parts[1] if parts[1] in ("*", "|", "/", "\\") else "",
                    "author": parts[1],
                    "date": parts[2],
                    "subject": " ".join(parts[3:]),
                })
        total = len(entries)
        data: Dict[str, Any] = {
            "operation": "log",
            "total_commits": total,
            "displayed": total,
            "entries": entries,
        }
        data["_message"] = f"Commit history retrieved ({total} commits)"
        return data

    @classmethod
    def _parse_diff(cls, result: subprocess.CompletedProcess, repo_path: str, cmd: List[str]) -> Dict[str, Any]:
        files_map: Dict[str, Dict[str, Any]] = {}
        current_file: Optional[str] = None
        current_hunk: Optional[Dict[str, str]] = None
        current_content: List[str] = []

        for line in result.stdout.splitlines():
            if line.startswith("diff --git"):
                if current_file and current_hunk is not None:
                    current_hunk["content"] = "\n".join(current_content)
                current_file = line.split()[-1].lstrip("a/")
                files_map.setdefault(current_file, {"path": current_file, "status": "modified", "hunks": []})
                current_hunk = None
                current_content = []
            elif line.startswith("@@") and current_file:
                if current_hunk is not None:
                    current_hunk["content"] = "\n".join(current_content)
                current_hunk = {"line_range": line, "content": ""}
                files_map[current_file]["hunks"].append(current_hunk)
                current_content = []
            elif current_file:
                current_content.append(line)

        if current_file and current_hunk is not None:
            current_hunk["content"] = "\n".join(current_content)

        return {
            "operation": "diff",
            "files": list(files_map.values()),
            "_message": f"Diff retrieved ({len(files_map)} files)",
        }

    @classmethod
    def _parse_branch(cls, result: subprocess.CompletedProcess, repo_path: str, cmd: List[str]) -> Dict[str, Any]:
        branches: List[Dict[str, Any]] = []
        current = ""
        for line in result.stdout.splitlines():
            name = line.strip().lstrip("* ")
            is_current = line.strip().startswith("*")
            if is_current:
                current = name
            branches.append({"name": name, "current": is_current})
        return {
            "operation": "branch",
            "current_branch": current,
            "branches": branches,
            "_message": f"Branches ({len(branches)} total, current: {current})",
        }

    @classmethod
    def _parse_remote(cls, result: subprocess.CompletedProcess, repo_path: str, cmd: List[str]) -> Dict[str, Any]:
        remotes: List[Dict[str, str]] = []
        name = ""
        url = ""
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                if name and parts[0] != name:
                    if name and url:
                        remotes.append({"name": name, "url": url})
                    name = parts[0]
                    url = parts[1]
                else:
                    name = parts[0]
                    url = parts[1]
        if name and url:
            remotes.append({"name": name, "url": url})
        return {
            "operation": "remote",
            "remotes": remotes,
            "_message": f"Remote repositories ({len(remotes)})",
        }

    @classmethod
    def _parse_stash(cls, result: subprocess.CompletedProcess, repo_path: str, cmd: List[str]) -> Dict[str, Any]:
        stashes: List[Dict[str, str]] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(":", 1)
            if len(parts) == 2:
                stashes.append({"stash_id": parts[0].strip(), "message": parts[1].strip()})
        return {
            "operation": "stash",
            "stashes": stashes,
            "_message": f"Stash list ({len(stashes)} entries)",
        }

    @classmethod
    def _parse_commit(cls, result: subprocess.CompletedProcess, repo_path: str, cmd: List[str]) -> Dict[str, Any]:
        output = result.stdout.strip()
        data: Dict[str, Any] = {"operation": "commit"}
        m = re.search(r"\[([^\]]+)\]", output)
        if m:
            data["branch"] = m.group(1)
        m = re.search(r"([a-f0-9]{7,40})", output)
        if m:
            data["short_hash"] = m.group(1)[:7]
            data["commit_hash"] = m.group(1)
        m = re.search(r"(\d+) files? changed", output)
        if m:
            data["files_changed"] = int(m.group(1))
        m = re.search(r"(\d+) insertions?", output)
        if m:
            data["insertions"] = int(m.group(1))
        m = re.search(r"(\d+) deletions?", output)
        if m:
            data["deletions"] = int(m.group(1))
        data["_message"] = output
        return data

    @classmethod
    def _parse_init(cls, result: subprocess.CompletedProcess, repo_path: str, cmd: List[str]) -> Dict[str, Any]:
        output = result.stderr.strip() or result.stdout.strip()
        data: Dict[str, Any] = {
            "operation": "init",
            "repo_path": _norm(Path(repo_path).resolve()),
        }
        try:
            version = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
            data["git_version"] = version.stdout.strip() if version.returncode == 0 else ""
        except Exception:
            pass
        try:
            head = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                  cwd=repo_path, capture_output=True, text=True, timeout=5)
            data["default_branch"] = head.stdout.strip() if head.returncode == 0 else "master"
        except Exception:
            data["default_branch"] = "master"
        data["_message"] = output
        return data

    @classmethod
    def _parse_clone(cls, result: subprocess.CompletedProcess, repo_path: str, cmd: List[str]) -> Dict[str, Any]:
        stderr = result.stderr.strip()
        data: Dict[str, Any] = {"operation": "clone"}

        m = re.search(r"'(https?://[^']+)'", " ".join(cmd))
        if m:
            data["source_url"] = m.group(1)

        lines = stderr.splitlines()
        dest_line = ""
        for line in lines:
            if "Cloning into" in line:
                dest_line = line
                break
        if dest_line:
            m = re.search(r"into '([^']+)'", dest_line)
            if m:
                data["target_path"] = _norm(Path(m.group(1)))

        try:
            if data.get("target_path"):
                tp = Path(data["target_path"])
                if tp.exists():
                    head = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                          cwd=str(tp), capture_output=True, text=True, timeout=5)
                    data["default_branch"] = head.stdout.strip() if head.returncode == 0 else "main"
        except Exception:
            pass

        depth = None
        for i, a in enumerate(cmd):
            if a == "--depth" and i + 1 < len(cmd):
                try:
                    depth = int(cmd[i + 1])
                except ValueError:
                    pass
                break
        if depth is not None:
            data["clone_depth"] = depth

        data["_message"] = f"Cloned repository to {data.get('target_path', 'unknown')}"
        return data

    @classmethod
    def _parse_sync(cls, result: subprocess.CompletedProcess, repo_path: str, cmd: List[str]) -> Dict[str, Any]:
        data: Dict[str, Any] = {"operation": cmd[1] if len(cmd) > 1 else "sync"}
        remote = ""
        branch = ""
        for i, a in enumerate(cmd):
            if a in ("origin", "upstream") and i > 1:
                remote = a
            elif remote and not branch and i > cmd.index(remote):
                branch = a
        if remote:
            data["remote"] = remote
        if branch:
            data["branch"] = branch

        output = result.stderr.strip() or result.stdout.strip()
        m = re.search(r"(\d+) commits?", output)
        if m:
            data["commits"] = int(m.group(1))
        if "--rebase" in cmd:
            data["method"] = "rebase"
        elif "--ff-only" in cmd:
            data["method"] = "fast-forward-only"
        else:
            data["method"] = "merge"

        force = "--force" in cmd or "--force-with-lease" in cmd
        data["force_used"] = force
        data["_message"] = output
        return data

    @classmethod
    def _parse_merge(cls, result: subprocess.CompletedProcess, repo_path: str, cmd: List[str]) -> Dict[str, Any]:
        output = result.stderr.strip() or result.stdout.strip()
        data: Dict[str, Any] = {"operation": "merge"}

        source_branch = ""
        for a in cmd:
            if a not in ("git", "merge", "--no-ff", "--ff-only", "--squash", "-m") and not a.startswith("-"):
                source_branch = a
        data["source_branch"] = source_branch

        try:
            branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                    cwd=repo_path, capture_output=True, text=True, timeout=5)
            data["target_branch"] = branch.stdout.strip() if branch.returncode == 0 else ""
        except Exception:
            pass

        if "fast-forward" in output.lower():
            data["merge_type"] = "fast-forward"
        elif "recursive" in output.lower():
            data["merge_type"] = "recursive"
        elif "merge made by" in output.lower():
            data["merge_type"] = "recursive"
        else:
            data["merge_type"] = "unknown"

        m = re.search(r"(\d+) files? changed", output)
        if m:
            data["files_changed"] = int(m.group(1))
        data["conflicts"] = []
        data["_message"] = output
        return data

    @classmethod
    def _parse_conflicts(cls, stderr: str) -> List[Dict[str, str]]:
        conflicts: List[Dict[str, str]] = []
        for line in stderr.splitlines():
            m = re.search(r"(?:both (?:modified|added|deleted)|(?:added|modified|deleted) by (?:us|them))", line)
            if m:
                file_part = line.split(":")[0].strip() if ":" in line else ""
                conflicts.append({"file": file_part, "status": m.group(0)})
        return conflicts
