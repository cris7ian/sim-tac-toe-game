#!/usr/bin/env python3
"""Publish the clean, committed site through the existing newsite installation."""
import io
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PATHS = ["index.html", "favicon.ico", "robots.txt", "sitemap.xml", "Build", "TemplateData"]


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def main():
    if git("status", "--porcelain").strip():
        raise SystemExit("Commit or move local changes before publishing; only HEAD is deployed.")
    revision = git("rev-parse", "HEAD").decode().strip()
    parent = Path.home() / ".local/share/newsite/releases/tictactoe"
    parent.mkdir(parents=True, exist_ok=True)
    release = parent / revision
    archive = git("archive", "--format=zip", "HEAD", *PUBLIC_PATHS)
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        for entry in bundle.infolist():
            path = Path(entry.filename)
            if path.is_absolute() or ".." in path.parts or ((entry.external_attr >> 16) & 0o170000) == 0o120000:
                raise SystemExit("Unsafe publication archive entry.")
        if release.exists():
            expected = {entry.filename for entry in bundle.infolist() if not entry.is_dir()}
            actual = {str(path.relative_to(release)) for path in release.rglob("*") if path.is_file()}
            if expected != actual or any(path.is_symlink() for path in release.rglob("*")):
                raise SystemExit("Existing release differs from HEAD; refusing to reuse it.")
            if any((release / name).read_bytes() != bundle.read(name) for name in expected):
                raise SystemExit("Existing release differs from HEAD; refusing to reuse it.")
        else:
            # Never serve .git, scripts, tests, or untracked local files.
            with tempfile.TemporaryDirectory(prefix=".staging-", dir=parent) as directory:
                staging = Path(directory) / "public"
                staging.mkdir()
                bundle.extractall(staging)
                staging.rename(release)
    manifest_path = Path.home() / "sites/tictactoe/site.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        "version": 1, "name": "tictactoe", "mode": "static"
    }
    if manifest.get("name") != "tictactoe" or manifest.get("mode") != "static":
        raise SystemExit("Unexpected live manifest; refusing to replace another site or mode.")
    manifest["root"] = str(release)
    with tempfile.TemporaryDirectory(prefix="tictactoe-publish-") as directory:
        source = Path(directory) / "site.json"
        source.write_text(json.dumps(manifest, indent=2) + "\n")
        source.chmod(0o600)
        result = subprocess.run(["newsite", "--manifest", str(source)], check=False)
    print(f"Release: {revision}", flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
