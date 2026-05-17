"""Validation tests for the initial Home Assistant scaffold."""

from __future__ import annotations

import importlib
import json
import sys
import unittest
from datetime import timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class TestHacsScaffold(unittest.TestCase):
    """Verify the T-001 scaffold files and constants."""

    def test_hacs_json(self) -> None:
        """The repository advertises HACS metadata from the root."""
        hacs_path = REPO_ROOT / "hacs.json"
        self.assertTrue(hacs_path.exists())

        data = json.loads(hacs_path.read_text(encoding="utf-8"))
        self.assertEqual(data, {"name": "Endgame Grocery", "render_readme": True})

    def test_manifest_json(self) -> None:
        """The integration manifest contains the planned HA metadata."""
        manifest_path = (
            REPO_ROOT
            / "custom_components"
            / "endgame_grocery"
            / "manifest.json"
        )
        self.assertTrue(manifest_path.exists())

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["domain"], "endgame_grocery")
        self.assertEqual(manifest["name"], "Endgame Grocery")
        self.assertEqual(manifest["version"], "0.1.0")
        self.assertEqual(manifest["homeassistant"], "2026.5.0")
        self.assertEqual(manifest["iot_class"], "cloud_polling")
        self.assertEqual(manifest["requirements"], [])
        self.assertTrue(manifest["config_flow"])

    def test_constants(self) -> None:
        """The constant module exposes the expected public integration values."""
        const = importlib.import_module("custom_components.endgame_grocery.const")

        self.assertEqual(const.DOMAIN, "endgame_grocery")
        self.assertEqual(const.PLATFORMS, ["todo"])
        self.assertEqual(const.CONF_BASE_URL, "base_url")
        self.assertEqual(const.CONF_API_KEY, "api_key")
        self.assertEqual(const.DEFAULT_SCAN_INTERVAL, timedelta(seconds=60))

    def test_init_stub_exists(self) -> None:
        """The integration package is present and importable."""
        integration = importlib.import_module("custom_components.endgame_grocery")

        self.assertEqual(
            integration.__doc__,
            "Endgame Grocery Home Assistant integration.",
        )


if __name__ == "__main__":
    unittest.main()
