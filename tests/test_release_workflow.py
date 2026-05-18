"""Validation tests for the GitHub release workflow."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestReleaseWorkflow(unittest.TestCase):
    """Verify the T-007 workflow structure and release packaging contract."""

    def test_release_workflow_matches_planned_contract(self) -> None:
        """The release workflow should package the integration from version tags."""
        workflow_path = REPO_ROOT / ".github" / "workflows" / "release.yml"
        self.assertTrue(workflow_path.exists())

        content = workflow_path.read_text(encoding="utf-8")

        self.assertIn("name: Release", content)
        self.assertIn("push:", content)
        self.assertIn("tags:", content)
        self.assertIn("- 'v*.*.*'", content)
        self.assertIn("permissions:", content)
        self.assertIn("contents: write", content)
        self.assertIn("jobs:", content)
        self.assertIn("release:", content)
        self.assertIn("uses: actions/checkout@v4", content)
        self.assertIn("id: version", content)
        self.assertIn('echo "VERSION=${GITHUB_REF_NAME#v}" >> "$GITHUB_OUTPUT"', content)
        self.assertIn("custom_components/endgame_grocery/manifest.json", content)
        self.assertIn('data["version"] = "${{ steps.version.outputs.VERSION }}"', content)
        self.assertIn('json.dumps(data, indent=2) + "\\n"', content)
        self.assertIn("cd custom_components", content)
        self.assertIn("zip -r ../endgame_grocery.zip endgame_grocery/", content)
        self.assertIn("uses: softprops/action-gh-release@v2", content)
        self.assertIn("files: endgame_grocery.zip", content)
        self.assertIn("generate_release_notes: true", content)


if __name__ == "__main__":
    unittest.main()
