import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import check  # noqa: E402


class RepositoryCheckTest(unittest.TestCase):
    def test_repository_passes_make_check(self):
        self.assertEqual(check.problems(ROOT), [])


if __name__ == '__main__':
    unittest.main()
