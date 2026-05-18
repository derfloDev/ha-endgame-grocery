"""Validation tests for the README overhaul and packaged icon."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestReadmeAndIcon(unittest.TestCase):
    """Verify the T-008 documentation and asset contract."""

    def test_readme_contains_end_user_sections_and_badges(self) -> None:
        """The README should present the end-user install and usage flow."""
        readme_path = REPO_ROOT / "README.md"
        content = readme_path.read_text(encoding="utf-8")

        self.assertIn('<img src="assets/endgame_grocery_logo.png"', content)
        self.assertIn("Endgame Grocery - Home Assistant Integration", content)
        self.assertIn(
            "https://github.com/DerFloDev/ha-endgame-grocery/actions/workflows/ci.yml/badge.svg",
            content,
        )
        self.assertIn(
            "https://my.home-assistant.io/redirect/hacs_repository/?owner=DerFloDev&repository=ha-endgame-grocery&category=integration",
            content,
        )
        self.assertIn("## Overview", content)
        self.assertIn("## Features", content)
        self.assertIn("## Prerequisites", content)
        self.assertIn("## Installation via HACS", content)
        self.assertIn("## Manual Installation", content)
        self.assertIn("## Configuration", content)
        self.assertIn("## Usage", content)
        self.assertIn("## Troubleshooting", content)
        self.assertIn("## Release and versioning", content)
        self.assertIn("## License", content)
        self.assertNotIn("## AI Workflow", content)

    def test_icon_is_png_copy_of_root_logo(self) -> None:
        """The packaged integration icon should match the source logo bytes."""
        source_path = REPO_ROOT / "assets" / "endgame_grocery_logo.png"
        icon_path = (
            REPO_ROOT
            / "custom_components"
            / "endgame_grocery"
            / "images"
            / "icon.png"
        )

        self.assertTrue(source_path.exists())
        self.assertTrue(icon_path.exists())

        source_bytes = source_path.read_bytes()
        icon_bytes = icon_path.read_bytes()

        self.assertTrue(icon_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(icon_bytes, source_bytes)


if __name__ == "__main__":
    unittest.main()
