"""Exercise publication exports and retries with real temporary Git repositories."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publisher", ROOT / "scripts/publish.py")
assert spec is not None and spec.loader is not None
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="tictactoe-publish-test-")
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.home = self.base / "home"
        self.home.mkdir()
        self.calls = []
        self.returncode = 0
        for name in ["index.html", "favicon.ico", "robots.txt", "sitemap.xml", "Build/game.wasm", "TemplateData/style.css", "scripts/private.py"]:
            file = self.repo / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("test fixture: " + name)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.git("add", ".")
        self.git("-c", "user.name=Test Operator", "-c", "user.email=test@example.invalid", "commit", "-qm", "Test fixture")
        self.revision = self.git("rev-parse", "HEAD").decode().strip()
        self.release = self.home / ".local/share/newsite/releases/tictactoe" / self.revision
        original_run = subprocess.run

        def run(argv, *args, **kwargs):
            if argv[0] != "newsite":
                return original_run(argv, *args, **kwargs)
            manifest = Path(argv[2])
            self.assertEqual(manifest.stat().st_mode & 0o777, 0o600)
            self.calls.append(json.loads(manifest.read_text()))
            return subprocess.CompletedProcess(argv, self.returncode)

        self.root_patch = patch.object(publisher, "ROOT", self.repo)
        self.home_patch = patch.dict(os.environ, {"HOME": str(self.home)})
        self.run_patch = patch.object(publisher.subprocess, "run", side_effect=run)
        for context in [self.root_patch, self.home_patch, self.run_patch]:
            context.start()
            self.addCleanup(context.stop)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args])

    def test_exports_only_allowed_committed_assets_and_preserves_site_settings(self):
        manifest = self.home / "sites/tictactoe/site.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"version": 1, "name": "tictactoe", "mode": "static", "root": "/old", "access": {"emails": ["owner@example.com"]}}))
        publisher.main()
        self.assertTrue((self.release / "index.html").is_file())
        self.assertTrue((self.release / "Build/game.wasm").is_file())
        self.assertFalse((self.release / ".git").exists())
        self.assertFalse((self.release / "scripts").exists())
        self.assertEqual(self.calls[0]["root"], str(self.release))
        self.assertEqual(self.calls[0]["access"], {"emails": ["owner@example.com"]})

    def test_identical_release_can_be_retried(self):
        publisher.main()
        publisher.main()
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[0], self.calls[1])

    def test_modified_release_is_refused(self):
        publisher.main()
        (self.release / "index.html").write_text("changed release fixture")
        with self.assertRaisesRegex(SystemExit, "differs from HEAD"):
            publisher.main()
        self.assertEqual(len(self.calls), 1)

    def test_newsite_failure_is_propagated_and_release_remains_retryable(self):
        self.returncode = 2
        with self.assertRaises(SystemExit) as raised:
            publisher.main()
        self.assertEqual(raised.exception.code, 2)
        self.returncode = 0
        publisher.main()
        self.assertEqual(len(self.calls), 2)

    def test_dirty_checkout_cannot_be_published(self):
        (self.repo / "index.html").write_text("uncommitted fixture")
        with self.assertRaisesRegex(SystemExit, "Commit or move"):
            publisher.main()
        self.assertFalse(self.release.exists())
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
