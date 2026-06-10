"""
Version — SemVer 2.0.0 compliant version string value object.

:project: CodeCortex
:package: Core.Utils.Version
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)"
    r"\.(?P<minor>0|[1-9]\d*)"
    r"\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z\-]+(?:\.[0-9A-Za-z\-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z\-]+(?:\.[0-9A-Za-z\-]+)*))?$"
)

class InvalidVersionError(ValueError):
    def __init__(self, version: str) -> None:
        super().__init__(f"Invalid semantic version: {version!r}")

@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None

    @classmethod
    def parse(cls, raw: str) -> Version:
        cleaned = raw.strip().lstrip("v")
        match = _SEMVER_RE.match(cleaned)
        if not match:
            raise InvalidVersionError(raw)
        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=match.group("prerelease"),
            build=match.group("build"),
        )

    @classmethod
    def default(cls) -> Version:
        return cls(major=0, minor=1, patch=0)

    def bump_major(self) -> Version:
        return Version(major=self.major + 1, minor=0, patch=0)

    def bump_minor(self) -> Version:
        return Version(major=self.major, minor=self.minor + 1, patch=0)

    def bump_patch(self) -> Version:
        return Version(major=self.major, minor=self.minor, patch=self.patch + 1)

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    @property
    def version_folder(self) -> str:
        return f"v{self.major}.{self.minor}"
