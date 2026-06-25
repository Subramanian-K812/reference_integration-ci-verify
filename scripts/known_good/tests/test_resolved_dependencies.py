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
"""Unit tests for ResolvedDependencies (DR-008 Option 4 dependency injection).

Self-contained: builds the resolved set from a temporary known_good.json and
overwrites a temporary module MODULE.bazel — no cloned repos or Bazel required.
"""

import json
import sys
from pathlib import Path

import pytest

# Make scripts/known_good importable when run via plain pytest.
_KG_DIR = Path(__file__).resolve().parents[1]
if str(_KG_DIR) not in sys.path:
    sys.path.insert(0, str(_KG_DIR))

from resolved_dependencies import (  # noqa: E402
    INJECTION_BEGIN,
    INJECTION_END,
    ResolvedDependencies,
)

KNOWN_GOOD = {
    "modules": {
        "target_sw": {
            "score_baselibs": {
                "repo": "https://github.com/eclipse-score/baselibs.git",
                "hash": "cab36dd7de92aaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "bazel_patches": ["patches/baselibs/001-fix.patch"],
            },
            "score_logging": {
                "repo": "https://github.com/eclipse-score/logging.git",
                "hash": "0e9187f79a99bbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            },
            "score_persistency": {
                "repo": "https://github.com/eclipse-score/persistency.git",
                "hash": "4d1fa1ae3c55cccccccccccccccccccccccccccc",
            },
        },
        "tooling": {
            "score_tooling": {
                "repo": "https://github.com/eclipse-score/tooling.git",
                "version": "1.2.0",
            },
        },
    },
    "timestamp": "2026-01-01T00:00:00+00:00Z",
}

MODULE_BAZEL = """\
module(name = "score_persistency", version = "0.0.0")

bazel_dep(name = "rules_cc", version = "0.2.17")
bazel_dep(name = "score_baselibs", version = "0.2.7")
bazel_dep(name = "score_logging", version = "0.2.0")
bazel_dep(name = "score_tooling", version = "1.0.0")
bazel_dep(name = "score_unpinned", version = "9.9.9")
"""


@pytest.fixture
def known_good_file(tmp_path: Path) -> Path:
    p = tmp_path / "known_good.json"
    p.write_text(json.dumps(KNOWN_GOOD))
    return p


@pytest.fixture
def module_bazel(tmp_path: Path) -> Path:
    p = tmp_path / "MODULE.bazel"
    p.write_text(MODULE_BAZEL)
    return p


@pytest.fixture
def resolved(known_good_file: Path) -> ResolvedDependencies:
    return ResolvedDependencies.from_known_good(known_good_file)


class TestFromKnownGood:
    def test_names_span_all_groups(self, resolved: ResolvedDependencies):
        assert {"score_baselibs", "score_logging", "score_persistency", "score_tooling"} <= resolved.names

    def test_get_returns_resolved_commit(self, resolved: ResolvedDependencies):
        assert resolved.get("score_baselibs").hash.startswith("cab36dd7de92")

    def test_version_module_kept(self, resolved: ResolvedDependencies):
        assert resolved.get("score_tooling").version == "1.2.0"


class TestScan:
    def test_returns_declared_deps(self, resolved: ResolvedDependencies, module_bazel: Path):
        declared = resolved.scan(module_bazel)
        assert "score_baselibs" in declared
        assert "score_unpinned" in declared
        assert "rules_cc" in declared


class TestOverwrite:
    def test_pins_declared_resolved_siblings(self, resolved: ResolvedDependencies, module_bazel: Path):
        patched = resolved.overwrite(module_bazel, module_under_test="score_persistency", write=False)
        block = patched.split(INJECTION_BEGIN)[1].split(INJECTION_END)[0]
        assert 'git_override(\n    module_name = "score_baselibs"' in block
        assert 'commit = "cab36dd7de92aaaaaaaaaaaaaaaaaaaaaaaaaaaa"' in block
        # version module -> single_version_override
        assert 'single_version_override(\n    module_name = "score_tooling"' in block
        assert 'version = "1.2.0"' in block

    def test_carries_patches(self, resolved: ResolvedDependencies, module_bazel: Path):
        patched = resolved.overwrite(module_bazel, module_under_test="score_persistency", write=False)
        assert "patches/baselibs/001-fix.patch" in patched
        assert "patch_strip = 1" in patched

    def test_skips_root_module(self, resolved: ResolvedDependencies, module_bazel: Path):
        patched = resolved.overwrite(module_bazel, module_under_test="score_persistency", write=False)
        block = patched.split(INJECTION_BEGIN)[1].split(INJECTION_END)[0]
        assert 'module_name = "score_persistency"' not in block

    def test_skips_unpinned_third_party(self, resolved: ResolvedDependencies, module_bazel: Path):
        patched = resolved.overwrite(module_bazel, module_under_test="score_persistency", write=False)
        block = patched.split(INJECTION_BEGIN)[1].split(INJECTION_END)[0]
        assert "score_unpinned" not in block
        assert "rules_cc" not in block

    def test_idempotent(self, resolved: ResolvedDependencies, module_bazel: Path):
        first = resolved.overwrite(module_bazel, module_under_test="score_persistency", write=True)
        second = resolved.overwrite(module_bazel, module_under_test="score_persistency", write=True)
        assert first == second
        assert second.count(INJECTION_BEGIN) == 1

    def test_skips_dep_with_existing_override(self, resolved: ResolvedDependencies, tmp_path: Path):
        mod = tmp_path / "MODULE.bazel"
        mod.write_text(
            MODULE_BAZEL
            + '\ngit_override(\n    module_name = "score_logging",\n    commit = "deadbeef",\n'
            '    remote = "https://example.com/x.git",\n)\n'
        )
        patched = resolved.overwrite(mod, module_under_test="score_persistency", write=False)
        block = patched.split(INJECTION_BEGIN)[1].split(INJECTION_END)[0]
        assert 'module_name = "score_logging"' not in block  # respected pre-existing override


class TestMetadataBazelConfig:
    def test_bazel_config_roundtrip(self):
        from models.module import Metadata

        m = Metadata.from_dict({"bazel_config": ["bl-x86_64-linux"]})
        assert m.bazel_config == ["bl-x86_64-linux"]
        assert m.to_dict()["bazel_config"] == ["bl-x86_64-linux"]

    def test_bazel_config_default_empty(self):
        from models.module import Metadata

        m = Metadata.from_dict({})
        assert m.bazel_config == []

    def test_bazel_config_multi(self):
        from models.module import Metadata

        m = Metadata.from_dict({"bazel_config": ["per-x86_64-linux", "ferrocene-coverage"]})
        assert m.bazel_config == ["per-x86_64-linux", "ferrocene-coverage"]


class TestFromResolvedArtifact:
    def test_requires_lockfile(self, tmp_path: Path):
        (tmp_path / "score_modules_target_sw.MODULE.bazel").write_text("bazel_dep(name='x')\n")
        with pytest.raises(FileNotFoundError):
            ResolvedDependencies.from_resolved_artifact(tmp_path)

    def test_roundtrip_known_good_to_artifact(self, tmp_path: Path, resolved: ResolvedDependencies):
        # Build an artifact dir mirroring stage1-resolved-deps, then parse it back.
        from update_module_from_known_good import generate_git_override_blocks

        art = tmp_path / "art"
        art.mkdir()
        (art / "MODULE.bazel.lock").write_text("{}")
        blocks = generate_git_override_blocks(list(resolved._resolved.values()), {})
        (art / "score_modules_target_sw.MODULE.bazel").write_text("\n".join(blocks))

        parsed = ResolvedDependencies.from_resolved_artifact(art)
        assert parsed.get("score_baselibs").hash == resolved.get("score_baselibs").hash
        assert parsed.get("score_tooling").version == "1.2.0"
