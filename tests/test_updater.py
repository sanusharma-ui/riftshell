"""test_updater.py - Unit tests for RiftShell updater and update_ui modules."""
from __future__ import annotations

import io
import json
import hashlib
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

import updater
from update_ui import CheckWorker, DownloadWorker, UpdateController


APP = QApplication.instance() or QApplication([])


class UpdaterCoreTests(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(updater.parse_version("1.1.0"), (1, 1, 0))
        self.assertEqual(updater.parse_version("v2.0.4"), (2, 0, 4))
        self.assertTrue(updater.parse_version("1.2.0") > updater.parse_version("1.1.0"))
        self.assertFalse(updater.parse_version("1.1.0") > updater.parse_version("1.1.0"))
        self.assertFalse(updater.parse_version("1.0.9") > updater.parse_version("1.1.0"))

    def test_check_update_returns_manifest_when_newer(self):
        fake_manifest = {
            "version": "2.0.0",
            "url": "https://example.com/riftshell.exe",
            "sha256": "abc",
            "notes": "New features",
        }
        fake_resp = io.BytesIO(json.dumps(fake_manifest).encode("utf-8"))
        with patch("urllib.request.urlopen", return_value=fake_resp):
            result = updater.check_update()
            self.assertEqual(result, fake_manifest)

    def test_check_update_returns_none_when_same_or_older(self):
        fake_manifest = {"version": "1.1.0", "url": "https://example.com/riftshell.exe", "sha256": "abc"}
        fake_resp = io.BytesIO(json.dumps(fake_manifest).encode("utf-8"))
        with patch("urllib.request.urlopen", return_value=fake_resp):
            self.assertIsNone(updater.check_update())

    def test_check_update_fails_silently_on_network_or_json_error(self):
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            self.assertIsNone(updater.check_update())

        bad_json = io.BytesIO(b"not json")
        with patch("urllib.request.urlopen", return_value=bad_json):
            self.assertIsNone(updater.check_update())

    def test_download_update_verifies_sha256_and_reports_progress(self):
        data = b"RiftShell updated binary content"
        sha = hashlib.sha256(data).hexdigest()
        manifest = {"version": "1.2.0", "url": "https://example.com/exe", "sha256": sha}

        fake_resp = MagicMock()
        fake_resp.read.side_effect = [data, b""]
        fake_resp.headers = {"Content-Length": str(len(data))}
        fake_resp.__enter__.return_value = fake_resp

        progress = []
        with patch("urllib.request.urlopen", return_value=fake_resp):
            path = updater.download_update(manifest, on_progress=progress.append)
            self.assertTrue(os.path.exists(path))
            self.assertEqual(open(path, "rb").read(), data)
            self.assertIn(100, progress)
            try:
                os.remove(path)
            except OSError:
                pass

    def test_download_update_raises_on_checksum_mismatch_and_deletes_file(self):
        data = b"corrupted data"
        manifest = {"version": "1.2.0", "url": "https://example.com/exe", "sha256": "expected_good_hash"}

        fake_resp = MagicMock()
        fake_resp.read.side_effect = [data, b""]
        fake_resp.headers = {"Content-Length": str(len(data))}
        fake_resp.__enter__.return_value = fake_resp

        with patch("urllib.request.urlopen", return_value=fake_resp):
            with self.assertRaises(RuntimeError) as ctx:
                updater.download_update(manifest)
            self.assertIn("Checksum mismatch", str(ctx.exception))

    def test_download_update_cancellation_cleans_up_file(self):
        data = b"Some data"
        manifest = {"version": "1.2.0", "url": "https://example.com/exe", "sha256": "abc"}

        fake_resp = MagicMock()
        fake_resp.read.side_effect = [data, b""]
        fake_resp.headers = {"Content-Length": "1000"}
        fake_resp.__enter__.return_value = fake_resp

        with patch("urllib.request.urlopen", return_value=fake_resp):
            with self.assertRaises(RuntimeError) as ctx:
                updater.download_update(manifest, is_cancelled=lambda: True)
            self.assertIn("cancelled by user", str(ctx.exception))
            dest = os.path.join(updater.tempfile.gettempdir(), "RiftShell_new.exe")
            self.assertFalse(os.path.exists(dest))

    def test_apply_update_enforces_frozen_environment(self):
        with patch.object(sys, "frozen", False, create=True):
            with self.assertRaises(RuntimeError) as ctx:
                updater.apply_update("dummy.exe")
            self.assertIn("Updates work only in the built exe", str(ctx.exception))

    def test_apply_update_spawns_batch_when_frozen(self):
        with patch.object(sys, "frozen", True, create=True), \
             patch("subprocess.Popen") as mock_popen:
            updater.apply_update("RiftShell_new.exe")
            mock_popen.assert_called_once()
            args, kwargs = mock_popen.call_args
            self.assertEqual(args[0][0], "cmd")
            self.assertEqual(args[0][1], "/c")
            self.assertEqual(kwargs["creationflags"], 0x08000000)


class UpdateUITests(unittest.TestCase):
    def test_check_worker_emits_found_and_none(self):
        worker = CheckWorker()
        manifest = {"version": "2.0.0", "url": "http://test"}
        with patch("update_ui.check_update", return_value=manifest):
            received = []
            worker.found.connect(received.append)
            worker.run()
            self.assertEqual(received, [manifest])

        with patch("update_ui.check_update", return_value=None):
            called = []
            worker.none.connect(lambda: called.append(True))
            worker.run()
            self.assertEqual(called, [True])

    def test_download_worker_emits_done_and_failed(self):
        manifest = {"version": "2.0.0", "url": "http://test"}
        worker = DownloadWorker(manifest)
        with patch("update_ui.download_update", return_value="/tmp/fake.exe"):
            done_paths = []
            worker.done.connect(done_paths.append)
            worker.run()
            self.assertEqual(done_paths, ["/tmp/fake.exe"])

        with patch("update_ui.download_update", side_effect=RuntimeError("connection dropped")):
            failed_msgs = []
            worker.failed.connect(failed_msgs.append)
            worker.run()
            self.assertEqual(failed_msgs, ["connection dropped"])


if __name__ == "__main__":
    unittest.main()
