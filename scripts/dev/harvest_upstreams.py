from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class UpstreamSpec:
    name: str
    mirror_dest: Path
    package_dest: Path
    package_src_from_repo: Path
    repo_dir: Path
    repo_url: str


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_files(root: Path, exclude_dirs: set[str]) -> Iterable[Path]:
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for name in files:
            yield Path(base) / name


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _copy_tree(src: Path, dst: Path, exclude_dirs: set[str]) -> None:
    _ensure_dir(dst)
    for path in _iter_files(src, exclude_dirs=exclude_dirs):
        rel = path.relative_to(src)
        target = dst / rel
        _ensure_dir(target.parent)
        shutil.copy2(path, target)


def _delete_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _git_clone(repo_url: str, target_dir: Path) -> None:
    _ensure_dir(target_dir.parent)
    subprocess.run(["git", "clone", repo_url, str(target_dir)], check=True)


def _build_specs(codecortex_root: Path, pythons_dir: Path) -> list[UpstreamSpec]:
    vendor_dir = codecortex_root / "vendor" / "upstreams"
    return [
        UpstreamSpec(
            name="codegraph",
            mirror_dest=vendor_dir / "codegraph",
            package_dest=codecortex_root / "src" / "domain" / "codegraph" / "upstream" / "codegraphcontext",
            package_src_from_repo=pythons_dir / "codegraph" / "src" / "codegraphcontext",
            repo_dir=pythons_dir / "codegraph",
            repo_url="https://github.com/steevenz/codegraph.git",
        ),
        UpstreamSpec(
            name="codeindex",
            mirror_dest=vendor_dir / "codeindex",
            package_dest=codecortex_root / "src" / "domain" / "codeindex" / "upstream" / "code_index_mcp",
            package_src_from_repo=pythons_dir / "codeindex" / "src" / "code_index_mcp",
            repo_dir=pythons_dir / "codeindex",
            repo_url="https://github.com/steevenz/codeindex.git",
        ),
        UpstreamSpec(
            name="graphify",
            mirror_dest=vendor_dir / "graphify",
            package_dest=codecortex_root / "src" / "domain" / "graphify" / "upstream" / "graphify",
            package_src_from_repo=pythons_dir / "graphify" / "graphify",
            repo_dir=pythons_dir / "graphify",
            repo_url="https://github.com/steevenz/graphify.git",
        ),
    ]


def _mirror_upstream(spec: UpstreamSpec, *, exclude_dirs: set[str]) -> dict:
    _delete_dir(spec.mirror_dest)
    _copy_tree(spec.repo_dir, spec.mirror_dest, exclude_dirs=exclude_dirs)
    return {"name": spec.name, "mirror_dest": str(spec.mirror_dest)}


def _verify_mirror(spec: UpstreamSpec, *, exclude_dirs: set[str]) -> dict:
    src_files = sorted([p.relative_to(spec.repo_dir).as_posix() for p in _iter_files(spec.repo_dir, exclude_dirs)])
    dst_files = sorted([p.relative_to(spec.mirror_dest).as_posix() for p in _iter_files(spec.mirror_dest, exclude_dirs)])
    missing = sorted(list(set(src_files) - set(dst_files)))
    extra = sorted(list(set(dst_files) - set(src_files)))
    ok = (not missing) and (not extra)
    return {
        "name": spec.name,
        "ok": ok,
        "source_files": len(src_files),
        "mirror_files": len(dst_files),
        "missing": missing[:50],
        "extra": extra[:50],
    }


def _verify_tree(src_root: Path, dst_root: Path, *, exclude_dirs: set[str], name: str, kind: str) -> dict:
    src_files = sorted([p.relative_to(src_root).as_posix() for p in _iter_files(src_root, exclude_dirs)])
    dst_files = sorted([p.relative_to(dst_root).as_posix() for p in _iter_files(dst_root, exclude_dirs)])
    missing = sorted(list(set(src_files) - set(dst_files)))
    extra = sorted(list(set(dst_files) - set(src_files)))
    ok = (not missing) and (not extra)
    return {
        "name": name,
        "kind": kind,
        "ok": ok,
        "source_files": len(src_files),
        "dest_files": len(dst_files),
        "missing": missing[:50],
        "extra": extra[:50],
    }


def _run(args: Sequence[str], cwd: Path) -> int:
    parser = argparse.ArgumentParser(
        prog="harvest_upstreams",
        description=(
            "Harvest upstream packages from pythons/ sibling repos into codecortex src/domain/*/upstream/. "
            "Requires codegraph, codeindex, and graphify repos to exist in the pythons/ directory."
        ),
    )
    parser.add_argument("--clone-missing", action="store_true", help="Clone repos that are missing")
    parser.add_argument("--mode", choices=["mirror", "package", "both"], default="both")
    parsed = parser.parse_args(list(args))

    codecortex_root = cwd.resolve()
    pythons_dir = codecortex_root.parent

    exclude_dirs = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules"}
    specs = _build_specs(codecortex_root, pythons_dir)

    results: list[dict] = []
    for spec in specs:
        if not spec.repo_dir.exists():
            if parsed.clone_missing:
                _git_clone(spec.repo_url, spec.repo_dir)
            else:
                raise FileNotFoundError(f"Upstream repo missing: {spec.repo_dir}")

        if parsed.mode in {"mirror", "both"}:
            results.append(_mirror_upstream(spec, exclude_dirs=exclude_dirs))

        if parsed.mode in {"package", "both"}:
            if not spec.package_src_from_repo.exists():
                raise FileNotFoundError(f"Package source not found: {spec.package_src_from_repo}")
            _delete_dir(spec.package_dest)
            _copy_tree(spec.package_src_from_repo, spec.package_dest, exclude_dirs=exclude_dirs)
            results.append({"name": spec.name, "package_dest": str(spec.package_dest), "source": "pythons"})

    verifications: list[dict] = []
    for spec in specs:
        if parsed.mode in {"mirror", "both"}:
            verifications.append(_verify_mirror(spec, exclude_dirs=exclude_dirs))
        if parsed.mode in {"package", "both"}:
            verifications.append(
                _verify_tree(
                    spec.package_src_from_repo,
                    spec.package_dest,
                    exclude_dirs=exclude_dirs,
                    name=spec.name,
                    kind="package",
                )
            )

    ok = all(v.get("ok") for v in verifications if "ok" in v)
    print(
        {
            "ok": ok,
            "codecortex_root": str(codecortex_root),
            "pythons_dir": str(pythons_dir),
            "source": "pythons",
            "actions": results,
            "verifications": verifications,
        }
    )
    return 0 if ok else 2


def main() -> None:
    raise SystemExit(_run(os.sys.argv[1:], cwd=Path.cwd()))


if __name__ == "__main__":
    main()
