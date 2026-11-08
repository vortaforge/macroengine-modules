#!/usr/bin/env python3
"""Assert that build/dist contains exactly the modules modules.json declares.

`check_jars.py` asks "is each of these jars a good jar?". That is a different
question from "are all the jars here?", and the difference is what shipped a
release that could pass while missing modules:

    total=20; if [ "$total" -lt 20 ] -> pass

A hard-coded floor is a guess at the module count that has to be right forever.
It was right when there were 20 modules, silently wrong at 34, and it can never
notice a module that failed to build as long as enough other modules did - the
release ships, `check_jars.py` passes, and the missing feature is discovered by
someone whose world silently does nothing.

So the expected set is read from modules.json, and the built set from the jars
themselves, and the two are compared as sets. Not counts: a release with 33 of
34 modules and one duplicate has the right count and the wrong contents.

Run:  python3 tools/check_manifest_parity.py [--dist build/dist] [--manifest modules.json]
Exit: 0 exact match; 1 mismatch; 2 environment error.
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

DEFAULT_DIST = Path("build/dist")
DEFAULT_MANIFEST = Path("modules.json")


def expected_modules(manifest: Path) -> dict[str, str]:
    """module name -> fabric mod id, from modules.json.

    Keyed on `modId` because that is what a jar states about itself in
    fabric.mod.json; `name` is the Gradle sub-project and the pack folder, which
    is where the two could drift apart without anyone noticing.
    """
    data = json.loads(manifest.read_text(encoding="utf-8"))
    modules = data.get("modules")
    if not isinstance(modules, list) or not modules:
        raise SystemExit(f"[parity] ERROR: {manifest} has no `modules` list")

    expected: dict[str, str] = {}
    for entry in modules:
        name = entry.get("name")
        mod_id = entry.get("modId")
        if not name or not mod_id:
            raise SystemExit(f"[parity] ERROR: manifest entry without name/modId: {entry!r}")
        if mod_id in expected.values():
            raise SystemExit(f"[parity] ERROR: duplicate modId `{mod_id}` in {manifest}")
        expected[name] = mod_id
    return expected


def built_modules(dist: Path) -> dict[str, str]:
    """fabric mod id -> jar filename, for every jar in dist."""
    built: dict[str, str] = {}
    for jar in sorted(dist.glob("*.jar")):
        try:
            with zipfile.ZipFile(jar) as archive:
                meta = json.loads(archive.read("fabric.mod.json"))
        except (KeyError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
            # Not this tool's job to explain why a jar is unreadable; check_jars
            # does that with a better message. Here it simply cannot be counted
            # as a module, so it is reported as one that did not appear.
            print(f"  - {jar.name}: unreadable as a mod jar ({exc})")
            continue
        mod_id = meta.get("id")
        if not mod_id:
            print(f"  - {jar.name}: fabric.mod.json declares no id")
            continue
        if mod_id in built:
            print(f"  - {jar.name}: duplicate mod id `{mod_id}` (also {built[mod_id]})")
            continue
        built[mod_id] = jar.name
    return built


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--allow-extra", action="store_true",
                        help="permit jars whose mod id is not in the manifest "
                             "(e.g. a probe jar during development)")
    args = parser.parse_args(argv)

    if not args.dist.is_dir():
        sys.stderr.write(f"[parity] ERROR: {args.dist} does not exist; run `gradlew dist` first\n")
        return 2

    expected = expected_modules(args.manifest)
    built = built_modules(args.dist)
    expected_ids = set(expected.values())

    missing = sorted(expected_ids - set(built))
    extra = sorted(set(built) - expected_ids)

    name_of = {mod_id: name for name, mod_id in expected.items()}
    for mod_id in missing:
        print(f"  - MISSING  {name_of.get(mod_id, mod_id)} ({mod_id}): declared in "
              f"{args.manifest.name}, absent from {args.dist}")
    if not args.allow_extra:
        for mod_id in extra:
            print(f"  - EXTRA    {mod_id} ({built[mod_id]}): built but not declared in "
                  f"{args.manifest.name}")

    if missing or (extra and not args.allow_extra):
        print(f"\n[parity] FAILED: {len(expected_ids)} declared, {len(built)} built, "
              f"{len(missing)} missing, {len(extra)} extra")
        return 1

    print(f"[parity] OK: all {len(expected_ids)} modules declared in {args.manifest.name} "
          f"are present in {args.dist}, with no duplicates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
