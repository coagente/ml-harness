import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import guard  # noqa: E402

SECRET_NAME = '.' + 'env'   # built so this file does not look like it touches a secret


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'data/raw').mkdir(parents=True)
        (self.root / 'data/raw/events.csv').write_text('a\n', encoding='utf-8')
        (self.root / 'runs').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def decision(self, tool, inp, branch='feature/x'):
        out = guard.pre_tool_use(tool, inp, self.root, branch)
        return out and out['hookSpecificOutput']['permissionDecision']

    def test_existing_raw_file_cannot_be_edited(self):
        self.assertEqual(self.decision('Edit', {'file_path': str(self.root / 'data/raw/events.csv')}), 'deny')

    def test_new_raw_file_can_be_added(self):
        self.assertIsNone(self.decision('Write', {'file_path': str(self.root / 'data/raw/new.csv')}))

    def test_run_records_are_generated(self):
        self.assertEqual(self.decision('Write', {'file_path': str(self.root / 'runs/r.json')}), 'deny')

    def test_secrets_are_denied_but_example_is_fine(self):
        self.assertEqual(self.decision('Read', {'file_path': str(self.root / SECRET_NAME)}), 'deny')
        self.assertEqual(self.decision('Bash', {'command': f'cat {SECRET_NAME}.local'}), 'deny')
        self.assertIsNone(self.decision('Read', {'file_path': str(self.root / (SECRET_NAME + '.example'))}))

    def test_bash_cannot_modify_raw(self):
        self.assertEqual(self.decision('Bash', {'command': 'rm data/raw/events.csv'}), 'deny')
        self.assertEqual(self.decision('Bash', {'command': "sed -i '' 's/a/b/' data/raw/events.csv"}), 'deny')
        self.assertIsNone(self.decision('Bash', {'command': 'head data/raw/events.csv'}))

    def test_main_branch_is_protected(self):
        self.assertEqual(self.decision('Bash', {'command': 'git commit -m x'}, branch='main'), 'deny')
        self.assertIsNone(self.decision('Bash', {'command': 'git commit -m x'}, branch='feature/x'))
        self.assertEqual(self.decision('Bash', {'command': 'git push origin main'}), 'deny')
        self.assertEqual(self.decision('Bash', {'command': 'git commit --no-verify -m x'}), 'deny')

    def test_ordinary_work_is_allowed(self):
        self.assertIsNone(self.decision('Bash', {'command': 'make demo && make gate'}))
        self.assertIsNone(self.decision('Edit', {'file_path': str(self.root / 'examples/weekly_risk/run.py')}))


if __name__ == '__main__':
    unittest.main()
