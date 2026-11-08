#!/usr/bin/env python3
"""Tests for check_manifest_parity.py.

The release gate this replaces was `[ "$total" -lt 20 ]` - a fixed floor that was
correct at twenty modules, wrong at thirty-four, and structurally unable to
notice a single missing module as long as enough others built. Every test below
is a case that floor got wrong, or a way it could come back.

Run:  python3 tools/test_check_manifest_parity.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / "check_manifest_parity.py"
MANIFEST = HERE.parent / "modules.json"


def jar(directory: Path, mod_id: str, *, version: str = "1.0.0") -> Path:
    path = directory / f"{mod_id}-{version}.jar"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("fabric.mod.json",
                         json.dumps({"schemaVersion": 1, "id": mod_id, "version": version}))
    return path


def manifest(directory: Path, entries: list[dict]) -> Path:
    path = directory / "modules.json"
    path.write_text(json.dumps({"schemaVersion": 1, "modules": entries}), encoding="utf-8")
    return path


def run_tool(dist: Path, man: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), "--dist", str(dist), "--manifest", str(man), *extra],
        capture_output=True, text=True)


class Parity(unittest.TestCase):
    def test_a_complete_build_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mods = [{"name": "core", "modId": "macroengine-core"},
                    {"name": "queue", "modId": "macroengine-queue"}]
            man = manifest(root, mods)
            dist = root / "dist"
            dist.mkdir()
            jar(dist, "macroengine-core")
            jar(dist, "macroengine-queue")

            result = run_tool(dist, man)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("all 2 modules", result.stdout)

    def test_one_missing_module_fails_even_when_the_count_is_large(self):
        """The exact failure the old floor could not see.

        Thirty-three of thirty-four modules built: the old check asked
        `33 -lt 20`, got false, and shipped. This asserts the set comparison
        catches it and that the message names the module, since "1 missing" in a
        34-jar release is not a useful thing to be told.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mods = [{"name": f"m{i}", "modId": f"macroengine-m{i}"} for i in range(34)]
            man = manifest(root, mods)
            dist = root / "dist"
            dist.mkdir()
            for entry in mods[:-1]:
                jar(dist, entry["modId"])

            result = run_tool(dist, man)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("MISSING", result.stdout)
            self.assertIn("macroengine-m33", result.stdout)
            self.assertIn("33 built", result.stdout)

    def test_an_extra_jar_fails(self):
        """A jar nobody declared is a jar nobody reviewed against the manifest."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            man = manifest(root, [{"name": "core", "modId": "macroengine-core"}])
            dist = root / "dist"
            dist.mkdir()
            jar(dist, "macroengine-core")
            jar(dist, "macroengine-surprise")

            result = run_tool(dist, man)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("EXTRA", result.stdout)
            self.assertIn("macroengine-surprise", result.stdout)

    def test_extra_jars_can_be_allowed_for_development(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            man = manifest(root, [{"name": "core", "modId": "macroengine-core"}])
            dist = root / "dist"
            dist.mkdir()
            jar(dist, "macroengine-core")
            jar(dist, "macroengine-probe")

            result = run_tool(dist, man, "--allow-extra")
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_a_duplicate_mod_id_is_not_two_modules(self):
        """Two jars with one id would satisfy a count and break the loader."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            man = manifest(root, [{"name": "core", "modId": "macroengine-core"},
                                 {"name": "queue", "modId": "macroengine-queue"}])
            dist = root / "dist"
            dist.mkdir()
            jar(dist, "macroengine-core")
            jar(dist, "macroengine-core", version="1.0.1")

            result = run_tool(dist, man)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("macroengine-queue", result.stdout)

    def test_an_unreadable_jar_counts_as_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            man = manifest(root, [{"name": "core", "modId": "macroengine-core"}])
            dist = root / "dist"
            dist.mkdir()
            (dist / "macroengine-core-1.0.0.jar").write_bytes(b"not a zip")

            result = run_tool(dist, man)
            self.assertEqual(result.returncode, 1, result.stdout)

    def test_a_missing_dist_is_an_environment_error_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            man = manifest(root, [{"name": "core", "modId": "macroengine-core"}])
            result = run_tool(root / "does-not-exist", man)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_a_manifest_without_modules_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            man = root / "modules.json"
            man.write_text(json.dumps({"schemaVersion": 1}), encoding="utf-8")
            dist = root / "dist"
            dist.mkdir()
            result = run_tool(dist, man)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("no `modules` list", result.stdout + result.stderr)

    def test_a_duplicate_mod_id_in_the_manifest_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            man = manifest(root, [{"name": "a", "modId": "same"},
                                  {"name": "b", "modId": "same"}])
            dist = root / "dist"
            dist.mkdir()
            jar(dist, "same")
            result = run_tool(dist, man)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("duplicate modId", result.stdout + result.stderr)

    def test_the_real_manifest_parses(self):
        """The repository's own modules.json is the input this tool must accept."""
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        modules = data["modules"]
        self.assertGreater(len(modules), 0)
        for entry in modules:
            self.assertTrue(entry.get("name"), entry)
            self.assertTrue(entry.get("modId"), entry)
        ids = [entry["modId"] for entry in modules]
        self.assertEqual(len(ids), len(set(ids)), "duplicate modId in modules.json")

    def test_the_release_workflow_has_no_hard_coded_module_count(self):
        """The floor is gone from the workflow, not merely shadowed by this tool.

        Matched as an executable shell test (`if [ ... -lt N ]`), not as the
        substring "-lt 20": the workflow explains in a comment why that gate was
        removed, and a test that forbids its own explanation would force the next
        person to choose between documenting the change and keeping the test green.
        """
        workflow = (HERE.parent / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        executable_floor = re.search(r"^\s*if\s+\[.*\s-lt\s+\d+\s*\]", workflow, re.MULTILINE)
        self.assertTrue(executable_floor is None,
                        "a hard-coded module floor is back: "
                        f"{(executable_floor.group(0).strip() if executable_floor else '')!r}")
        self.assertIn("check_manifest_parity.py", workflow,
                      "the parity check must be wired into the release workflow")

    def test_the_release_workflow_pins_the_source_commit(self):
        """A release built from a branch is not reproducible."""
        workflow = (HERE.parent / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn("SOURCE_SHA:", workflow)
        self.assertIn("rev-parse HEAD", workflow,
                      "the workflow must verify that the checkout landed on the pin")
        self.assertNotIn("--depth=1 \\\n                \"https://x-access-token", workflow,
                         "the floating shallow clone of the source repo is back")


if __name__ == "__main__":
    unittest.main(verbosity=2)
