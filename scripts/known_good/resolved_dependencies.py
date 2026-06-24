#!/usr/bin/env python3
# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************
"""Resolved dependency versions from the reference_integration root.

DR-008 Option 4 requires that the dependency versions ``reference_integration``
resolves are pushed *into* each module so the module's own unit tests + coverage
run against the resolved set (not against the versions the module declares in its
released ``MODULE.bazel``).

This module provides :class:`ResolvedDependencies`, which:

* holds the resolved version/commit per dependency (sourced from ref_int's root —
  either ``known_good.json`` for local runs, or the Stage-1 ``stage1-resolved-deps``
  artifact for CI runs so the resolution flows Stage 1 -> Stage 2), and
* exposes an interface to **scan** an individual module's ``MODULE.bazel`` and
  **overwrite** the declared dependency versions to match the resolved set, by
  appending the matching ``git_override`` / ``single_version_override`` directives.

The injection is append-only and operates on the CI checkout of the module — it is
never committed back to the module's released sources (DR-008 "temporary mechanism").
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Import ``models`` + ``generate_override_directive`` whether this file is loaded as
# ``known_good.resolved_dependencies`` (scripts/ on path, e.g. from quality_runners.py)
# or as ``resolved_dependencies`` (scripts/known_good/ on path). Preferring the
# package-qualified form keeps a single ``Module`` class identity in the package context.
_HERE = Path(__file__).resolve().parent
try:
    from known_good.models.known_good import load_known_good
    from known_good.models.module import Module
    from known_good.update_module_from_known_good import generate_override_directive
except ImportError:
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))
    from models.known_good import load_known_good  # noqa: E402
    from models.module import Module  # noqa: E402
    from update_module_from_known_good import generate_override_directive  # noqa: E402

# Marker delimiting the block we append, so injection is idempotent / detectable.
INJECTION_BEGIN = "# --- BEGIN ref_int resolved-deps injection (DR-008 Option 4) ---"
INJECTION_END = "# --- END ref_int resolved-deps injection (DR-008 Option 4) ---"

# Capture the module name from any ``bazel_dep(name = "...")`` call (name is the first arg).
_BAZEL_DEP_RE = re.compile(r'bazel_dep\(\s*name\s*=\s*"([^"]+)"')
# Capture an existing override target so we don't inject a duplicate for the same module.
_OVERRIDE_RE = re.compile(r'(?:git_override|single_version_override|local_path_override|archive_override)\(\s*module_name\s*=\s*"([^"]+)"')
# Parsers for reconstructing the resolved set from generated score_modules_*.MODULE.bazel.
_GIT_OVERRIDE_BLOCK_RE = re.compile(r"git_override\((?P<body>.*?)\)", re.S)
_SINGLE_VERSION_BLOCK_RE = re.compile(r"single_version_override\((?P<body>.*?)\)", re.S)
_FIELD_RE = lambda field: re.compile(rf'{field}\s*=\s*"([^"]+)"')  # noqa: E731


class ResolvedDependencies:
    """Resolved dependency versions from the reference_integration root.

    Holds a ``name -> Module`` map of the dependencies ref_int pins, and provides an
    interface to scan + overwrite a module's ``MODULE.bazel`` to those versions.
    """

    def __init__(self, resolved: Dict[str, Module]):
        self._resolved = resolved

    # -- construction: "resolved deps versions from ref_int root" --------------------

    @classmethod
    def from_known_good(cls, known_good_path: Path) -> "ResolvedDependencies":
        """Build from ``known_good.json`` (local / dev source of the resolved pins)."""
        kg = load_known_good(Path(known_good_path).resolve())
        resolved: Dict[str, Module] = {}
        for group in kg.modules.values():
            for module in group.values():
                resolved[module.name] = module
        return cls(resolved)

    @classmethod
    def from_resolved_artifact(cls, artifact_dir: Path) -> "ResolvedDependencies":
        """Build from the Stage-1 ``stage1-resolved-deps`` artifact.

        Parses the generated ``score_modules_*.MODULE.bazel`` override files (the
        authoritative record of the commits/versions ref_int resolved). Requires the
        ``MODULE.bazel.lock`` to also be present — it is the evidence of the complete
        transitive resolution and confirms the artifact is the genuine Stage-1 output
        being consumed by Stage 2 (DR-008 V3 / reviewer point R2).
        """
        artifact_dir = Path(artifact_dir)
        lock = artifact_dir / "MODULE.bazel.lock"
        if not lock.is_file():
            raise FileNotFoundError(
                f"MODULE.bazel.lock not found in resolved-deps artifact {artifact_dir}; "
                "Stage 2 must consume the Stage-1 resolved dependency set."
            )

        module_files = sorted(artifact_dir.glob("score_modules_*.MODULE.bazel"))
        if not module_files:
            raise FileNotFoundError(
                f"No score_modules_*.MODULE.bazel files in resolved-deps artifact {artifact_dir}."
            )

        resolved: Dict[str, Module] = {}
        for mf in module_files:
            for module in cls._parse_override_file(mf.read_text()):
                resolved[module.name] = module
        return cls(resolved)

    @staticmethod
    def _parse_override_file(text: str) -> List[Module]:
        """Reconstruct Module objects from generated git/single_version override blocks."""
        modules: List[Module] = []

        for match in _GIT_OVERRIDE_BLOCK_RE.finditer(text):
            body = match.group("body")
            name = _field(body, "module_name")
            commit = _field(body, "commit")
            remote = _field(body, "remote")
            if name and commit and remote:
                modules.append(Module(name=name, hash=commit, repo=remote))

        for match in _SINGLE_VERSION_BLOCK_RE.finditer(text):
            body = match.group("body")
            name = _field(body, "module_name")
            version = _field(body, "version")
            if name and version:
                modules.append(Module(name=name, hash="", repo="", version=version))

        return modules

    # -- interface: scan + overwrite a module's MODULE.bazel -------------------------

    @property
    def names(self) -> set[str]:
        return set(self._resolved)

    def get(self, name: str) -> Optional[Module]:
        return self._resolved.get(name)

    def scan(self, module_bazel: Path) -> List[str]:
        """Return the names of dependencies a module declares via ``bazel_dep``."""
        text = Path(module_bazel).read_text()
        # Ignore anything inside a previous injection block so re-scans are stable.
        text = self._strip_injection(text)
        return _BAZEL_DEP_RE.findall(text)

    def overwrite(self, module_bazel: Path, *, module_under_test: Optional[str] = None, write: bool = True) -> str:
        """Overwrite a module's declared dependency versions with the resolved set.

        Appends a ``git_override`` / ``single_version_override`` directive for every
        dependency the module declares that we have a resolved version for, so the
        module (and all its transitive deps) build against ref_int's resolved versions.

        * Skips the module under test itself (the root is never overridden).
        * Skips dependencies that already carry an override in the file.
        * Re-running is idempotent: a prior injection block is replaced.
        """
        module_bazel = Path(module_bazel)
        original = self._strip_injection(module_bazel.read_text())

        declared = set(_BAZEL_DEP_RE.findall(original))
        already_overridden = set(_OVERRIDE_RE.findall(original))

        directives: List[str] = []
        for name in declared:
            if name == module_under_test:
                continue
            if name in already_overridden:
                continue
            module = self._resolved.get(name)
            if module is None:
                continue  # third-party dep ref_int doesn't pin; resolves normally
            directive = generate_override_directive(module)
            if directive is None:
                continue
            directives.append(directive)

        if not directives:
            patched = original
        else:
            body = "\n".join(directives)
            patched = f"{original.rstrip()}\n\n{INJECTION_BEGIN}\n{body}\n{INJECTION_END}\n"

        if write:
            module_bazel.write_text(patched)
        return patched

    @staticmethod
    def _strip_injection(text: str) -> str:
        """Remove a previously appended injection block, if present."""
        pattern = re.compile(
            re.escape(INJECTION_BEGIN) + r".*?" + re.escape(INJECTION_END) + r"\n?",
            re.S,
        )
        return pattern.sub("", text).rstrip() + "\n" if pattern.search(text) else text


def _field(body: str, field: str) -> str:
    match = _FIELD_RE(field).search(body)
    return match.group(1) if match else ""


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan/overwrite a module's MODULE.bazel with ref_int's resolved dependency versions (DR-008 Option 4)."
    )
    parser.add_argument("module_bazel", type=Path, help="Path to the module's MODULE.bazel to overwrite")
    parser.add_argument(
        "--known-good-path",
        type=Path,
        default=_HERE.parents[1] / "known_good.json",
        help="Resolved set source: known_good.json (default).",
    )
    parser.add_argument(
        "--resolved-deps",
        type=Path,
        default=None,
        help="Resolved set source: Stage-1 stage1-resolved-deps artifact dir (overrides --known-good-path).",
    )
    parser.add_argument(
        "--module-under-test",
        default=None,
        help="Name of the module under test (never overridden as it is the root).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print patched content instead of writing.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.resolved_deps:
        resolved = ResolvedDependencies.from_resolved_artifact(args.resolved_deps)
    else:
        resolved = ResolvedDependencies.from_known_good(args.known_good_path)

    patched = resolved.overwrite(
        args.module_bazel,
        module_under_test=args.module_under_test,
        write=not args.dry_run,
    )
    if args.dry_run:
        print(patched)
    else:
        print(f"Injected resolved-deps overrides into {args.module_bazel}")


if __name__ == "__main__":
    main()
