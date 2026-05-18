"""Validation tests for the GitHub CI workflow."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestCiWorkflow(unittest.TestCase):
    """Verify the T-006 workflow structure and planned commands."""

    def test_ci_workflow_matches_planned_contract(self) -> None:
        """The CI workflow should expose the expected triggers and jobs."""
        workflow_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        self.assertTrue(workflow_path.exists())

        content = workflow_path.read_text(encoding="utf-8")

        self.assertIn("name: CI", content)
        self.assertIn("push:", content)
        self.assertIn("- main", content)
        self.assertIn("- 'feature/**'", content)
        self.assertIn("pull_request:", content)
        self.assertIn("branches:", content)
        self.assertIn("jobs:", content)
        self.assertIn("validate:", content)
        self.assertIn("hacs:", content)
        self.assertIn("python-version: '3.12'", content)
        self.assertIn("python -m py_compile", content)
        self.assertIn("custom_components/endgame_grocery/api.py", content)
        self.assertIn("custom_components/endgame_grocery/config_flow.py", content)
        self.assertIn("custom_components/endgame_grocery/const.py", content)
        self.assertIn("custom_components/endgame_grocery/__init__.py", content)
        self.assertIn("custom_components/endgame_grocery/todo.py", content)
        self.assertIn(
            'python -m unittest discover -s tests -p "test_*.py" -v',
            content,
        )
        self.assertIn("uses: hacs/action@main", content)
        self.assertIn("category: integration", content)


if __name__ == "__main__":
    unittest.main()
